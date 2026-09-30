from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
QUALITY_REPORT = ROOT / "data" / "retrieval_quality.json"
sys.path.insert(0, str(ROOT))

from scripts.evaluate_basic_search import evaluate  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Fail when retrieval quality drops below release thresholds.")
    parser.add_argument("--split", choices=["validation", "test"], default="test")
    parser.add_argument("--mode", choices=["keyword", "hybrid"], default="hybrid")
    parser.add_argument("--min-top-1", type=float, default=0.90)
    parser.add_argument("--min-top-5", type=float, default=0.96)
    parser.add_argument("--min-mrr", type=float, default=0.93)
    args = parser.parse_args()

    metrics = evaluate(split=args.split, limit=10, mode=args.mode)
    checks = {
        "top_1_accuracy": args.min_top_1,
        "top_5_accuracy": args.min_top_5,
        "mean_reciprocal_rank": args.min_mrr,
    }
    failed = []
    for metric, threshold in checks.items():
        value = metrics[metric]
        print(f"{metric}: {value:.3f} (required: {threshold:.3f})")
        if value < threshold:
            failed.append(metric)

    if failed:
        raise SystemExit(f"Quality gate failed: {', '.join(failed)}")

    recorded = json.loads(QUALITY_REPORT.read_text(encoding="utf-8"))
    recorded_metrics = {
        "top_1_accuracy": recorded["top_1_accuracy"],
        "top_5_accuracy": recorded["top_5_accuracy"],
        "mean_reciprocal_rank": recorded["mean_reciprocal_rank"],
    }
    stale = [
        metric
        for metric, value in recorded_metrics.items()
        if abs(value - metrics[metric]) > 0.0005
    ]
    if args.split == "test" and args.mode == recorded["mode"] and stale:
        raise SystemExit(f"Recorded retrieval quality is stale: {', '.join(stale)}")
    print("Quality gate passed.")


if __name__ == "__main__":
    main()
