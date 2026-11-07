"""Evaluation suite for NiyamAI retrieval quality.
Uses topic-grounded Recall@K and Precision@K since ground-truth chunks are null.
Produces data/eval_report.json and prints a summary table.
Run: python -m scripts.eval
"""

import json
import sys
from collections import Counter
from pathlib import Path

# Allow running from project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

EVAL_PATH = Path("data/eval_set.json")
REPORT_PATH = Path("data/eval_report.json")


def run_eval():
    dataset = json.loads(EVAL_PATH.read_text(encoding="utf-8"))

    from src.retrieval import get_retriever
    retriever = get_retriever()

    results = []
    correct_top1 = 0
    correct_top3 = 0
    correct_top5 = 0
    per_topic_recall = Counter({"total": 0, "correct_top1": 0})

    for i, item in enumerate(dataset):
        query = item["question"]
        topic = item["topic"]
        chunks = retriever.retrieve(query, top_k=5)

        # Ground truth: does any retrieved chunk come from the expected topic's directory?
        found_in_topic = False
        top1_matches = False
        for c in chunks:
            rel = c.get("rel_path", "").replace("\\", "/")
            matches = rel.startswith(f"{topic}/") or topic in c.get("doc_name", "")
            if matches:
                found_in_topic = True
                break

        if len(chunks) > 0 and (
            rel.startswith(f"{topic}/") or topic in chunks[0].get("doc_name", "")
        ):
            top1_matches = True
        if len(chunks) >= 3:
            for c in chunks[:3]:
                rel = c.get("rel_path", "").replace("\\", "/")
                if rel.startswith(f"{topic}/") or topic in c.get("doc_name", ""):
                    break
            else:
                pass  # not top3
        else:
            pass

        # Simpler: check top-1, top-3, top-5 individually
        top1_ok = False
        top3_ok = False
        top5_ok = False
        for rank, c in enumerate(chunks):
            rel = c.get("rel_path", "").replace("\\", "/")
            name = c.get("doc_name", "")
            hit = rel.startswith(f"{topic}/") or topic in name
            if rank == 0 and hit:
                top1_ok = True
            if rank < 3 and hit:
                top3_ok = True
            if rank < 5 and hit:
                top5_ok = True

        recall_1 = 1.0 if top1_ok else 0.0
        recall_3 = 1.0 if top3_ok else 0.0
        recall_5 = 1.0 if top5_ok else 0.0

        per_topic_recall[(topic, "top1")] += 1 if top1_ok else 0
        per_topic_recall[(topic, "top3")] += 1 if top3_ok else 0
        per_topic_recall[(topic, "top5")] += 1 if top5_ok else 0
        per_topic_recall[(topic, "total")] += 1

        correct_top1 += 1 if top1_ok else 0
        correct_top3 += 1 if top3_ok else 0
        correct_top5 += 1 if top5_ok else 0

        results.append({
            "question": query,
            "topic": topic,
            "recall@1": recall_1,
            "recall@3": recall_3,
            "recall@5": recall_5,
            "top_docs": [c["doc_name"] for c in chunks[:3]],
        })
        print(f"  [{i+1}/{len(dataset)}] {query[:60]}... R@1={recall_1}, R@3={recall_3}, R@5={recall_5}")

    report = {
        "config": "hybrid_rerank",
        "total_questions": len(dataset),
        "recall@1": round(correct_top1 / len(dataset), 3) if dataset else 0,
        "recall@3": round(correct_top3 / len(dataset), 3) if dataset else 0,
        "recall@5": round(correct_top5 / len(dataset), 3) if dataset else 0,
        "per_topic": {},
        "details": results,
    }

    # Per-topic breakdown
    seen_topics = set()
    for r in results:
        t = r["topic"]
        if t in seen_topics:
            continue
        seen_topics.add(t)
        topic_results = [x for x in results if x["topic"] == t]
        report["per_topic"][t] = {
            "count": len(topic_results),
            "recall@1": round(sum(x["recall@1"] for x in topic_results) / len(topic_results), 3),
            "recall@3": round(sum(x["recall@3"] for x in topic_results) / len(topic_results), 3),
            "recall@5": round(sum(x["recall@5"] for x in topic_results) / len(topic_results), 3),
        }

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nReport saved -> {REPORT_PATH}")

    # Summary table
    print("\n" + "=" * 60)
    print("  EVALUATION SUMMARY")
    print("=" * 60)
    print(f"{'Metric':<15} {'Value':>8}")
    print("-" * 60)
    print(f"{'Recall@1':<15} {report['recall@1']:>8.3f}")
    print(f"{'Recall@3':<15} {report['recall@3']:>8.3f}")
    print(f"{'Recall@5':<15} {report['recall@5']:>8.3f}")
    print("-" * 60)
    print(f"{'Per-topic Recall@1':}")
    for topic, m in sorted(report["per_topic"].items()):
        print(f"  {topic:<25} {m['recall@1']:.3f} ({m['count']} questions)")
    print("=" * 60)
    return report


if __name__ == "__main__":
    run_eval()
