from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from typing import Iterable

from src.standards_search import SearchResult, normalize, search_standards, tokenize


VECTOR_FIELDS = (
    "title",
    "category",
    "subcategory",
    "keywords",
    "related_terms",
    "procurement_examples",
    "scope_summary",
    "embedding_text",
)

SYNONYMS = {
    "ac": ["air", "conditioner", "hvac"],
    "bars": ["reinforcement", "steel", "rebar"],
    "bottle": ["container", "packaging"],
    "bulb": ["lamp", "lighting"],
    "cable": ["wire", "conductor"],
    "cement": ["concrete", "mortar"],
    "drain": ["drainage", "wastewater"],
    "drinking": ["potable", "water"],
    "fixture": ["luminaire", "fitting"],
    "fixtures": ["luminaires", "fittings"],
    "hydrant": ["fire", "hose", "reel"],
    "lamp": ["lighting", "bulb"],
    "light": ["lighting", "luminaire"],
    "lights": ["lighting", "luminaires"],
    "pipe": ["pipeline", "tube"],
    "pipes": ["pipeline", "tubes"],
    "potable": ["drinking", "water"],
    "rebar": ["reinforcement", "steel", "bars"],
    "rod": ["bar", "reinforcement", "steel"],
    "rods": ["bars", "reinforcement", "steel"],
    "streetlight": ["street", "lighting", "luminaire"],
    "streetlights": ["street", "lighting", "luminaires"],
    "tmt": ["reinforcement", "steel", "rebar"],
    "wire": ["cable", "conductor"],
}


@dataclass(frozen=True)
class VectorDocument:
    standard: dict[str, str]
    vector: dict[str, float]


def expand_tokens(tokens: list[str]) -> list[str]:
    expanded = list(tokens)
    for token in tokens:
        expanded.extend(SYNONYMS.get(token, []))
    return expanded


def feature_counts(text: str) -> Counter[str]:
    tokens = expand_tokens(tokenize(text))
    counts: Counter[str] = Counter()

    for token in tokens:
        counts[f"tok:{token}"] += 1

    for first, second in zip(tokens, tokens[1:]):
        counts[f"bi:{first}_{second}"] += 1

    compact = normalize(text).replace(" ", "")
    for index in range(max(0, len(compact) - 3)):
        counts[f"ch:{compact[index:index + 4]}"] += 0.25

    return counts


def normalize_vector(counts: Counter[str]) -> dict[str, float]:
    magnitude = math.sqrt(sum(value * value for value in counts.values()))
    if not magnitude:
        return {}
    return {feature: value / magnitude for feature, value in counts.items()}


def cosine_similarity(left: dict[str, float], right: dict[str, float]) -> float:
    if not left or not right:
        return 0.0

    if len(left) > len(right):
        left, right = right, left

    return sum(value * right.get(feature, 0.0) for feature, value in left.items())


def standard_text(standard: dict[str, str]) -> str:
    return " ".join(standard.get(field, "") for field in VECTOR_FIELDS)


class HybridSearchEngine:
    def __init__(self, standards: Iterable[dict[str, str]]):
        self.standards = list(standards)
        self.documents = [
            VectorDocument(
                standard=standard,
                vector=normalize_vector(feature_counts(standard_text(standard))),
            )
            for standard in self.standards
        ]

    def search(
        self,
        query: str,
        limit: int = 10,
        min_score: float = 1.0,
        keyword_weight: float = 1.0,
        vector_weight: float = 24.0,
    ) -> list[SearchResult]:
        keyword_results = search_standards(
            query,
            standards=self.standards,
            limit=len(self.standards),
            min_score=0,
        )
        keyword_by_id = {result.standard["id"]: result for result in keyword_results}
        query_vector = normalize_vector(feature_counts(query))

        results: list[SearchResult] = []
        for document in self.documents:
            standard_id = document.standard["id"]
            keyword_result = keyword_by_id.get(
                standard_id,
                SearchResult(
                    standard=document.standard,
                    score=0.0,
                    matched_terms=[],
                    matched_fields=[],
                ),
            )
            vector_score = cosine_similarity(query_vector, document.vector)
            combined_score = (keyword_result.score * keyword_weight) + (vector_score * vector_weight)

            if combined_score < min_score:
                continue

            matched_fields = set(keyword_result.matched_fields)
            matched_terms = set(keyword_result.matched_terms)

            if vector_score > 0:
                matched_fields.add("vector_similarity")
            if vector_score >= 0.12:
                matched_terms.add("semantic_match")

            results.append(
                SearchResult(
                    standard=document.standard,
                    score=round(combined_score, 2),
                    matched_terms=sorted(matched_terms),
                    matched_fields=sorted(matched_fields),
                )
            )

        return sorted(results, key=lambda result: result.score, reverse=True)[:limit]


def search_hybrid_standards(
    query: str,
    standards: Iterable[dict[str, str]],
    limit: int = 10,
    min_score: float = 1.0,
) -> list[SearchResult]:
    return HybridSearchEngine(standards).search(query=query, limit=limit, min_score=min_score)
