from __future__ import annotations

import re
from dataclasses import dataclass

from src.standards_search import SearchResult


SENTENCE_BOUNDARY_RE = re.compile(r"(?<=[.!?;])\s+")
MAX_CLAUSE_CHARS = 600
MIN_CLAUSE_CHARS = 12


@dataclass(frozen=True)
class DocumentMatch:
    result: SearchResult
    evidence_clauses: list[str]


def split_document_clauses(text: str, max_clauses: int = 80) -> list[str]:
    clauses: list[str] = []
    seen: set[str] = set()

    for raw_line in text.splitlines():
        line = " ".join(raw_line.split())
        if not line:
            continue

        for piece in SENTENCE_BOUNDARY_RE.split(line):
            piece = piece.strip()
            if len(piece) < MIN_CLAUSE_CHARS:
                continue

            for start in range(0, len(piece), MAX_CLAUSE_CHARS):
                clause = piece[start : start + MAX_CLAUSE_CHARS].strip()
                normalized = clause.casefold()
                if len(clause) >= MIN_CLAUSE_CHARS and normalized not in seen:
                    clauses.append(clause)
                    seen.add(normalized)
                    if len(clauses) >= max_clauses:
                        return clauses

    if not clauses and text.strip():
        clauses.append(" ".join(text.split())[:MAX_CLAUSE_CHARS])
    return clauses


def aggregate_clause_results(
    clause_results: list[tuple[str, list[SearchResult]]],
    limit: int,
) -> list[DocumentMatch]:
    by_standard: dict[str, dict] = {}

    for clause, results in clause_results:
        for rank, result in enumerate(results, start=1):
            standard_id = result.standard["id"]
            item = by_standard.setdefault(
                standard_id,
                {
                    "standard": result.standard,
                    "best_score": 0.0,
                    "rank_support": 0.0,
                    "matched_terms": set(),
                    "matched_fields": set(),
                    "evidence": [],
                },
            )
            item["best_score"] = max(item["best_score"], result.score)
            item["rank_support"] += 1 / rank
            item["matched_terms"].update(result.matched_terms)
            item["matched_fields"].update(result.matched_fields)
            item["evidence"].append((result.score, clause))

    matches: list[DocumentMatch] = []
    for item in by_standard.values():
        aggregate_score = item["best_score"] + max(0.0, item["rank_support"] - 1.0) * 5.0
        evidence = [
            clause
            for _, clause in sorted(item["evidence"], key=lambda evidence_item: evidence_item[0], reverse=True)[:3]
        ]
        matches.append(
            DocumentMatch(
                result=SearchResult(
                    standard=item["standard"],
                    score=round(aggregate_score, 2),
                    matched_terms=sorted(item["matched_terms"]),
                    matched_fields=sorted(item["matched_fields"]),
                ),
                evidence_clauses=evidence,
            )
        )

    return sorted(matches, key=lambda match: match.result.score, reverse=True)[:limit]
