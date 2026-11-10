"""
Generate PNG diagrams for NiyamAI README using Pillow only (no Cairo/system deps).
Run: python scripts/generate_diagrams.py
Output: docs/images/pipeline.png, retrieval.png, techstack.png
"""

from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

OUT = Path("docs/images")
OUT.mkdir(parents=True, exist_ok=True)

# ── Palette ──────────────────────────────────────────────────────────────────
BG         = (249, 250, 252)   # #F9FAFC
DARK       = (15,  23,  42)    # #0F172A  (dark boxes)
GREEN_DARK = (44,  62,  26)    # #2C3E1A  (accent green dark)
GREEN_BRD  = (90, 109,  52)    # #5A6D34  (accent green border)
GREEN_LITE = (240, 244, 241)   # #F0F4F1
WHITE      = (255, 255, 255)
BORDER     = (203, 213, 225)   # #CBD5E1
MUTED      = (100, 116, 139)   # #64748B
TEXT       = (15,  23,  42)
TEXT2      = (71,  85, 105)
ARROW      = (148, 163, 184)   # #94A3B8

SCALE = 2  # render at 2x, then scale down for crisp output

def make_canvas(w, h):
    img = Image.new("RGB", (w * SCALE, h * SCALE), BG)
    draw = ImageDraw.Draw(img)
    return img, draw

def save(img, name, w, h):
    out = img.resize((w, h), Image.LANCZOS)
    path = OUT / f"{name}.png"
    out.save(path, "PNG", optimize=True)
    print(f"  Saved {path}  ({w}x{h})")

def S(n):
    """Scale a coord to 2x canvas."""
    return n * SCALE

def font(size):
    try:
        return ImageFont.truetype("arial.ttf", size * SCALE)
    except Exception:
        return ImageFont.load_default()

def bold(size):
    try:
        return ImageFont.truetype("arialbd.ttf", size * SCALE)
    except Exception:
        return ImageFont.load_default()

def box(draw, x, y, w, h, fill=WHITE, border=BORDER, radius=6):
    r = radius * SCALE
    x, y, w, h = S(x), S(y), S(w), S(h)
    draw.rounded_rectangle([x, y, x+w, y+h], radius=r, fill=fill, outline=border, width=SCALE)

def text_center(draw, cx, cy, txt, fnt, color=TEXT):
    draw.text((S(cx), S(cy)), txt, font=fnt, fill=color, anchor="mm")

def text_left(draw, x, y, txt, fnt, color=TEXT):
    draw.text((S(x), S(y)), txt, font=fnt, fill=color, anchor="lm")

def arrow_down(draw, cx, y1, y2, color=ARROW):
    draw.line([(S(cx), S(y1)), (S(cx), S(y2)-S(6))], fill=color, width=SCALE*2)
    draw.polygon([(S(cx), S(y2)), (S(cx)-S(5), S(y2)-S(8)), (S(cx)+S(5), S(y2)-S(8))], fill=color)

def arrow_right(draw, x1, x2, cy, color=ARROW):
    draw.line([(S(x1), S(cy)), (S(x2)-S(6), S(cy))], fill=color, width=SCALE*2)
    draw.polygon([(S(x2), S(cy)), (S(x2)-S(8), S(cy)-S(5)), (S(x2)-S(8), S(cy)+S(5))], fill=color)

def divider(draw, y, x1, x2):
    draw.line([(S(x1), S(y)), (S(x2), S(y))], fill=BORDER, width=SCALE)

def title_bar(draw, W, txt):
    draw.line([(S(20), S(52)), (S(W-20), S(52))], fill=BORDER, width=SCALE)
    text_center(draw, W//2, 34, txt, bold(13), TEXT)

# ═══════════════════════════════════════════════════════════════════════════════
# 1. PIPELINE DIAGRAM
# ═══════════════════════════════════════════════════════════════════════════════
def make_pipeline():
    W, H = 860, 500
    img, draw = make_canvas(W, H)

    title_bar(draw, W, "NiyamAI — Full RAG Pipeline")

    # ── Ingestion column (x=20) ──
    label_x = 20
    col1_cx = 104

    draw.rounded_rectangle([S(16), S(60), S(196), S(82)], radius=S(3), fill=(226,232,240))
    text_center(draw, col1_cx, 71, "INGESTION", font(8), MUTED)

    # PDF box
    box(draw, 20, 88, 168, 52, WHITE, BORDER)
    text_center(draw, col1_cx, 108, "📄 PDF Documents", bold(11), TEXT)
    text_center(draw, col1_cx, 124, "33 RBI circulars & directions", font(9), MUTED)
    arrow_down(draw, col1_cx, 140, 160)

    # Parse & Chunk
    box(draw, 20, 160, 168, 52, WHITE, BORDER)
    text_center(draw, col1_cx, 180, "⚙  Parse & Chunk", bold(11), TEXT)
    text_center(draw, col1_cx, 196, "Section-aware or fixed-size", font(9), MUTED)
    arrow_down(draw, col1_cx, 212, 232)

    # Embed & Index
    box(draw, 20, 232, 168, 52, WHITE, BORDER)
    text_center(draw, col1_cx, 252, "🗄  Embed & Index", bold(11), TEXT)
    text_center(draw, col1_cx, 268, "FAISS vectors + BM25 tokens", font(9), MUTED)

    # ── Divider ──
    draw.line([(S(204), S(62)), (S(204), S(440))], fill=BORDER, width=SCALE)

    # ── Query column ──
    col2_cx = 300

    draw.rounded_rectangle([S(216), S(60), S(386), S(82)], radius=S(3), fill=(226,232,240))
    text_center(draw, col2_cx, 71, "QUERY", font(8), MUTED)

    box(draw, 216, 88, 168, 52, DARK, DARK)
    text_center(draw, col2_cx, 108, "💬 User Query", bold(11), WHITE)
    text_center(draw, col2_cx, 124, "Plain-English question", font(9), (148,163,184))
    arrow_down(draw, col2_cx, 140, 160)

    box(draw, 216, 160, 168, 52, GREEN_LITE, (90,109,52))
    text_center(draw, col2_cx, 180, "🔤 Acronym Expand", bold(11), GREEN_DARK)
    text_center(draw, col2_cx, 196, "KYC → know your customer", font(9), GREEN_BRD)
    arrow_down(draw, col2_cx, 212, 232)

    box(draw, 216, 232, 168, 52, WHITE, BORDER)
    text_center(draw, col2_cx, 252, "🔍 Dual Retrieval", bold(11), TEXT)
    text_center(draw, col2_cx, 268, "FAISS dense + BM25 keyword", font(9), MUTED)
    arrow_down(draw, col2_cx, 284, 304)

    box(draw, 216, 304, 168, 44, WHITE, BORDER)
    text_center(draw, col2_cx, 322, "⚖  RRF Fusion", bold(11), TEXT)
    text_center(draw, col2_cx, 336, "Reciprocal Rank Fusion", font(9), MUTED)
    arrow_down(draw, col2_cx, 348, 368)

    box(draw, 216, 368, 168, 44, WHITE, BORDER)
    text_center(draw, col2_cx, 386, "🎯 Rerank + Dedup", bold(11), TEXT)
    text_center(draw, col2_cx, 400, "Cross-encoder · no dup pages", font(9), MUTED)

    # ── Divider ──
    draw.line([(S(400), S(62)), (S(400), S(440))], fill=BORDER, width=SCALE)

    # ── Generation column ──
    col3_cx = 500

    draw.rounded_rectangle([S(406), S(60), S(596), S(82)], radius=S(3), fill=(226,232,240))
    text_center(draw, col3_cx, 71, "GENERATION", font(8), MUTED)

    box(draw, 406, 88, 184, 52, WHITE, BORDER)
    text_center(draw, col3_cx, 108, "📚 Context Chunks", bold(11), TEXT)
    text_center(draw, col3_cx, 124, "Top-K passages with metadata", font(9), MUTED)
    arrow_down(draw, col3_cx, 140, 160)

    box(draw, 406, 160, 184, 52, GREEN_DARK, GREEN_DARK)
    text_center(draw, col3_cx, 180, "🤖 Groq LLM", bold(11), WHITE)
    text_center(draw, col3_cx, 196, "llama-3.3-70b-versatile", font(9), (167,181,138))
    arrow_down(draw, col3_cx, 212, 232)

    box(draw, 406, 232, 184, 52, WHITE, BORDER)
    text_center(draw, col3_cx, 252, "📡 SSE Stream", bold(11), TEXT)
    text_center(draw, col3_cx, 268, "Tokens streamed live to browser", font(9), MUTED)

    # Arrow: rerank → context (horizontal across divider)
    draw.line([(S(384), S(390)), (S(406), S(390)), (S(406), S(114))], fill=ARROW, width=SCALE*2)
    draw.polygon([(S(406), S(108)), (S(401), S(118)), (S(411), S(118))], fill=ARROW)

    # ── Divider ──
    draw.line([(S(600), S(62)), (S(600), S(440))], fill=BORDER, width=SCALE)

    # ── Output column ──
    col4_cx = 724

    draw.rounded_rectangle([S(606), S(60), S(844), S(82)], radius=S(3), fill=(226,232,240))
    text_center(draw, col4_cx, 71, "OUTPUT", font(8), MUTED)

    # Arrow from SSE to output
    arrow_right(draw, 590, 610, 258)

    box(draw, 606, 232, 232, 52, WHITE, (90,109,52))
    text_center(draw, col4_cx, 252, "✅ Structured Answer", bold(11), GREEN_DARK)
    text_center(draw, col4_cx, 268, "Summary · provisions · scope", font(9), GREEN_BRD)
    arrow_down(draw, col4_cx, 284, 304)

    box(draw, 606, 304, 232, 52, WHITE, (90,109,52))
    text_center(draw, col4_cx, 322, "🔖 Citations", bold(11), GREEN_DARK)
    text_center(draw, col4_cx, 338, "Document · page · PDF deep-link", font(9), GREEN_BRD)
    arrow_down(draw, col4_cx, 356, 376)

    box(draw, 606, 376, 232, 44, GREEN_LITE, (90,109,52))
    text_center(draw, col4_cx, 394, "💾 SQLite Cache", bold(11), GREEN_DARK)
    text_center(draw, col4_cx, 408, "24hr TTL · survives restarts", font(9), GREEN_BRD)

    # Footer note
    text_center(draw, W//2, 460, "USE_DENSE=0 (default): BM25-only ~180 MB RAM   |   USE_DENSE=1: Full hybrid ≥512 MB RAM", font(9), MUTED)

    save(img, "pipeline", W, H)

# ═══════════════════════════════════════════════════════════════════════════════
# 2. RETRIEVAL DIAGRAM
# ═══════════════════════════════════════════════════════════════════════════════
def make_retrieval():
    W, H = 780, 340
    img, draw = make_canvas(W, H)

    title_bar(draw, W, "Retrieval Pipeline")

    # Query input
    box(draw, 290, 60, 200, 48, DARK, DARK)
    text_center(draw, 390, 78, "User Query", bold(12), WHITE)
    text_center(draw, 390, 94, "+ Acronym Expansion", font(9), (148,163,184))

    # Fork lines
    draw.line([(S(320), S(108)), (S(180), S(148))], fill=ARROW, width=SCALE*2)
    draw.polygon([(S(174), S(150)), (S(182), S(141)), (S(188), S(150))], fill=ARROW)
    draw.line([(S(460), S(108)), (S(600), S(148))], fill=ARROW, width=SCALE*2)
    draw.polygon([(S(606), S(150)), (S(594), S(141)), (S(600), S(150))], fill=ARROW)

    # BM25
    box(draw, 60, 150, 240, 50, WHITE, BORDER)
    text_center(draw, 180, 169, "🔑 BM25 Keyword", bold(12), TEXT)
    text_center(draw, 180, 185, "Term frequency scoring", font(9), MUTED)

    # FAISS
    box(draw, 480, 150, 240, 50, WHITE, BORDER)
    text_center(draw, 600, 169, "🧲 FAISS Dense", bold(12), TEXT)
    text_center(draw, 600, 185, "BGE-small cosine similarity", font(9), MUTED)

    # USE_DENSE label
    draw.rounded_rectangle([S(528), S(148), S(718), S(162)], radius=S(3), fill=(226,232,240))
    text_center(draw, 623, 155, "USE_DENSE=1 only", font(8), MUTED)

    # Merge lines to RRF
    draw.line([(S(180), S(200)), (S(180), S(220)), (S(340), S(240))], fill=ARROW, width=SCALE*2)
    draw.line([(S(600), S(200)), (S(600), S(220)), (S(440), S(240))], fill=ARROW, width=SCALE*2)
    draw.polygon([(S(345), S(243)), (S(336), S(234)), (S(345), S(234))], fill=ARROW)
    draw.polygon([(S(435), S(243)), (S(435), S(234)), (S(444), S(234))], fill=ARROW)

    # RRF
    box(draw, 240, 243, 300, 46, WHITE, BORDER)
    text_center(draw, 390, 262, "⚖  Reciprocal Rank Fusion", bold(12), TEXT)
    text_center(draw, 390, 278, "score = Σ 1 / (rank + k)", font(9), MUTED)

    arrow_down(draw, 390, 289, 308)

    # Rerank + dedup
    box(draw, 240, 310, 300, 28, GREEN_DARK, GREEN_DARK)
    text_center(draw, 390, 325, "🎯 Rerank · Sector Filter · Dedup", bold(10), WHITE)

    text_center(draw, W//2, 352, "Returns top-K chunks with full metadata", font(9), MUTED)

    save(img, "retrieval", W, H)

# ═══════════════════════════════════════════════════════════════════════════════
# 3. TECH STACK DIAGRAM
# ═══════════════════════════════════════════════════════════════════════════════
def make_techstack():
    W, H = 780, 310
    img, draw = make_canvas(W, H)

    title_bar(draw, W, "Tech Stack")

    rows = [
        ("FRONTEND", 62,  [(108, "Vanilla HTML/CSS/JS", "templates/index.html"), (296, "marked.js", "Markdown render"), (480, "SSE EventSource", "Live token streaming")]),
        ("BACKEND",  122, [(108, "FastAPI", "REST + SSE"), (256, "Uvicorn", "ASGI server"), (396, "Groq API", "llama-3.3-70b"), (570, "PyMuPDF", "PDF parsing")]),
        ("RETRIEVAL",182, [(108, "BM25 (rank-bm25)", "Keyword · always on"), (296, "FAISS (faiss-cpu)", "Dense · USE_DENSE=1"), (484, "SentenceTransformers", "BGE-small + CrossEncoder")]),
        ("STORAGE",  242, [(108, "SQLite", "cache · log · rate limiter"), (280, "FAISS Index", ".faiss file"), (430, "BM25 Pickle", ".pkl file"), (580, "Metadata JSON", "chunk text + pages")]),
    ]

    # Row lines
    for _, y, _ in rows:
        draw.line([(S(20), S(y-2)), (S(760), S(y-2))], fill=BORDER, width=SCALE)

    draw.line([(S(20), S(298)), (S(760), S(298))], fill=BORDER, width=SCALE)

    for label, y, chips in rows:
        # Row label
        text_left(draw, 22, y + 29, label, font(8), MUTED)

        for cx, name, sub in chips:
            # auto-width based on text
            cw = max(130, len(name) * 8 + 24)
            ch = 42
            bx = cx
            by = y + 10

            fill = DARK if label == "BACKEND" and name in ("FastAPI", "Uvicorn") else \
                   GREEN_DARK if label == "BACKEND" and name == "Groq API" else WHITE
            border = GREEN_BRD if label in ("RETRIEVAL",) and name == "BM25 (rank-bm25)" else BORDER
            tc = WHITE if fill in (DARK, GREEN_DARK) else TEXT
            sc = (148,163,184) if fill in (DARK, GREEN_DARK) else MUTED

            box(draw, bx, by, cw, ch, fill, border)
            text_center(draw, bx + cw//2, by + 15, name, bold(10), tc)
            text_center(draw, bx + cw//2, by + 30, sub, font(8), sc)

    save(img, "techstack", W, H)


if __name__ == "__main__":
    print("Generating diagrams...")
    make_pipeline()
    make_retrieval()
    make_techstack()
    print("Done. Files in docs/images/")
