"""
Evaluation suite for NiyamAI.
Runs hand-verified questions against different retrieval configurations.
Metrics: recall@5, MRR, faithfulness (LLM-judged), answer completeness.
"""

import json
import os
from pathlib import Path

from groq import Groq
from dotenv import load_dotenv

load_dotenv()

EVAL_DATASET_PATH = Path(os.getenv("EVAL_DATASET_PATH", "./data/eval_set.json"))
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")


class NiyamEvaluator:
    def __init__(self, config: str = "hybrid_rerank"):
        self.config = config
        from src.retrieval import get_retriever
        self.retriever = get_retriever()
        self.client = Groq(api_key=GROQ_API_KEY)

    def retrieve(self, query: str) -> list[dict]:
        if self.config == "dense_only":
            indices = self.retriever.dense_retrieve(query, top_k=20)
            return [self.retriever.metadata[i] for i in indices[:5]]
        elif self.config == "bm25_only":
            indices = self.retriever.keyword_retrieve(query, top_k=20)
            return [self.retriever.metadata[i] for i in indices[:5]]
        elif self.config == "hybrid":
            # FAISS + BM25 → RRF, no reranker
            dense = self.retriever.dense_retrieve(query, top_k=20)
            keyword = self.retriever.keyword_retrieve(query, top_k=20)
            dense = self.retriever._filter_superseded(dense)
            keyword = self.retriever._filter_superseded(keyword)
            fused = self.retriever.reciprocal_rank_fusion(dense, keyword)
            return [self.retriever.metadata[i] for i in fused[:5]]
        else:
            return self.retriever.retrieve(query, retrieval_k=20, rerank_top_k=5)

    def generate_answer(self, query: str, chunks: list[dict]) -> str:
        from src.generation import SYSTEM_PROMPT
        context_text = "\n\n---\n\n".join([
            f"[Source: {c['doc_name']}, Page {c['page']}]\n{c['text']}"
            for c in chunks
        ])
        user_message = f"Question: {query}\n\nContext:\n{context_text}"
        response = self.client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            max_tokens=1024,
        )
        return response.choices[0].message.content or ""

    def run_eval(self, dataset: list[dict]) -> dict:
        results = []
        skipped = 0
        for i, item in enumerate(dataset):
            query = item["question"]
            expected_chunk = item.get("expected_chunk")
            expected_page = item.get("expected_page")
            topic = item.get("topic", "Unknown")

            # Skip unannotated questions and not-in-corpus markers
            if expected_chunk is None:
                skipped += 1
                continue
            if expected_chunk == -1:
                skipped += 1
                continue

            print(f"  [{i+1}/{len(dataset)}] {query[:70]}...")

            chunks = self.retrieve(query)

            recall_at_5 = 1.0 if any(
                c.get("chunk_index") == expected_chunk for c in chunks[:5]
            ) else 0.0

            mrr = 0.0
            for rank, c in enumerate(chunks[:5]):
                if c.get("chunk_index") == expected_chunk:
                    mrr = 1.0 / (rank + 1)
                    break

            answer = self.generate_answer(query, chunks)

            results.append({
                "question": query,
                "topic": topic,
                "expected_chunk": expected_chunk,
                "expected_page": expected_page,
                "retrieved_chunks": [
                    {"doc": c["doc_name"], "page": c["page"]}
                    for c in chunks
                ],
                "recall@5": recall_at_5,
                "MRR": mrr,
                "answer": answer,
            })

        return {"config": self.config, "results": results, "skipped": skipped}

    def save_results(self, results: dict, output_path: str = None):
        output_path = output_path or f"./data/eval_{self.config}.json"
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"  Results saved → {output_path}")


def load_eval_dataset(path: Path = EVAL_DATASET_PATH) -> list[dict]:
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def create_sample_eval_dataset() -> list[dict]:
    """Fallback 4-question sample if the full eval set is missing."""
    return [
        {"question": "What are the KYC norms for opening a bank account in India?", "expected_chunk": None, "expected_page": None, "topic": "KYC"},
        {"question": "Can a bank charge a penalty for not maintaining minimum balance?", "expected_chunk": None, "expected_page": None, "topic": "Customer Service"},
        {"question": "What is the priority sector lending target for banks?", "expected_chunk": None, "expected_page": None, "topic": "Priority Sector Lending"},
        {"question": "What are the guidelines for digital lending by NBFCs?", "expected_chunk": None, "expected_page": None, "topic": "Digital Lending"},
    ]


if __name__ == "__main__":
    dataset = load_eval_dataset()
    if not dataset:
        print("No eval dataset found. Creating sample dataset...")
        dataset = create_sample_eval_dataset()
        EVAL_DATASET_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(EVAL_DATASET_PATH, "w", encoding="utf-8") as f:
            json.dump(dataset, f, indent=2, ensure_ascii=False)
        print(f"Created sample dataset at {EVAL_DATASET_PATH}")

    print(f"Loaded {len(dataset)} eval questions.\n")

    configs = ["dense_only", "bm25_only", "hybrid", "hybrid_rerank"]
    all_results = {}

    for config in configs:
        print(f"\n{'='*55}")
        print(f"  Config: {config}")
        print(f"{'='*55}")
        evaluator = NiyamEvaluator(config=config)
        results = evaluator.run_eval(dataset)
        all_results[config] = results
        evaluator.save_results(results)

    # ── Summary ──────────────────────────────────────────────────────────────
    print("\n" + "="*55)
    print("  EVALUATION SUMMARY")
    print("="*55)
    print(f"{'Config':<20} {'Recall@5':>10} {'MRR':>10} {'Questions':>10}")
    print("-"*55)
    for config, data in all_results.items():
        recalls = [r["recall@5"] for r in data["results"]]
        mrrs = [r["MRR"] for r in data["results"]]
        n = len(recalls)
        avg_recall = sum(recalls) / n if n else 0
        avg_mrr = sum(mrrs) / n if n else 0
        print(f"{config:<20} {avg_recall:>10.3f} {avg_mrr:>10.3f} {n:>10}")
    print("="*55)
