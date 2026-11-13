"""
Hybrid retrieval: FAISS (dense) + BM25 (keyword) → RRF fusion → cross-encoder rerank.
Uses BM25-only mode by default to keep memory under 512 MB (Render free tier).
Set USE_DENSE=1 to enable FAISS dense retrieval (requires sentence-transformers/torch).
"""

import json
import os
import pickle
import re
from pathlib import Path

import numpy as np
import faiss
from rank_bm25 import BM25Okapi

from dotenv import load_dotenv
load_dotenv()

# ── Acronym expansion for BM25 query preprocessing ──────────────────────────
# Maps common RBI-domain abbreviations to their expanded forms so BM25 can
# match passages that use the full term rather than the abbreviation.
ACRONYM_MAP = {
    "kyc": "know your customer",
    "aml": "anti money laundering",
    "cdd": "customer due diligence",
    "ckycr": "central kyc registry",
    "ovd": "officially valid document",
    "psl": "priority sector lending",
    "nbfc": "non banking financial company",
    "emi": "equated monthly instalment",
    "upi": "unified payments interface",
    "neft": "national electronic funds transfer",
    "rtgs": "real time gross settlement",
    "imps": "immediate payment service",
    "ppi": "prepaid payment instrument",
    "pa": "payment aggregator",
    "pg": "payment gateway",
    "ews": "early warning signal",
    "lcr": "liquidity coverage ratio",
    "npa": "non performing asset",
    "msme": "micro small medium enterprise",
    "rrb": "regional rural bank",
    "sfb": "small finance bank",
    "ucb": "urban cooperative bank",
    "lrs": "liberalised remittance scheme",
    "fema": "foreign exchange management act",
    "pmla": "prevention of money laundering act",
    "vcip": "video based customer identification process",
    "re": "regulated entity",
    "rbi": "reserve bank of india",
    "ird": "interest rate derivative",
    "cbs": "core banking solution",
    "atm": "automated teller machine",
    "pos": "point of sale",
}

# Canonical sector names map: lowercased user input → exact directory name
SECTOR_NAME_MAP = {
    "kyc": "KYC",
    "kyc & aml": "KYC",
    "kyc and aml": "KYC",
    "digital payment": "Digital Payment",
    "digital payments": "Digital Payment",
    "digital banking": "Digital Banking",
    "fraud": "Fraud Risk Management",
    "fraud risk": "Fraud Risk Management",
    "fraud risk management": "Fraud Risk Management",
    "priority sector": "Priority sector lending",
    "priority sector lending": "Priority sector lending",
    "psl": "Priority sector lending",
}

from src.ingestion import METADATA_PATH, FAISS_PATH, BM25_INDEX_PATH, EMBEDDING_MODEL, RERANKER_MODEL

USE_DENSE = os.getenv("USE_DENSE", "0").strip() == "1"

RETRIEVAL_K = int(os.getenv("RETRIEVAL_K", "20").strip())
RERANK_TOP_K = int(os.getenv("RERANK_TOP_K", "5").strip())


class NiyamRetriever:
    def __init__(self):
        self.metadata = []
        self.embed_model = None
        self.faiss_index = None
        self.bm25 = None
        self.reranker = None
        self._loaded = False

    def load(self):
        """Load all indexes and metadata. Gracefully handles missing indexes."""
        print("Loading NiyamAI retriever...")
        print(f"  BM25_INDEX_PATH resolved: {BM25_INDEX_PATH.resolve()}")
        print(f"  METADATA_PATH resolved:   {METADATA_PATH.resolve()}")
        print(f"  BM25 exists: {BM25_INDEX_PATH.exists()}, Metadata exists: {METADATA_PATH.exists()}")

        if not METADATA_PATH.exists() or not BM25_INDEX_PATH.exists():
            print("  WARNING: Indexes not found. App will start but queries will return no results.")
            print("  Run: python -m src.ingestion  to build the indexes.")
            self._loaded = True  # mark loaded so we don't retry on every request
            return

        # Load metadata
        with open(METADATA_PATH, "r", encoding="utf-8") as f:
            self.metadata = json.load(f)
        print(f"  Metadata: {len(self.metadata)} chunks")

        # Load BM25 (always)
        with open(BM25_INDEX_PATH, "rb") as f:
            self.bm25 = pickle.load(f)
        print("  BM25 index loaded")

        # Load FAISS + embedding model only if USE_DENSE=1
        if USE_DENSE:
            # Lazy imports to avoid torch (192MB) unless dense retrieval is requested
            from sentence_transformers import SentenceTransformer, CrossEncoder
            self.faiss_index = faiss.read_index(str(FAISS_PATH))
            print(f"  FAISS index: {self.faiss_index.ntotal} vectors")
            self.embed_model = SentenceTransformer(EMBEDDING_MODEL)
            print(f"  Embedding model: {EMBEDDING_MODEL}")
            self.reranker = CrossEncoder(RERANKER_MODEL)
            print(f"  Reranker: {RERANKER_MODEL}")
        else:
            self.faiss_index = None
            self.embed_model = None
            self.reranker = None
            print("  Dense retrieval SKIPPED (USE_DENSE=0, BM25-only mode for low memory)")

        self._loaded = True
        print("Retriever ready.")

    def _expand_query(self, query: str) -> str:
        """Expand acronyms in the query for better BM25 recall."""
        tokens = query.lower().split()
        expanded = []
        for token in tokens:
            # Strip punctuation for lookup
            clean = re.sub(r"[^\w]", "", token)
            if clean in ACRONYM_MAP:
                expanded.append(token)
                expanded.append(ACRONYM_MAP[clean])
            else:
                expanded.append(token)
        return " ".join(expanded)

    def _normalize_sector(self, sector: str) -> str | None:
        """Normalize user-supplied sector name to the exact directory name."""
        if not sector or sector.lower() == "all":
            return None
        normalized = SECTOR_NAME_MAP.get(sector.lower().strip())
        if normalized:
            return normalized
        # Fallback: case-insensitive prefix match against known dirs
        for canonical in SECTOR_NAME_MAP.values():
            if canonical.lower() == sector.lower():
                return canonical
        return sector  # pass through as-is so existing exact matches still work

    def _dedup_chunks(self, chunk_indices: list[int]) -> list[int]:
        """Remove duplicate (doc_name, page) pairs, keeping first occurrence."""
        seen: set[tuple] = set()
        deduped = []
        for i in chunk_indices:
            key = (self.metadata[i].get("doc_name", ""), self.metadata[i].get("page", -1))
            if key not in seen:
                seen.add(key)
                deduped.append(i)
        return deduped

    def _filter_superseded(self, chunk_indices: list[int]) -> list[int]:
        """Drop superseded chunks."""
        return [i for i in chunk_indices if not self.metadata[i].get("superseded", False)]

    def dense_retrieve(self, query: str, top_k: int = 50) -> list[int]:
        """FAISS dense retrieval. Requires USE_DENSE=1."""
        if not self.embed_model or not self.faiss_index:
            return []
        query_emb = self.embed_model.encode([query])
        query_emb = query_emb / np.linalg.norm(query_emb)  # normalize
        scores, indices = self.faiss_index.search(query_emb.astype(np.float32), top_k)
        return indices[0].tolist()

    def keyword_retrieve(self, query: str, top_k: int = 50) -> list[int]:
        """BM25 keyword retrieval with acronym expansion."""
        expanded = self._expand_query(query)
        query_terms = expanded.lower().split()  # must match ingestion tokenization
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
        """Cross-encoder reranking. Requires USE_DENSE=1."""
        if not self.reranker:
            # BM25-only mode: return top_k candidates directly
            return candidate_indices[:top_k]
        pool = candidate_indices[:max(top_k * 3, 12)]
        candidates = [self.metadata[i]["text"] for i in pool]
        pairs = [[query, text] for text in candidates]
        scores = self.reranker.predict(pairs)
        scored = list(zip(pool, scores))
        scored.sort(key=lambda x: x[1], reverse=True)
        return [idx for idx, _ in scored[:top_k]]

    def retrieve(self, query: str, retrieval_k: int = None, rerank_top_k: int = None, top_k: int = None, sector: str = None) -> list[dict]:
        """Full retrieval pipeline: dense + keyword → RRF → filter → rerank → dedup."""
        if not query or not query.strip():
            return []
        retrieval_k = retrieval_k or RETRIEVAL_K
        rerank_top_k = top_k or rerank_top_k or RERANK_TOP_K

        # Step 1: Keyword (always) + Dense (only if enabled)
        keyword_results = self.keyword_retrieve(query, top_k=retrieval_k)
        if USE_DENSE:
            dense_results = self.dense_retrieve(query, top_k=retrieval_k)
            dense_results = self._filter_superseded(dense_results)
        else:
            dense_results = []

        # Step 2: Filter superseded
        keyword_results = self._filter_superseded(keyword_results)

        # Step 3: RRF fusion
        fused = self.reciprocal_rank_fusion(dense_results, keyword_results)
        if not fused:
            fused = keyword_results  # BM25-only fallback

        # Step 3.5: Optional sector filter (normalized)
        normalized_sector = self._normalize_sector(sector)
        if normalized_sector:
            filtered_fused = [
                i for i in fused
                if self.metadata[i].get("rel_path", "").replace("\\", "/").startswith(f"{normalized_sector}/")
            ]
            # Only apply filter if it yields results; otherwise return unfiltered
            if filtered_fused:
                fused = filtered_fused

        # Step 4: Rerank
        reranked = self.rerank(query, fused, top_k=rerank_top_k)

        # Step 5: Deduplicate on (doc_name, page) to avoid redundant citations
        reranked = self._dedup_chunks(reranked)

        # Return full metadata for top results
        return [self.metadata[i] for i in reranked]

    def retrieve_raw(self, query: str, retrieval_k: int = None, rerank_top_k: int = None) -> dict:
        """Return retrieval details for debugging."""
        retrieval_k = retrieval_k or RETRIEVAL_K
        rerank_top_k = rerank_top_k or RERANK_TOP_K

        keyword_results = self.keyword_retrieve(query, top_k=retrieval_k)
        if USE_DENSE:
            dense_results = self.dense_retrieve(query, top_k=retrieval_k)
            dense_results = self._filter_superseded(dense_results)
        else:
            dense_results = []
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
