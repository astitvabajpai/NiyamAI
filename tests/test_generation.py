"""Unit tests for generation pipeline."""

import os
from pathlib import Path

from src.generation import generate_answer


def test_system_prompt_structure():
    """System prompt has required sections."""
    from src.generation import SYSTEM_PROMPT
    assert "Summary" in SYSTEM_PROMPT
    assert "Key Provisions" in SYSTEM_PROMPT
    assert "Scope" in SYSTEM_PROMPT
    assert "References" in SYSTEM_PROMPT
    assert "CRITICAL RULES" in SYSTEM_PROMPT


def test_generate_answer_returns_string():
    """generate_answer yields strings."""
    chunks = [
        {
            "text": "Test context about KYC norms.",
            "doc_name": "KYC Master Direction",
            "page": 10,
            "section": "Section 4",
        }
    ]
    for token in generate_answer("What are KYC norms?", chunks, stream=True):
        assert isinstance(token, str)
        break


def test_env_vars_present():
    """Required env vars are set."""
    assert os.getenv("GROQ_API_KEY")
    assert os.getenv("EMBEDDING_MODEL") == "BAAI/bge-small-en-v1.5"
    assert os.getenv("RERANKER_MODEL") == "cross-encoder/ms-marco-MiniLM-L-6-v2"


if __name__ == "__main__":
    test_system_prompt_structure()
    test_generate_answer_returns_string()
    test_env_vars_present()
    print("Generation tests passed!")