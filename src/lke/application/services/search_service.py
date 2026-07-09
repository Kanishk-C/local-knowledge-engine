"""Application service for semantic search."""

from lke.config.models import SearchConfig
from lke.domain.exceptions import DomainError
from lke.domain.models.search import SearchResult
from lke.domain.protocols.embedding_provider import EmbeddingProvider
from lke.domain.repositories.vector_repository import VectorRepository
from lke.domain.services.relevance import RelevanceScorer


class SearchService:
    """Application service for performing semantic search."""

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        vector_repository: VectorRepository,
        relevance_scorer: RelevanceScorer,
        config: SearchConfig,
    ) -> None:
        """Initialize the search service.

        Args:
            embedding_provider: Provider to embed search queries.
            vector_repository: Repository to query for similar chunks.
            relevance_scorer: Service to score and sort hits.
            config: Configuration for search defaults.
        """
        self._provider = embedding_provider
        self._repo = vector_repository
        self._scorer = relevance_scorer
        self._config = config

    def search(self, query: str, top_k: int | None = None) -> list[SearchResult]:
        """Perform a semantic search.

        Args:
            query: The natural language search query.
            top_k: Optional maximum number of results. Defaults to config.

        Returns:
            A list of SearchResult objects representing the best matches.

        Raises:
            DomainError: If the query is empty or whitespace.
        """
        if not query or not query.strip():
            raise DomainError("Search query cannot be empty or whitespace.")

        limit = top_k if top_k is not None else self._config.top_k
        if limit <= 0:
            limit = self._config.top_k

        limit = min(limit, self._config.max_results)

        # 1. Embed the search query
        embedding_results = self._provider.generate_embeddings([query])
        if not embedding_results:
            raise DomainError("Failed to generate embedding for the search query.")
        embedding = embedding_results[0]

        # 2. Query VectorRepo for nearest neighbors
        hits = self._repo.search(embedding=embedding, top_k=limit)

        # 3. Score and format into SearchResults
        return self._scorer.score(hits)
