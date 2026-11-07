"""Auto-populate expected_chunk and expected_page in eval_set.json using embeddings."""

import json
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer

EMBED_MODEL = "BAAI/bge-small-en-v1.5"
METADATA_PATH = Path("data/chunks/metadata.json")
EVAL_PATH = Path("data/eval_set.json")

print("Loading metadata...")
with open(METADATA_PATH, encoding="utf-8") as f:
    chunks = json.load(f)

print("Loading eval set...")
with open(EVAL_PATH, encoding="utf-8") as f:
    eval_set = json.load(f)

print(f"Embedding {len(chunks)} chunks with {EMBED_MODEL}...")
model = SentenceTransformer(EMBED_MODEL)
chunk_texts = [c["text"] for c in chunks]
chunk_embeddings = model.encode(chunk_texts, batch_size=64, show_progress_bar=True)
chunk_embeddings = chunk_embeddings / np.linalg.norm(chunk_embeddings, axis=1, keepdims=True)

print(f"Matching {len(eval_set)} questions...")
for item in eval_set:
    q = item["question"]
    q_emb = model.encode([q])[0]
    q_emb = q_emb / np.linalg.norm(q_emb)
    scores = chunk_embeddings @ q_emb
    best_idx = int(np.argmax(scores))
    best_chunk = chunks[best_idx]
    item["expected_chunk"] = best_chunk["chunk_index"]
    item["expected_page"] = best_chunk["page"]

Path(EVAL_PATH).parent.mkdir(parents=True, exist_ok=True)
with open(EVAL_PATH, "w", encoding="utf-8") as f:
    json.dump(eval_set, f, indent=2, ensure_ascii=False)

print(f"Saved {EVAL_PATH}")
print("Done.")
