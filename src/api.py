"""
FastAPI backend for NiyamAI with SSE streaming, persistent SQLite cache,
PDF deep-linking, sector filtering, grounding confidence scoring, and multi-turn support.
"""

import asyncio
import json
import os
import re
import sqlite3
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, Response, StreamingResponse
from pydantic import BaseModel

from src.retrieval import get_retriever
from src.generation import generate_answer
from src.ui import HTMLPage
from src.ingestion import METADATA_PATH, PDF_DIR, BM25_INDEX_PATH

app = FastAPI(title="NiyamAI - RBI Regulation QA")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Persistent SQLite Cache ──────────────────────────────────────────────────
DB_PATH = Path("data/cache.db")
CACHE_TTL = 3600 * 24  # 24 hours


def _init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS query_cache (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                ts REAL NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS query_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                sector TEXT,
                latency_ms REAL NOT NULL,
                grounding_score INTEGER,
                chunks_returned INTEGER,
                cached INTEGER DEFAULT 0,
                error TEXT,
                ts REAL NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS rate_limit (
                ip TEXT NOT NULL,
                ts REAL NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_rate_limit_ip_ts ON rate_limit (ip, ts)")
        conn.commit()


def _log_query(query: str, sector: str | None, latency_ms: float, grounding: int,
               n_chunks: int, cached: bool, error: str | None = None):
    """Append a row to query_log for metrics tracking."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "INSERT INTO query_log (query, sector, latency_ms, grounding_score, chunks_returned, cached, error, ts) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (query[:500], sector, round(latency_ms, 1), grounding, n_chunks, int(cached), error, time.time()),
            )
            conn.commit()
    except Exception:
        pass


def _cache_get(key: str):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.execute("SELECT value, ts FROM query_cache WHERE key = ?", (key,))
            row = cur.fetchone()
            if row and (time.time() - row[1] < CACHE_TTL):
                return json.loads(row[0])
    except Exception:
        pass
    return None


def _cache_set(key: str, value: dict):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO query_cache (key, value, ts) VALUES (?, ?, ?)",
                (key, json.dumps(value), time.time()),
            )
    except Exception:
        pass


def _cache_count() -> int:
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.execute("SELECT COUNT(*) FROM query_cache")
            return cur.fetchone()[0]
    except Exception:
        return 0


# ── Grounding Score Calculator ───────────────────────────────────────────────
def _calc_grounding(answer: str, chunks: list[dict]) -> int:
    """Calculate grounding score using lexical token overlap with retrieved chunks.

    This is a simple word-overlap ratio — useful as a relative signal but NOT a
    guarantee of factual accuracy. It measures how much of the generated answer's
    vocabulary came from the retrieved passages. A low score may indicate the LLM
    introduced content not present in the sources.
    """
    if not chunks or not answer or not answer.strip():
        return 0

    import re
    # Extract meaningful words (alpha, length > 3)
    answer_words = set(re.findall(r"\b[a-z]{4,}\b", answer.lower()))
    if not answer_words:
        return 0

    chunk_words = set()
    for c in chunks:
        chunk_words.update(re.findall(r"\b[a-z]{4,}\b", c.get("text", "").lower()))

    if not chunk_words:
        return 0

    overlap = len(answer_words.intersection(chunk_words))
    ratio = overlap / len(answer_words)
    return min(100, int(ratio * 100))


# ── Conversational Greetings Fast-Path ─────────────────────────────────────────
GREETING_WORDS = {
    "hi", "hii", "hiii", "hello", "hey", "heyy", "greetings",
    "good morning", "good afternoon", "good evening", "help",
    "who are you", "what can you do", "what is niyamai", "namaste", "hi niyamai"
}

GREETING_TEXT = """### 📌 Hello! Welcome to NiyamAI
I am **NiyamAI**, your specialized regulatory intelligence assistant for **Reserve Bank of India (RBI)** notifications, master directions, and circulars.

### 📋 What I Can Help You With
You can ask me plain-English regulatory questions with official circular citations across:
- **🏛️ KYC & AML Compliance:** Customer Due Diligence, CKYCR upload rules, foreign student onboarding, OVD requirements.
- **💳 Digital Payments & UPI:** Payment aggregator licensing, card tokenisation, transaction caps, PPI guidelines.
- **📱 Digital Banking Channels:** Internet & mobile banking authorization, transactional vs. view-only banking, IPv6 mandates.
- **🚨 Fraud Risk Management:** Early Warning Signals (EWS), fraud reporting timelines to RBI, red flag indicators.
- **🌾 Priority Sector Lending:** Targets for Domestic Banks, Foreign Banks, and Small Finance Banks.

### 💡 Try Asking
- *"What are the KYC norms for opening a bank account?"*
- *"What are the simplified norms for foreign students?"*
- *"What are the eligibility criteria for transactional digital banking?"*
- *"What are the priority sector lending targets for commercial banks?"*

Feel free to pick a sector from the filter pills above or type your question below!"""


def is_conversational_greeting(query: str) -> bool:
    clean = query.strip().lower().rstrip("!?. ")
    return clean in GREETING_WORDS or bool(re.match(r"\b(hello|hi|hey)\s*$", clean))


# ── Rate limiter (SQLite-backed, survives restarts) ──────────────────────────
RATE_LIMIT = 40       # requests
RATE_WINDOW = 60      # per second window


def _check_rate(client_ip: str) -> bool:
    """Persistent rate limiter backed by SQLite. Survives process restarts."""
    now = time.time()
    cutoff = now - RATE_WINDOW
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "DELETE FROM rate_limit WHERE ts < ?", (cutoff,)
            )
            cur = conn.execute(
                "SELECT COUNT(*) FROM rate_limit WHERE ip = ? AND ts >= ?",
                (client_ip, cutoff),
            )
            count = cur.fetchone()[0]
            if count >= RATE_LIMIT:
                return False
            conn.execute(
                "INSERT INTO rate_limit (ip, ts) VALUES (?, ?)", (client_ip, now)
            )
            conn.commit()
    except Exception:
        return True  # fail open on DB errors
    return True


# ── Startup ───────────────────────────────────────────────────────────────────
def _ensure_index():
    """Warn if indexes are missing. Does NOT run ingestion on deploy —
    PDFs are not committed to the repo. Run python -m src.ingestion locally
    and commit the generated data/ files to rebuild."""
    if METADATA_PATH.exists() and BM25_INDEX_PATH.exists():
        return
    print("WARNING: Search indexes not found.")
    print("  The app will start but all queries will return no results.")
    print("  To fix: run  python -m src.ingestion  then redeploy.")


@app.on_event("startup")
async def startup():
    _init_db()
    _ensure_index()
    get_retriever()


# ── Models ────────────────────────────────────────────────────────────────────
class QueryRequest(BaseModel):
    query: str
    sector: str | None = None
    history: list[dict] | None = None
    show_context: bool = False


class QueryResponse(BaseModel):
    answer: str
    citations: list[dict]
    grounding_score: int = 0
    context_chunks: list[dict] | None = None
    cached: bool = False


# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def index():
    return HTMLPage.get_html()


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)


@app.get("/api/pdf/{doc_name:path}")
async def get_pdf(doc_name: str):
    """Serve official RBI PDF document for deep-linking citation previews."""
    clean_name = doc_name.replace(".pdf", "").strip()
    retriever = get_retriever()
    matched_path = None

    for c in retriever.metadata:
        if c.get("doc_name") == clean_name:
            rel = c.get("rel_path")
            if rel:
                candidate = Path("Directories") / rel
                if candidate.exists():
                    matched_path = candidate
                    break

    if not matched_path:
        for p in Path("Directories").rglob(f"*{clean_name}*.pdf"):
            matched_path = p
            break

    if not matched_path or not matched_path.exists():
        raise HTTPException(status_code=404, detail=f"PDF '{doc_name}' not found")

    return FileResponse(
        str(matched_path),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{matched_path.name}"'},
    )


@app.post("/api/query", response_model=QueryResponse)
async def query_endpoint(req: QueryRequest, request: Request):
    """Non-streaming query endpoint with persistent SQLite caching."""
    client_ip = request.client.host if request.client else "unknown"
    if not _check_rate(client_ip):
        raise HTTPException(status_code=429, detail="Too many requests. Please wait a moment.")

    if is_conversational_greeting(req.query):
        return QueryResponse(
            answer=GREETING_TEXT,
            citations=[],
            grounding_score=100,
            context_chunks=None,
            cached=False,
        )

    t0 = time.time()
    cache_key = f"query:{req.query.strip().lower()}:sec:{req.sector or 'all'}"
    cached = _cache_get(cache_key)
    if cached:
        latency_ms = (time.time() - t0) * 1000
        _log_query(req.query, req.sector, latency_ms, cached.get("grounding_score", 0),
                   len(cached.get("citations", [])), cached=True)
        return QueryResponse(**cached, cached=True)

    loop = asyncio.get_running_loop()
    retriever = get_retriever()
    chunks = await loop.run_in_executor(
        None, lambda: retriever.retrieve(req.query, sector=req.sector)
    )

    if not chunks:
        latency_ms = (time.time() - t0) * 1000
        _log_query(req.query, req.sector, latency_ms, 0, 0, cached=False, error="no_chunks")
        raise HTTPException(status_code=404, detail="No relevant documents found")

    answer_parts = await loop.run_in_executor(
        None, lambda: list(generate_answer(req.query, chunks, stream=False, history=req.history))
    )
    answer = "".join(answer_parts)
    grounding = _calc_grounding(answer, chunks)

    citations = [
        {
            "id": i + 1,
            "doc": c["doc_name"],
            "page": c["page"],
            "section": c.get("section", ""),
            "pdf_url": f"/api/pdf/{c['doc_name']}#page={c['page']}",
        }
        for i, c in enumerate(chunks)
    ]

    result = {
        "answer": answer,
        "citations": citations,
        "grounding_score": grounding,
        "context_chunks": chunks if req.show_context else None,
    }
    _cache_set(cache_key, result)
    latency_ms = (time.time() - t0) * 1000
    _log_query(req.query, req.sector, latency_ms, grounding, len(chunks), cached=False)

    return QueryResponse(**result, cached=False)


@app.post("/api/query/stream")
async def query_stream_endpoint(req: QueryRequest, request: Request):
    """Streaming query endpoint using Server-Sent Events."""
    client_ip = request.client.host if request.client else "unknown"
    if not _check_rate(client_ip):
        return StreamingResponse(
            iter([f"data: {json.dumps({'type': 'error', 'message': 'Rate limit exceeded. Please wait a moment.'})}\n\n"]),
            media_type="text/event-stream",
        )

    if is_conversational_greeting(req.query):
        async def greeting_stream():
            yield f"data: {json.dumps({'type': 'context', 'chunks': []})}\n\n"
            words = GREETING_TEXT.split(" ")
            for i, w in enumerate(words):
                token = w if i == 0 else " " + w
                yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
                await asyncio.sleep(0.012)
            yield f"data: {json.dumps({'type': 'complete', 'answer': GREETING_TEXT, 'citations': [], 'grounding_score': 100})}\n\n"

        return StreamingResponse(greeting_stream(), media_type="text/event-stream")

    t0 = time.time()
    loop = asyncio.get_running_loop()
    retriever = get_retriever()
    chunks = await loop.run_in_executor(
        None, lambda: retriever.retrieve(req.query, sector=req.sector)
    )

    if not chunks:
        latency_ms = (time.time() - t0) * 1000
        _log_query(req.query, req.sector, latency_ms, 0, 0, cached=False, error="no_chunks")
        return StreamingResponse(
            iter([f"data: {json.dumps({'type': 'error', 'message': 'No relevant documents found for this sector query.'})}\n\n"]),
            media_type="text/event-stream",
        )

    async def event_stream():
        # Send initial context info with PDF URLs
        decorated_chunks = []
        for c in chunks:
            c_copy = dict(c)
            c_copy["pdf_url"] = f"/api/pdf/{c['doc_name']}#page={c['page']}"
            decorated_chunks.append(c_copy)

        yield f"data: {json.dumps({'type': 'context', 'chunks': decorated_chunks})}\n\n"

        # Stream tokens live via queue
        queue: asyncio.Queue = asyncio.Queue()

        def _producer():
            try:
                for token in generate_answer(req.query, chunks, stream=True, history=req.history):
                    loop.call_soon_threadsafe(queue.put_nowait, token)
            except Exception as e:
                loop.call_soon_threadsafe(queue.put_nowait, e)
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, None)

        loop.run_in_executor(None, _producer)

        answer_text = ""
        while True:
            item = await queue.get()
            if item is None:
                break
            if isinstance(item, Exception):
                yield f"data: {json.dumps({'type': 'error', 'message': str(item)})}\n\n"
                return
            answer_text += item
            yield f"data: {json.dumps({'type': 'token', 'content': item})}\n\n"

        grounding = _calc_grounding(answer_text, chunks)
        citations = [
            {
                "id": i + 1,
                "doc": c["doc_name"],
                "page": c["page"],
                "section": c.get("section", ""),
                "pdf_url": f"/api/pdf/{c['doc_name']}#page={c['page']}",
            }
            for i, c in enumerate(chunks)
        ]

        # Cache complete result
        cache_key = f"query:{req.query.strip().lower()}:sec:{req.sector or 'all'}"
        _cache_set(
            cache_key,
            {
                "answer": answer_text,
                "citations": citations,
                "grounding_score": grounding,
                "context_chunks": chunks if req.show_context else None,
            },
        )

        # Log after streaming completes
        latency_ms = (time.time() - t0) * 1000
        _log_query(req.query, req.sector, latency_ms, grounding, len(chunks), cached=False)

        yield f"data: {json.dumps({'type': 'complete', 'answer': answer_text, 'citations': citations, 'grounding_score': grounding})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/api/chunks/{chunk_index}")
async def get_chunk(chunk_index: int):
    """Get a specific chunk by index for citation display."""
    retriever = get_retriever()
    if chunk_index < 0 or chunk_index >= len(retriever.metadata):
        raise HTTPException(status_code=404, detail="Chunk not found")
    return retriever.metadata[chunk_index]


@app.get("/health")
async def health():
    retriever = get_retriever()
    return {
        "status": "ok",
        "chunks": len(retriever.metadata),
        "cache_entries": _cache_count(),
    }


@app.get("/api/metrics")
async def metrics_endpoint():
    """Return aggregated query metrics from SQLite log."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            # Summary stats
            cur = conn.execute("""
                SELECT
                    COUNT(*) as total_queries,
                    AVG(latency_ms) as avg_latency_ms,
                    MAX(latency_ms) as max_latency_ms,
                    AVG(grounding_score) as avg_grounding,
                    SUM(cached) as cache_hits
                FROM query_log
                WHERE ts > strftime('%s', 'now', '-24 hours')
            """)
            row = cur.fetchone()
            total = row[0] or 0
            avg_lat = round(row[1] or 0, 1)
            max_lat = round(row[2] or 0, 1)
            avg_grnd = round(row[3] or 0, 1)
            cache_hits = row[4] or 0

            # Per-sector breakdown
            cur = conn.execute("""
                SELECT sector, COUNT(*) as n, AVG(latency_ms) as avg_ms, AVG(grounding_score) as avg_g
                FROM query_log
                WHERE ts > strftime('%s', 'now', '-24 hours') AND sector IS NOT NULL
                GROUP BY sector
                ORDER BY n DESC
            """)
            by_sector = [{"sector": r[0], "count": r[1], "avg_latency_ms": round(r[2] or 0, 1),
                          "avg_grounding": round(r[3] or 0, 1)} for r in cur.fetchall()]

            # Recent queries (last 20)
            cur = conn.execute("""
                SELECT query, sector, latency_ms, grounding_score, cached, error
                FROM query_log
                ORDER BY ts DESC LIMIT 20
            """)
            recent = [{"query": r[0][:80], "sector": r[1], "latency_ms": round(r[2], 1),
                       "grounding": r[3], "cached": bool(r[4]), "error": r[5]} for r in cur.fetchall()]

            return {
                "total_queries_24h": total,
                "avg_latency_ms": avg_lat,
                "max_latency_ms": max_lat,
                "avg_grounding_score": avg_grnd,
                "cache_hit_rate": round(cache_hits / total, 3) if total else 0,
                "by_sector": by_sector,
                "recent_queries": recent,
            }
    except Exception as e:
        return {"error": str(e)}
