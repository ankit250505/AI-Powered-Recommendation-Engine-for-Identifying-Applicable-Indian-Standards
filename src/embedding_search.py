from __future__ import annotations

from typing import Iterable

from src.config import settings
from src.hybrid_search import VECTOR_FIELDS
from src.standards_search import SearchResult, search_standards


DEFAULT_MODEL = settings.embedding_model


def standard_embedding_text(standard: dict[str, str]) -> str:
    labelled_fields = [
        f"Indian Standard: {standard.get('standard_code', '')}",
        f"Title: {standard.get('title', '')}",
        f"Category: {standard.get('category', '')}",
        f"Subcategory: {standard.get('subcategory', '')}",
    ]
    labelled_fields.extend(
        f"{field.replace('_', ' ').title()}: {standard.get(field, '')}"
        for field in VECTOR_FIELDS
        if field not in {"title", "category", "subcategory"}
    )
    return "\n".join(labelled_fields)


class EmbeddingSearchEngine:
    def __init__(
        self,
        standards: Iterable[dict[str, str]],
        model_name: str = DEFAULT_MODEL,
    ):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as error:
            raise RuntimeError(
                "Embedding search requires the sentence-transformers dependency."
            ) from error

        self.standards = list(standards)
        self.model_name = model_name
        self.model = SentenceTransformer(
            model_name,
            local_files_only=settings.embedding_local_only,
        )
        self.embeddings = self.model.encode(
            [standard_embedding_text(standard) for standard in self.standards],
            batch_size=32,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )

    def search(
        self,
        query: str,
        limit: int = 10,
        min_score: float = 1.0,
        keyword_weight: float = 1.0,
        embedding_weight: float = 60.0,
    ) -> list[SearchResult]:
        keyword_results = search_standards(
            query,
            standards=self.standards,
            limit=len(self.standards),
            min_score=0,
        )
        keyword_by_id = {result.standard["id"]: result for result in keyword_results}
        query_embedding = self.model.encode(
            [query],
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )[0]
        similarities = self.embeddings @ query_embedding

        results: list[SearchResult] = []
        for standard, similarity in zip(self.standards, similarities):
            keyword_result = keyword_by_id.get(
                standard["id"],
                SearchResult(standard=standard, score=0.0, matched_terms=[], matched_fields=[]),
            )
            semantic_score = max(0.0, float(similarity))
            combined_score = (keyword_result.score * keyword_weight) + (
                semantic_score * embedding_weight
            )
            if combined_score < min_score:
                continue

            matched_fields = set(keyword_result.matched_fields)
            matched_terms = set(keyword_result.matched_terms)
            if semantic_score > 0:
                matched_fields.add("model_embedding")
            if semantic_score >= 0.35:
                matched_terms.add("semantic_match")

            results.append(
                SearchResult(
                    standard=standard,
                    score=round(combined_score, 2),
                    matched_terms=sorted(matched_terms),
                    matched_fields=sorted(matched_fields),
                )
            )

        return sorted(results, key=lambda result: result.score, reverse=True)[:limit]
