from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
QUERY_EXAMPLES_CSV = ROOT / "data" / "procurement_query_examples.csv"
sys.path.insert(0, str(ROOT))

from src.embedding_search import EmbeddingSearchEngine  # noqa: E402
from src.standards_search import load_standards, search_standards  # noqa: E402


def load_examples(split: str) -> list[dict[str, str]]:
    with QUERY_EXAMPLES_CSV.open(newline="", encoding="utf-8") as examples_file:
        return [row for row in csv.DictReader(examples_file) if row["split"] == split]


def rank_metrics(rankings: list[list[str]], targets: list[str]) -> dict[str, float]:
    reciprocal_rank_total = 0.0
    top_1 = top_3 = top_5 = 0
    for result_codes, target in zip(rankings, targets):
        top_1 += target in result_codes[:1]
        top_3 += target in result_codes[:3]
        top_5 += target in result_codes[:5]
        if target in result_codes:
            reciprocal_rank_total += 1 / (result_codes.index(target) + 1)

    total = len(targets)
    return {
        "top_1": top_1 / total,
        "top_3": top_3 / total,
        "top_5": top_5 / total,
        "mrr": reciprocal_rank_total / total,
    }


def tune(split: str, weights: list[float]) -> list[tuple[float, dict[str, float]]]:
    standards = load_standards()
    examples = load_examples(split)
    engine = EmbeddingSearchEngine(standards)
    query_embeddings = engine.model.encode(
        [example["query_text"] for example in examples],
        batch_size=32,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    keyword_scores: list[list[float]] = []
    for example in examples:
        results = search_standards(
            example["query_text"], standards=standards, limit=len(standards), min_score=0
        )
        by_id = {result.standard["id"]: result.score for result in results}
        keyword_scores.append([by_id.get(standard["id"], 0.0) for standard in standards])

    targets = [example["target_standard_code"] for example in examples]
    outcomes: list[tuple[float, dict[str, float]]] = []
    for weight in weights:
        rankings = []
        for query_embedding, scores in zip(query_embeddings, keyword_scores):
            similarities = engine.embeddings @ query_embedding
            ranked_indexes = sorted(
                range(len(standards)),
                key=lambda index: scores[index] + max(0.0, float(similarities[index])) * weight,
                reverse=True,
            )[:10]
            rankings.append([standards[index]["standard_code"] for index in ranked_indexes])
        outcomes.append((weight, rank_metrics(rankings, targets)))
    return outcomes


def main() -> None:
    parser = argparse.ArgumentParser(description="Tune embedding/keyword blend on a fixed data split.")
    parser.add_argument("--split", choices=["train", "validation"], default="validation")
    parser.add_argument(
        "--weights",
        type=float,
        nargs="+",
        default=[5, 10, 15, 20, 25, 30, 40, 60, 100],
    )
    args = parser.parse_args()

    print("weight\ttop_1\ttop_3\ttop_5\tmrr")
    for weight, metrics in tune(args.split, args.weights):
        print(
            f"{weight:g}\t{metrics['top_1']:.3f}\t{metrics['top_3']:.3f}\t"
            f"{metrics['top_5']:.3f}\t{metrics['mrr']:.3f}"
        )


if __name__ == "__main__":
    main()
