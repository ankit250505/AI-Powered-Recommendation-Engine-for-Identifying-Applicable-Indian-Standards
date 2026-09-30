from __future__ import annotations

import argparse
import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


SEARCH_FIELDS = (
    "title",
    "keywords",
    "related_terms",
    "procurement_examples",
    "embedding_text",
)

FIELD_WEIGHTS = {
    "title": 4.0,
    "keywords": 3.0,
    "related_terms": 2.0,
    "procurement_examples": 2.0,
    "embedding_text": 1.5,
}

DEFAULT_DATASET = Path(__file__).resolve().parents[1] / "data" / "indian_standards_seed.csv"
TOKEN_RE = re.compile(r"[a-z0-9]+(?:/[a-z0-9]+)?")
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "into",
    "is",
    "it",
    "of",
    "on",
    "or",
    "the",
    "to",
    "up",
    "use",
    "used",
    "with",
    "work",
    "works",
}


@dataclass(frozen=True)
class SearchResult:
    standard: dict[str, str]
    score: float
    matched_terms: list[str]
    matched_fields: list[str]


def normalize(text: str) -> str:
    return " ".join(TOKEN_RE.findall(text.lower()))


def tokenize(text: str) -> list[str]:
    tokens = TOKEN_RE.findall(text.lower())
    return [token for token in tokens if len(token) > 1 and token not in STOPWORDS]


def load_standards(csv_path: str | Path = DEFAULT_DATASET) -> list[dict[str, str]]:
    with Path(csv_path).open(newline="", encoding="utf-8") as dataset:
        return list(csv.DictReader(dataset))


def search_standards(
    query: str,
    standards: Iterable[dict[str, str]] | None = None,
    limit: int = 10,
    min_score: float = 1.0,
) -> list[SearchResult]:
    rows = list(standards) if standards is not None else load_standards()
    query_tokens = tokenize(query)
    normalized_query = normalize(query)

    if not query_tokens:
        return []

    results: list[SearchResult] = []

    for row in rows:
        score = 0.0
        matched_terms: set[str] = set()
        matched_fields: set[str] = set()

        for field in SEARCH_FIELDS:
            field_text = row.get(field, "")
            normalized_field = normalize(field_text)
            field_tokens = set(tokenize(field_text))

            if not normalized_field:
                continue

            if normalized_query and normalized_query in normalized_field:
                score += FIELD_WEIGHTS[field] * 3
                matched_terms.add(normalized_query)
                matched_fields.add(field)

            for token in query_tokens:
                if token in field_tokens:
                    score += FIELD_WEIGHTS[field]
                    matched_terms.add(token)
                    matched_fields.add(field)
                elif len(token) >= 4 and token in normalized_field:
                    score += FIELD_WEIGHTS[field] * 0.5
                    matched_terms.add(token)
                    matched_fields.add(field)

        normalized_code = normalize(row.get("standard_code", ""))
        code_tokens = set(tokenize(row.get("standard_code", "")))
        numeric_query_tokens = {token for token in query_tokens if token.isdigit()}
        if normalized_code and (
            normalized_query in normalized_code
            or bool(numeric_query_tokens.intersection(code_tokens))
        ):
            score += 8.0
            matched_terms.add(row.get("standard_code", ""))
            matched_fields.add("standard_code")

        if score >= min_score:
            results.append(
                SearchResult(
                    standard=row,
                    score=round(score, 2),
                    matched_terms=sorted(matched_terms),
                    matched_fields=sorted(matched_fields),
                )
            )

    return sorted(results, key=lambda item: item.score, reverse=True)[:limit]


def format_result(result: SearchResult, index: int) -> str:
    standard = result.standard
    return (
        f"{index}. {standard['standard_code']} - {standard['title']}\n"
        f"   Score: {result.score}\n"
        f"   Category: {standard['category']} / {standard['subcategory']}\n"
        f"   Matched fields: {', '.join(result.matched_fields)}\n"
        f"   Matched terms: {', '.join(result.matched_terms)}\n"
        f"   Why: {standard['scope_summary']}\n"
        f"   Example use: {standard['procurement_examples']}\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Search applicable Indian Standards.")
    parser.add_argument("query", help="Procurement specification or product description")
    parser.add_argument("--dataset", default=DEFAULT_DATASET, help="Path to standards CSV")
    parser.add_argument("--limit", type=int, default=10, help="Maximum results to show")
    parser.add_argument("--min-score", type=float, default=1.0, help="Minimum score to include")
    args = parser.parse_args()

    standards = load_standards(args.dataset)
    results = search_standards(args.query, standards=standards, limit=args.limit, min_score=args.min_score)

    if not results:
        print("No standards matched this query.")
        return

    for index, result in enumerate(results, start=1):
        print(format_result(result, index))


if __name__ == "__main__":
    main()
