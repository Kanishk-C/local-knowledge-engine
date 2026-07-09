"""Domain service for relevance scoring."""

from lke.domain.models.search import SearchResult, VectorSearchHit


class RelevanceScorer:
    """Service to score and normalize search hits."""

    def __init__(self, min_similarity: float = 0.0) -> None:
        """Initialize the relevance scorer.

        Args:
            min_similarity: The minimum similarity score to include in the results.
        """
        self.min_similarity = min_similarity

    def score(self, hits: list[VectorSearchHit]) -> list[SearchResult]:
        """Convert raw vector search hits into normalized search results."""
        results: list[SearchResult] = []
        for hit in hits:
            # Ensure similarity is normalized between 0.0 and 1.0
            relevance = max(0.0, min(1.0, hit.similarity))

            if relevance < self.min_similarity:
                continue

            results.append(
                SearchResult(
                    chunk_id=hit.chunk.chunk.chunk_id,
                    document_id=hit.chunk.chunk.document_id,
                    content=hit.chunk.chunk.content,
                    score=relevance,
                    metadata=hit.chunk.chunk.metadata,
                )
            )

        # Sort results by score descending
        results.sort(key=lambda r: r.score, reverse=True)
        return results
