"""Domain service for relevance scoring."""

from lke.domain.models.search import SearchResult, VectorSearchHit


class RelevanceScorer:
    """Service to score and normalize search hits."""

    def __init__(self, metric: str = "cosine") -> None:
        """Initialize the relevance scorer.

        Args:
            metric: The distance metric used by the vector store (e.g., 'cosine', 'l2').
        """
        self.metric = metric.lower()

    def score(self, hits: list[VectorSearchHit]) -> list[SearchResult]:
        """Convert raw vector search hits into normalized search results."""
        results: list[SearchResult] = []
        for hit in hits:
            relevance = self._normalize_distance(hit.distance)
            results.append(
                SearchResult(
                    document_id=hit.chunk.document_id,
                    chunk=hit.chunk,
                    relevance_score=relevance,
                )
            )

        # Sort results by relevance descending
        results.sort(key=lambda r: r.relevance_score, reverse=True)
        return results

    def _normalize_distance(self, distance: float) -> float:
        """Normalize a distance into a 0.0 to 1.0 relevance score."""
        if distance < 0:
            distance = 0.0

        if self.metric == "cosine":
            # Cosine distance is usually between 0 and 2.
            # 0 means exact match (similarity 1), 2 means opposite (similarity -1)
            # Normalize to 0-1 range where 0 distance -> 1.0 score
            return max(0.0, min(1.0, 1.0 - (distance / 2.0)))

        # Fallback for L2 or generic: 1 / (1 + distance)
        # This maps [0, inf) to (0, 1]
        return 1.0 / (1.0 + distance)
