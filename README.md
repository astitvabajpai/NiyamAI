# NiyamAI

**Question-answering system over RBI regulations.** Ask plain-English questions, get precise answers with citations to exact documents and pages.

## Architecture

**RAG (Retrieval-Augmented Generation):** Not a trained model — uses pre-trained models for retrieval and generation.

### Pipeline

```
PDF Documents
    │
    ▼ [Ingestion — run once offline]
Parse PDFs → Clean text → Chunk (section-aware) → Embed → FAISS + BM25 indexes
    │
    ▼ [Query — real-time]
Dense retrieval (FAISS) + Keyword retrieval (BM25)
    → RRF Fusion → Cross-encoder Rerank → Groq LLM (streaming)
    → Answer with citations
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI + Uvicorn |
| Embedding | `BAAI/bge-small-en-v1.5` (optional — disabled on low-memory deployments) |
| Vector DB | FAISS (local) — skipped when `USE_DENSE=0` |
| Keyword Search | BM25 (rank_bm25) |
| Reranker | `cross-encoder/ms-marco-MiniLM-L-6-v2` — skipped when `USE_DENSE=0` |
| LLM | Groq — Llama 3.3 70B |
| PDF Parsing | PyMuPDF |
| Frontend | Vanilla HTML/CSS/JS (dark glassmorphism) |

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set environment variables
cp .env.example .env
# Edit .env and add your GROQ_API_KEY from https://console.groq.com/keys

# 3. Run ingestion (one-time — builds indexes from PDFs in ./Directories)
python -m src.ingestion

# 4. Start the server
python main.py
# or
uvicorn src.api:app --reload --host 0.0.0.0 --port 8000
```

Then open http://localhost:8000

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GROQ_API_KEY` | required | Get from https://console.groq.com/keys |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Groq model name |
| `EMBEDDING_MODEL` | `BAAI/bge-small-en-v1.5` | Local embedding model |
| `RERANKER_MODEL` | `cross-encoder/ms-marco-MiniLM-L-6-v2` | Local reranker |
| `USE_DENSE` | `0` | Set `1` to enable FAISS+reranker (requires >512MB RAM) |
| `PDF_DIR` | `./Directories` | Source PDF folder |
| `CHUNKS_DIR` | `./data/chunks` | Where indexes are stored |
| `BM25_INDEX_PATH` | `./data/bm25_index.pkl` | BM25 index file |
| `CHUNKING_STRATEGY` | `section_aware` | `fixed` or `section_aware` |
| `CHUNK_SIZE` | `400` | Tokens per chunk (fixed mode) |
| `CHUNK_OVERLAP` | `80` | Token overlap between chunks |
| `RETRIEVAL_K` | `20` | Top-K per index before fusion |
| `RERANK_TOP_K` | `5` | Top-K after reranking (sent to LLM) |
| `API_HOST` | `0.0.0.0` | Server host |
| `API_PORT` | `8000` | Server port |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Premium HTML frontend |
| POST | `/api/query` | Non-streaming query (with caching) |
| POST | `/api/query/stream` | SSE streaming query |
| GET | `/api/chunks/{index}` | Get chunk by index |
| GET | `/health` | Health check + chunk count |

### Example Request

```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the KYC norms for bank accounts?"}'
```

## Evaluation

```bash
python -m src.evaluation
```

Runs 60 hand-verified questions across 6 topics (KYC, Digital Lending, Priority Sector Lending, Digital Banking, Digital Payment, Fraud Risk Management). Compares 4 retrieval configs: `dense_only`, `bm25_only`, `hybrid`, `hybrid_rerank`.

## File Structure

```
NiyamAI/
├── src/
│   ├── ingestion.py    # PDF parsing, chunking, embedding, indexing
│   ├── retrieval.py    # FAISS + BM25 + RRF + cross-encoder reranking
│   ├── generation.py   # Groq LLM streaming
│   ├── api.py          # FastAPI endpoints (with caching + rate limiting)
│   ├── ui.py           # Premium dark HTML frontend
│   └── evaluation.py   # Eval suite (60 questions, 4 configs)
├── data/
│   ├── chunks/
│   │   ├── metadata.json      # Chunk metadata (generated)
│   │   └── faiss_index.faiss  # FAISS index (generated)
│   ├── bm25_index.pkl         # BM25 index (generated)
│   └── eval_set.json          # 60-question eval dataset
├── Directories/        # Place source PDFs here (by category)
│   ├── KYC/
│   ├── Digital Banking/
│   ├── Digital Payment/
│   ├── Fraud Risk Management/
│   └── Priority sector lending/
├── .env                # API keys (never commit)
├── main.py             # Entry point
├── requirements.txt
├── Dockerfile
├── render.yaml
└── README.md
```

## Deployment

### Render / Railway
1. Connect GitHub repo
2. Set env vars (`GROQ_API_KEY`, optionally `USE_DENSE=1` for full hybrid retrieval on higher-tier instances)
3. Start command: `uvicorn src.api:app --host 0.0.0.0 --port $PORT`
4. First boot automatically runs ingestion if `data/chunks/metadata.json` is missing

> **Note:** Pre-built `data/` indexes are committed to the repo. Set `USE_DENSE=1` only on instances with ≥1GB RAM — default BM25-only mode uses ~180 MB.

### Docker

```bash
docker build -t niyamai .
docker run -p 8000:8000 --env-file .env niyamai
```

## Features

- ✅ **Hybrid retrieval** — Dense (FAISS) + Keyword (BM25) + RRF fusion
- ✅ **Cross-encoder reranking** for precision
- ✅ **Streaming answers** via Server-Sent Events (SSE)
- ✅ **Source citations** with document + page number
- ✅ **In-memory response caching** (1hr TTL)
- ✅ **Rate limiting** (20 req/min per IP)
- ✅ **Premium dark UI** — glassmorphism design, mobile responsive
- ✅ **Query history** — persisted in localStorage
- ✅ **60-question eval suite** across 6 regulatory topics
