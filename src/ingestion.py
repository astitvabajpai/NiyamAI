"""
Ingestion pipeline: parse PDFs → chunk → embed → index (FAISS + BM25) + metadata.
Run once offline to build the knowledge base.
"""

import json
import os
import pickle
import re
from pathlib import Path

import pymupdf as fitz  # PyMuPDF
from rank_bm25 import BM25Okapi
import faiss

# ── Config from env ──────────────────────────────────────────────────────────
from dotenv import load_dotenv
load_dotenv()

PDF_DIR = Path(os.getenv("PDF_DIR", "./Directories").strip())
CHUNKS_DIR = Path(os.getenv("CHUNKS_DIR", "./data/chunks").strip())
BM25_INDEX_PATH = Path(os.getenv("BM25_INDEX_PATH", "./data/bm25_index.pkl").strip())
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5").strip()
RERANKER_MODEL = os.getenv("RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2").strip()
CHUNKING_STRATEGY = os.getenv("CHUNKING_STRATEGY", "section_aware").strip()
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "400"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "80"))

CHUNKS_DIR.mkdir(parents=True, exist_ok=True)

METADATA_PATH = CHUNKS_DIR / "metadata.json"
FAISS_PATH = CHUNKS_DIR / "faiss_index.faiss"


def _safe_str(s: str | None) -> str:
    """Strip or replace chars that can't encode on this platform."""
    if not s:
        return ""
    # Handle Unicode characters that cause encoding issues on Windows
    return s.encode("utf-8", errors="ignore").decode("utf-8")


def extract_pdf_info(pdf_path: Path) -> dict:
    """Extract document-level metadata from a PDF."""
    doc = fitz.open(pdf_path)
    meta = doc.metadata or {}
    info = {
        "filename": pdf_path.name,
        "path": str(pdf_path),
        "page_count": len(doc),
        "title": _safe_str(meta.get("title")).strip() or pdf_path.stem,
        "subject": _safe_str(meta.get("subject")),
        "creation_date": _safe_str(meta.get("creationDate")),
    }
    doc.close()
    return info


def clean_text(text: str) -> str:
    """Remove headers, footers, page numbers, and fix broken line breaks."""
    # Remove headers/footers pattern (common in RBI docs)
    text = re.sub(r"^\s*RBI\s*[-–]?\s*\d+\s*[-–]?\s*[A-Z]*\s*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^.*Page \d+.*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)  # collapse blank lines
    text = re.sub(r"[ \t]+", " ", text)             # collapse whitespace
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)    # join lines without blank between
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_section_headings(text: str) -> list[tuple[int, str]]:
    """Find section headings and their approximate character positions."""
    headings = []
    pattern = r"((?:^|\n)\s*(?:Section|Chapter|Clause|Part|Regulation|Rule|Sub-section|Sub-Section|Para|Paragraph)\s*[\dIVX]+\s*[:\-]?\s*.+?)(?=\n)"
    for match in re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE):
        heading = match.group(1).strip()
        if len(heading) < 100:
            headings.append((match.start(), heading))
    return headings


def chunk_fixed_size(text: str, chunk_size: int = 400, overlap: int = 80) -> list[dict]:
    """Fixed-size chunking with overlap."""
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        end = min(i + chunk_size, len(words))
        chunk_text = " ".join(words[i:end])
        if len(chunk_text.strip()) > 50:
            chunks.append({"text": chunk_text.strip(), "start_token": i, "end_token": end})
        i += chunk_size - overlap
    return chunks


def chunk_section_aware(text: str, max_tokens: int = 400, overlap: int = 80) -> list[dict]:
    """Section-aware chunking: split on headings first, then sub-chunk if needed."""
    paragraphs = re.split(r"\n{2,}", text)
    chunks = []
    current_text = ""
    current_heading = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        is_heading = bool(re.match(
            r"^(Section|Chapter|Clause|Part|Regulation|Rule|Sub-section|Sub-Section|Para|Paragraph)\s*[\dIVX]+",
            para, re.IGNORECASE
        ))

        if is_heading:
            if current_text and len(current_text.strip()) > 50:
                chunks.append({"text": current_text.strip(), "heading": current_heading})
            current_text = para
            current_heading = para
        else:
            if len(current_text) + len(para) > max_tokens * 3:
                if current_text:
                    chunks.append({"text": current_text.strip(), "heading": current_heading})
                overlap_words = para.split()[:overlap]
                current_text = " ".join(overlap_words) + "\n\n" + para
                current_heading = ""
            else:
                current_text += "\n\n" + para

    if current_text and len(current_text.strip()) > 50:
        chunks.append({"text": current_text.strip(), "heading": current_heading})

    return chunks


def chunk_text(text: str, strategy: str = "section_aware", chunk_size: int = 400, overlap: int = 80) -> list[dict]:
    """Choose chunking strategy."""
    if strategy == "fixed":
        return chunk_fixed_size(text, chunk_size, overlap)
    return chunk_section_aware(text, chunk_size, overlap)


def process_pdfs(pdf_dir: Path) -> tuple[list, "SentenceTransformer"]:
    """Main ingestion: process all PDFs, return chunks and embedding model."""
    from sentence_transformers import SentenceTransformer  # lazy import: keeps torch out of startup path

    print(f"Loading embedding model: {EMBEDDING_MODEL}")
    embed_model = SentenceTransformer(EMBEDDING_MODEL)

    all_chunks = []
    all_texts = []
    pdf_files = sorted(pdf_dir.rglob("*.pdf"))
    print(f"Found {len(pdf_files)} PDFs in {pdf_dir}")

    if not pdf_files:
        print(f"WARNING: No PDFs found in {pdf_dir}. Make sure PDFs are placed there.")
        return [], embed_model

    _seen_names: dict[str, Path] = {}
    for pdf_path in pdf_files:
        # Dedup: skip if same filename already processed (handles cross-dir copies)
        if pdf_path.name in _seen_names:
            print(f"Skipping duplicate: {pdf_path.name} (duplicate of {_seen_names[pdf_path.name]})")
            continue
        _seen_names[pdf_path.name] = pdf_path
        print(f"Processing: {pdf_path.name}")
        try:
            doc = fitz.open(pdf_path)
            rel_path = str(pdf_path.relative_to(pdf_dir))
            doc_info = extract_pdf_info(pdf_path)

            # Build per-page character offsets for accurate page mapping
            page_texts = []
            page_offsets = []
            offset = 0
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text("text")
                text = clean_text(text)
                marker = f"[PAGE {page_num + 1}]\n{text}"
                page_texts.append(marker)
                page_offsets.append(offset)
                offset += len(marker) + 2  # +2 for \n\n join

            full_text = "\n\n".join(page_texts)
            chunks = chunk_text(full_text, CHUNKING_STRATEGY, CHUNK_SIZE, CHUNK_OVERLAP)

            for i, chunk in enumerate(chunks):
                # Find chunk's actual character position in full_text
                chunk_snippet = chunk["text"][:80]
                char_pos = full_text.find(chunk_snippet)
                if char_pos == -1:
                    char_pos = 0
                page_num = 1
                for p in range(len(doc)):
                    next_offset = page_offsets[p + 1] if p + 1 < len(doc) else len(full_text)
                    if char_pos < next_offset:
                        page_num = p + 1
                        break

                metadata = {
                    "doc_name": doc_info["title"] or pdf_path.stem,
                    "doc_path": str(pdf_path),
                    "page": page_num,
                    "section": chunk.get("heading", ""),
                    "date": doc_info.get("creation_date", ""),
                    "superseded": False,
                    "chunk_index": len(all_chunks),
                    "rel_path": rel_path,
                }
                chunk_with_meta = {**chunk, **metadata}
                all_chunks.append(chunk_with_meta)
                all_texts.append(chunk["text"])

            doc.close()
            print(f"  → {len(chunks)} chunks created")
        except Exception as e:
            print(f"  ERROR processing {pdf_path.name}: {e}")

    if not all_chunks:
        print("No chunks created. Aborting.")
        return [], embed_model

    print(f"\nTotal chunks: {len(all_chunks)}")

    # Build embeddings
    print("Embedding chunks...")
    embeddings = embed_model.encode(all_texts, show_progress_bar=True, batch_size=32)
    print(f"Embedding shape: {embeddings.shape}")

    # Normalize for cosine similarity
    import numpy as np
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    embeddings = embeddings / np.maximum(norms, 1e-8)

    # Save metadata
    with open(METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, indent=2, ensure_ascii=False)
    print(f"Metadata saved: {METADATA_PATH} ({len(all_chunks)} chunks)")

    # Build FAISS index
    dimension = embeddings.shape[1]
    faiss_index = faiss.IndexFlatIP(dimension)
    faiss_index.add(embeddings.astype("float32"))
    faiss.write_index(faiss_index, str(FAISS_PATH))
    print(f"FAISS index saved: {FAISS_PATH}")

    # Build BM25 index
    tokenized_docs = [text.lower().split() for text in all_texts]
    bm25 = BM25Okapi(tokenized_docs)
    with open(BM25_INDEX_PATH, "wb") as f:
        pickle.dump(bm25, f)
    print(f"BM25 index saved: {BM25_INDEX_PATH}")

    print("\n✅ Ingestion complete!")
    return all_chunks, embed_model


if __name__ == "__main__":
    process_pdfs(PDF_DIR)
