"""
Interactive eval annotation tool for NiyamAI.

For each unannotated question it:
  1. Runs BM25 retrieval and shows the top-5 chunks with their text
  2. Asks you to pick the best matching chunk (1-5), skip (s), or mark as not-in-corpus (x)
  3. Saves your answer immediately to data/eval_set.json

Resume any time — already-annotated questions are skipped automatically.

Usage:
    python scripts/annotate_eval.py
    python scripts/annotate_eval.py --topic KYC       # filter to one topic
    python scripts/annotate_eval.py --reset           # clear all annotations and restart
"""

import argparse
import json
import os
import sys
from pathlib import Path

# ── make sure project root is on path ───────────────────────────────────────
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from dotenv import load_dotenv
load_dotenv()

from src.retrieval import get_retriever

EVAL_PATH = ROOT / "data" / "eval_set.json"
DISPLAY_WIDTH = 100


def load_dataset():
    with open(EVAL_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_dataset(dataset):
    with open(EVAL_PATH, "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2, ensure_ascii=False)


def hr(char="─"):
    print(char * DISPLAY_WIDTH)


def truncate(text, n=400):
    return text[:n] + "..." if len(text) > n else text


def annotate(topic_filter=None, reset=False):
    dataset = load_dataset()

    if reset:
        for item in dataset:
            item["expected_chunk"] = None
            item["expected_page"] = None
        save_dataset(dataset)
        print("All annotations cleared.\n")

    retriever = get_retriever()

    to_annotate = [
        (i, item) for i, item in enumerate(dataset)
        if item.get("expected_chunk") is None
        and (topic_filter is None or item.get("topic", "").lower() == topic_filter.lower())
    ]

    total = len(to_annotate)
    if total == 0:
        print("All questions already annotated! Run with --reset to start over.")
        return

    print(f"\n{'='*DISPLAY_WIDTH}")
    print(f"  NiyamAI Eval Annotator — {total} questions to annotate")
    if topic_filter:
        print(f"  Topic filter: {topic_filter}")
    print(f"{'='*DISPLAY_WIDTH}")
    print("  Controls:")
    print("   [1-5]  Select the chunk that best answers the question")
    print("   [s]    Skip (leave as null, come back later)")
    print("   [x]    Mark as not in corpus (sets expected_chunk = -1)")
    print("   [q]    Quit and save progress")
    print(f"{'='*DISPLAY_WIDTH}\n")

    annotated = 0

    for n, (idx, item) in enumerate(to_annotate, 1):
        query = item["question"]
        topic = item.get("topic", "")

        hr("═")
        print(f"  [{n}/{total}]  Topic: {topic}")
        print(f"  Q: {query}")
        hr()

        # Retrieve top-5 chunks via BM25
        chunks = retriever.retrieve(query, retrieval_k=20, rerank_top_k=5)

        if not chunks:
            print("  No chunks retrieved — marking as not in corpus (x)")
            dataset[idx]["expected_chunk"] = -1
            dataset[idx]["expected_page"] = -1
            save_dataset(dataset)
            annotated += 1
            continue

        # Display chunks
        for ci, chunk in enumerate(chunks, 1):
            hr("·")
            print(f"  [{ci}] {chunk['doc_name']}  |  Page {chunk['page']}"
                  + (f"  |  {chunk.get('section','')[:60]}" if chunk.get('section') else ""))
            hr("·")
            print(f"  chunk_index = {chunk['chunk_index']}")
            print()
            # Pretty-print text with word wrap
            words = chunk["text"].split()
            line = "  "
            for word in words[:120]:  # show up to ~120 words
                if len(line) + len(word) + 1 > DISPLAY_WIDTH:
                    print(line)
                    line = "  " + word + " "
                else:
                    line += word + " "
            if line.strip():
                print(line)
            if len(words) > 120:
                print("  ...")
            print()

        hr()

        # Get user input
        while True:
            raw = input(f"  Pick best chunk [1-{len(chunks)}], (s)kip, (x) not in corpus, (q)uit: ").strip().lower()

            if raw == "q":
                print(f"\nSaved. Annotated {annotated} questions this session.")
                return

            if raw == "s":
                print("  → Skipped\n")
                break

            if raw == "x":
                dataset[idx]["expected_chunk"] = -1
                dataset[idx]["expected_page"] = -1
                save_dataset(dataset)
                annotated += 1
                print("  → Marked as not in corpus\n")
                break

            if raw.isdigit() and 1 <= int(raw) <= len(chunks):
                chosen = chunks[int(raw) - 1]
                dataset[idx]["expected_chunk"] = chosen["chunk_index"]
                dataset[idx]["expected_page"] = chosen["page"]
                save_dataset(dataset)
                annotated += 1
                print(f"  → Saved: chunk {chosen['chunk_index']} (page {chosen['page']})\n")
                break

            print(f"  Invalid input. Enter 1-{len(chunks)}, s, x, or q.")

    print(f"\nDone! Annotated {annotated}/{total} questions.")

    # Print progress summary
    dataset = load_dataset()
    done = sum(1 for x in dataset if x.get("expected_chunk") is not None)
    not_corpus = sum(1 for x in dataset if x.get("expected_chunk") == -1)
    print(f"Overall: {done}/{len(dataset)} annotated ({not_corpus} marked not-in-corpus)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Annotate eval set with ground-truth chunk IDs")
    parser.add_argument("--topic", type=str, default=None,
                        help="Filter to a specific topic (e.g. KYC, 'Digital Payment')")
    parser.add_argument("--reset", action="store_true",
                        help="Clear all existing annotations and restart from scratch")
    args = parser.parse_args()
    annotate(topic_filter=args.topic, reset=args.reset)
