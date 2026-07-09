"""Dependency Injection container."""

from typing import Any, TypeVar

from lke.application.services.indexing_pipeline import IndexingPipeline
from lke.application.services.search_service import SearchService
from lke.config.loader import load_configuration
from lke.config.models import ApplicationConfig
from lke.domain.protocols.embedding_provider import EmbeddingProvider
from lke.domain.protocols.parser import Parser
from lke.domain.repositories.vector_repository import VectorRepository
from lke.domain.services.chunking import ChunkingService
from lke.domain.services.embedding import EmbeddingService
from lke.domain.services.relevance import RelevanceScorer
from lke.infrastructure.parsing.markdown_parser import MarkdownParser
from lke.infrastructure.providers.ollama_provider import OllamaProvider
from lke.infrastructure.repositories.lancedb_repository import LanceDBRepository

T = TypeVar("T")


class Container:
    """A lightweight dependency injection container.

    Holds singletons and resolves dependencies for the CLI and Application layers.
    """

    def __init__(self) -> None:
        self._registry: dict[type, Any] = {}

    def register(self, interface: Any, implementation: Any) -> None:
        """Register an implementation for an interface."""
        self._registry[interface] = implementation

    def resolve(self, interface: Any) -> Any:
        """Resolve an implementation for an interface."""
        if interface not in self._registry:
            name = getattr(interface, "__name__", str(interface))
            raise KeyError(f"No implementation registered for {name}")
        return self._registry[interface]


# Global container instance
container = Container()


def initialize_container() -> None:
    """Initialize the container with all application dependencies."""
    config = load_configuration()
    container.register(ApplicationConfig, config)

    # Infrastructure
    provider = OllamaProvider(config.ai_provider, config.embeddings)
    container.register(EmbeddingProvider, provider)

    vector_repo = LanceDBRepository(config.paths, config.embeddings)
    container.register(VectorRepository, vector_repo)

    parser = MarkdownParser()
    container.register(Parser, parser)

    # Domain Services
    chunking_service = ChunkingService(
        max_tokens=config.embeddings.chunk_size,
        overlap_tokens=config.embeddings.chunk_overlap,
        min_tokens=config.embeddings.min_chunk_size,
    )
    container.register(ChunkingService, chunking_service)

    embedding_service = EmbeddingService(provider, config.embeddings)
    container.register(EmbeddingService, embedding_service)

    relevance_scorer = RelevanceScorer(min_similarity=config.search.min_similarity)
    container.register(RelevanceScorer, relevance_scorer)

    # Application Services
    indexing_pipeline = IndexingPipeline(parser, chunking_service, embedding_service, vector_repo)
    container.register(IndexingPipeline, indexing_pipeline)

    search_service = SearchService(provider, vector_repo, relevance_scorer, config.search)
    container.register(SearchService, search_service)
