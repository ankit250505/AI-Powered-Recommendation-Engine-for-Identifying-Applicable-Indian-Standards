from __future__ import annotations

import argparse
import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
QUERY_EXAMPLES_CSV = ROOT / "data" / "procurement_query_examples.csv"

import sys

sys.path.insert(0, str(ROOT))

from src.hybrid_search import HybridSearchEngine  # noqa: E402
from src.embedding_search import EmbeddingSearchEngine  # noqa: E402
from src.standards_search import load_standards, search_standards  # noqa: E402


def load_examples(split: str) -> list[dict[str, str]]:
    with QUERY_EXAMPLES_CSV.open(newline="", encoding="utf-8") as examples:
        rows = list(csv.DictReader(examples))
    return [row for row in rows if row["split"] == split]


def evaluate(split: str, limit: int, mode: str) -> dict[str, float]:
    standards = load_standards()
    engine = None
    if mode == "hybrid":
        engine = HybridSearchEngine(standards)
    elif mode == "embedding":
        engine = EmbeddingSearchEngine(standards)
    examples = load_examples(split)

    top_1 = 0
    top_3 = 0
    top_5 = 0
    reciprocal_rank_total = 0.0

    for example in examples:
        if engine:
            results = engine.search(example["query_text"], limit=limit)
        else:
            results = search_standards(example["query_text"], standards=standards, limit=limit)
        result_codes = [result.standard["standard_code"] for result in results]
        target_code = example["target_standard_code"]

        if result_codes[:1] == [target_code]:
            top_1 += 1
        if target_code in result_codes[:3]:
            top_3 += 1
        if target_code in result_codes[:5]:
            top_5 += 1
        if target_code in result_codes:
            reciprocal_rank_total += 1 / (result_codes.index(target_code) + 1)

    total = len(examples)
    return {
        "examples": total,
        "top_1_accuracy": top_1 / total if total else 0.0,
        "top_3_accuracy": top_3 / total if total else 0.0,
        "top_5_accuracy": top_5 / total if total else 0.0,
        "mean_reciprocal_rank": reciprocal_rank_total / total if total else 0.0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate basic standards search.")
    parser.add_argument("--split", choices=["train", "validation", "test"], default="test")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--mode", choices=["keyword", "hybrid", "embedding"], default="keyword")
    args = parser.parse_args()

    metrics = evaluate(split=args.split, limit=args.limit, mode=args.mode)
    print(f"Split: {args.split}")
    print(f"Mode: {args.mode}")
    for key, value in metrics.items():
        if key == "examples":
            print(f"{key}: {value}")
        else:
            print(f"{key}: {value:.3f}")


if __name__ == "__main__":
    main()
