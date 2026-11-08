"""
Hybrid retrieval: FAISS (dense) + BM25 (keyword) → RRF fusion → cross-encoder rerank.
"""

import pickle
from pathlib import Path

import faiss
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder
import numpy as np

from dotenv import load_dotenv
load_dotenv()

from src.ingestion import METADATA_PATH, FAISS_PATH, BM25_INDEX_PATH, EMBEDDING_MODEL, RERANKER_MODEL
import json

RETRIEVAL_K = int(getattr(__import__("os"), "environ").get("RETRIEVAL_K", "20"))
RERANK_TOP_K = int(getattr(__import__("os"), "environ").get("RERANK_TOP_K", "5"))


class NiyamRetriever:
    def __init__(self):
        self.metadata = []
        self.embed_model = None
        self.faiss_index = None
        self.bm25 = None
        self.reranker = None
        self._loaded = False

    def load(self):
        """Load all indexes and metadata."""
        print("Loading NiyamAI retriever...")

        # Load metadata
        with open(METADATA_PATH, "r", encoding="utf-8") as f:
            self.metadata = json.load(f)
        print(f"  Metadata: {len(self.metadata)} chunks")

        # Load FAISS
        self.faiss_index = faiss.read_index(str(FAISS_PATH))
        print(f"  FAISS index: {self.faiss_index.ntotal} vectors")

        # Load BM25
        with open(BM25_INDEX_PATH, "rb") as f:
            self.bm25 = pickle.load(f)
        print("  BM25 index loaded")

        # Load reranker (commented out for Render free-tier <512MB limits; skips cross-encoder ~92MB)
        self.reranker = None
        print("  Reranker: SKIPPED (save ~92MB for low-memory deploy)")

        self.embed_model = SentenceTransformer(EMBEDDING_MODEL)
        self._loaded = True
        print("Retriever ready.")

    def _filter_superseded(self, chunk_indices: list[int]) -> list[int]:
        """Drop superseded chunks."""
        return [i for i in chunk_indices if not self.metadata[i].get("superseded", False)]

    def dense_retrieve(self, query: str, top_k: int = 50) -> list[int]:
        """FAISS dense retrieval."""
        query_emb = self.embed_model.encode([query])
        query_emb = query_emb / np.linalg.norm(query_emb)  # normalize
        scores, indices = self.faiss_index.search(query_emb.astype(np.float32), top_k)
        return indices[0].tolist()

    def keyword_retrieve(self, query: str, top_k: int = 50) -> list[int]:
        """BM25 keyword retrieval."""
        query_terms = query.lower().split()  # must match ingestion tokenization
        scores = self.bm25.get_scores(query_terms)
        top_indices = np.argsort(scores)[::-1][:top_k].tolist()
        return top_indices

    def reciprocal_rank_fusion(self, dense_indices: list[int], keyword_indices: list[int], k: int = 60) -> list[int]:
        """Combine two ranked lists using Reciprocal Rank Fusion."""
        rrf_score = {}
        for i, idx in enumerate(dense_indices):
            rrf_score[idx] = rrf_score.get(idx, 0) + 1 / (i + k)
        for i, idx in enumerate(keyword_indices):
            rrf_score[idx] = rrf_score.get(idx, 0) + 1 / (i + k)
        sorted_indices = sorted(rrf_score.keys(), key=lambda x: rrf_score[x], reverse=True)
        return sorted_indices

    def rerank(self, query: str, candidate_indices: list[int], top_k: int = 5) -> list[int]:
        """Cross-encoder reranking (optimized for low-latency CPU inference)."""
        pool = candidate_indices[:max(top_k * 3, 12)]
        candidates = [self.metadata[i]["text"] for i in pool]
        pairs = [[query, text] for text in candidates]
        scores = self.reranker.predict(pairs)
        scored = list(zip(pool, scores))
        scored.sort(key=lambda x: x[1], reverse=True)
        return [idx for idx, _ in scored[:top_k]]

    def retrieve(self, query: str, retrieval_k: int = None, rerank_top_k: int = None, top_k: int = None, sector: str = None) -> list[dict]:
        """Full retrieval pipeline: dense + keyword → RRF → filter → rerank."""
        if not query or not query.strip():
            return []
        retrieval_k = retrieval_k or RETRIEVAL_K
        rerank_top_k = top_k or rerank_top_k or RERANK_TOP_K

        # Step 1: Dense + Keyword retrieval
        dense_results = self.dense_retrieve(query, top_k=retrieval_k)
        keyword_results = self.keyword_retrieve(query, top_k=retrieval_k)

        # Step 2: Filter superseded
        dense_results = self._filter_superseded(dense_results)
        keyword_results = self._filter_superseded(keyword_results)

        # Step 3: RRF fusion
        fused = self.reciprocal_rank_fusion(dense_results, keyword_results)

        # Step 3.5: Optional sector filter
        if sector and sector.lower() != "all":
            sec_lower = sector.lower()
            filtered_fused = [
                i for i in fused
                if self.metadata[i].get("rel_path", "").replace("\\", "/").startswith(f"{sector}/")
            ]
            fused = filtered_fused

        # Step 4: Rerank
        reranked = self.rerank(query, fused, top_k=rerank_top_k)

        # Return full metadata for top results
        return [self.metadata[i] for i in reranked]

    def retrieve_raw(self, query: str, retrieval_k: int = None, rerank_top_k: int = None) -> dict:
        """Return retrieval details for debugging."""
        retrieval_k = retrieval_k or RETRIEVAL_K
        rerank_top_k = rerank_top_k or RERANK_TOP_K

        dense_results = self.dense_retrieve(query, top_k=retrieval_k)
        keyword_results = self.keyword_retrieve(query, top_k=retrieval_k)
        dense_results = self._filter_superseded(dense_results)
        keyword_results = self._filter_superseded(keyword_results)
        fused = self.reciprocal_rank_fusion(dense_results, keyword_results)
        reranked = self.rerank(query, fused, top_k=rerank_top_k)

        return {
            "dense": [self.metadata[i] for i in dense_results[:5]],
            "keyword": [self.metadata[i] for i in keyword_results[:5]],
            "fused_count": len(fused),
            "final": [self.metadata[i] for i in reranked],
        }


# Singleton instance
_retriever = None

def get_retriever() -> NiyamRetriever:
    global _retriever
    if _retriever is None:
        _retriever = NiyamRetriever()
        _retriever.load()
    return _retriever
