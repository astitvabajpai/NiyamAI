"""Unit tests for NiyamAI retrieval pipeline."""

import json
import numpy as np
from pathlib import Path

from src.retrieval import NiyamRetriever, get_retriever


def test_retriever_loads():
    """Retriever loads without error."""
    retriever = NiyamRetriever()
    retriever.load()
    assert len(retriever.metadata) > 0
    assert retriever.faiss_index is not None
    assert retriever.bm25 is not None
    assert retriever.reranker is not None


def test_dense_retrieve():
    """Dense retrieval returns top-K indices."""
    retriever = get_retriever()
    indices = retriever.dense_retrieve("KYC norms", top_k=10)
    assert len(indices) == 10
    assert all(0 <= i < len(retriever.metadata) for i in indices)


def test_keyword_retrieve():
    """BM25 keyword retrieval returns top-K indices."""
    retriever = get_retriever()
    indices = retriever.keyword_retrieve("KYC", top_k=10)
    assert len(indices) == 10
    assert all(0 <= i < len(retriever.metadata) for i in indices)


def test_rrf_fusion():
    """Reciprocal Rank Fusion combines two lists correctly."""
    retriever = NiyamRetriever()
    retriever.load()
    dense = [10, 5, 20, 30]
    keyword = [5, 15, 10, 40]
    fused = retriever.reciprocal_rank_fusion(dense, keyword)
    # 5 should be highest (rank 2 in dense, rank 1 in keyword)
    assert fused[0] == 5


def test_filter_superseded():
    """Superseded chunks are filtered out."""
    retriever = NiyamRetriever()
    retriever.load()
    # find one superseded chunk
    superseded_idx = None
    for i, m in enumerate(retriever.metadata):
        if m.get("superseded"):
            superseded_idx = i
            break
    if superseded_idx is not None:
        filtered = retriever._filter_superseded([superseded_idx, superseded_idx + 1])
        assert superseded_idx not in filtered


def test_retrieve_pipeline():
    """Full retrieval pipeline returns top 5 after rerank."""
    retriever = get_retriever()
    chunks = retriever.retrieve("What are KYC norms?", top_k=5)
    assert len(chunks) == 5
    assert all("text" in c for c in chunks)
    assert all("doc_name" in c for c in chunks)


def test_eval_set_loaded():
    """Eval set has expected fields."""
    eval_path = Path("data/eval_set.json")
    with open(eval_path, encoding="utf-8") as f:
        data = json.load(f)
    assert len(data) == 60
    for item in data:
        assert "question" in item
        assert "topic" in item
        # Check expected fields if present, skip null ground-truth fields
        if item.get("expected_chunk") is not None:
            assert isinstance(item["expected_chunk"], int)
        if item.get("expected_page") is not None:
            assert isinstance(item["expected_page"], int)


if __name__ == "__main__":
    test_retriever_loads()
    test_dense_retrieve()
    test_keyword_retrieve()
    test_rrf_fusion()
    test_filter_superseded()
    test_retrieve_pipeline()
    test_eval_set_loaded()
    print("All tests passed!")