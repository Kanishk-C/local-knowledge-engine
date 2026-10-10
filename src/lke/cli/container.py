"""Dependency Injection container."""

from typing import Any, TypeVar

T = TypeVar("T")

AI_EXTRA_HINT = (
    "This command needs the optional AI dependencies. Install them with:\n"
    "  uv sync --extra ai        (from a checkout)\n"
    "  pipx install 'lke[ai]'    (or uv tool install 'lke[ai]')"
)


class MissingExtraError(RuntimeError):
    """Raised when an optional dependency group is not installed."""


class Container:
    """A lightweight dependency injection container.

    Holds singletons and resolves dependencies for the CLI and Application layers.
    """

    def __init__(self) -> None:
        self._registry: dict[type, Any] = {}
        self._initialized = False

    def register(self, interface: Any, implementation: Any) -> None:
        """Register an implementation for an interface."""
        self._registry[interface] = implementation

    def resolve(self, interface: Any) -> Any:
        """Resolve an implementation for an interface.

        The global container is wired lazily on first use, so commands that
        don't need the AI stack never import it.
        """
        if interface not in self._registry and self is container and not self._initialized:
            initialize_container()
        if interface not in self._registry:
            name = getattr(interface, "__name__", str(interface))
            raise KeyError(f"No implementation registered for {name}")
        return self._registry[interface]


# Global container instance
container = Container()


def initialize_container() -> None:
    """Initialize the container with all application dependencies."""
    container._initialized = True
    try:
        from lke.application.services.enrichment_pipeline import EnrichmentPipeline
        from lke.application.services.indexing_pipeline import IndexingPipeline, _MetadataStore
        from lke.application.services.rag_service import RAGService
        from lke.application.services.search_service import SearchService
        from lke.config.loader import load_configuration
        from lke.config.models import ApplicationConfig
        from lke.domain.protocols.ai_provider import AIProvider
        from lke.domain.protocols.embedding_provider import EmbeddingProvider
        from lke.domain.protocols.parser import Parser
        from lke.domain.protocols.vocabulary import FolderVocabulary, TagVocabulary
        from lke.domain.repositories.vector_repository import VectorRepository
        from lke.domain.services.chunking import ChunkingService
        from lke.domain.services.embedding import EmbeddingService
        from lke.domain.services.relevance import RelevanceScorer
        from lke.infrastructure.parsing.markdown_parser import MarkdownParser
        from lke.infrastructure.parsing.markdown_writer import MarkdownFrontmatterWriter
        from lke.infrastructure.providers.ollama_provider import OllamaProvider
        from lke.infrastructure.repositories.lancedb_repository import LanceDBRepository
        from lke.infrastructure.vocabulary.json_vocabulary import JsonVocabulary
    except ModuleNotFoundError as e:
        container._initialized = False
        raise MissingExtraError(f"Missing module '{e.name}'.\n{AI_EXTRA_HINT}") from e

    config = load_configuration()
    container.register(ApplicationConfig, config)

    # Infrastructure
    provider = OllamaProvider(config.ai_provider, config.embeddings, config.enrichment)
    container.register(EmbeddingProvider, provider)
    container.register(AIProvider, provider)

    vector_repo = LanceDBRepository(config.paths, config.embeddings)
    container.register(VectorRepository, vector_repo)

    parser = MarkdownParser()
    container.register(Parser, parser)

    workspace_path = config.paths.metadata_file.parent.parent
    tags_vocab = JsonVocabulary(workspace_path, "tags.json")
    folders_vocab = JsonVocabulary(workspace_path, "folders.json")
    container.register(TagVocabulary, tags_vocab)
    container.register(FolderVocabulary, folders_vocab)

    writer = MarkdownFrontmatterWriter()
    container.register(MarkdownFrontmatterWriter, writer)

    metadata_store = _MetadataStore(config.paths.metadata_file)
    container.register(_MetadataStore, metadata_store)

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
    indexing_pipeline = IndexingPipeline(
        parser, chunking_service, embedding_service, vector_repo, metadata_store
    )
    container.register(IndexingPipeline, indexing_pipeline)

    enrichment_pipeline = EnrichmentPipeline(
        parser=parser,
        ai_provider=provider,
        vector_repo=vector_repo,
        tag_vocab=tags_vocab,
        folder_vocab=folders_vocab,
        writer=writer,
        metadata_store=metadata_store,
        config=config.enrichment,
    )
    container.register(EnrichmentPipeline, enrichment_pipeline)

    search_service = SearchService(provider, vector_repo, relevance_scorer, config.search)
    container.register(SearchService, search_service)

    rag_service = RAGService(search_service, provider, config.rag)
    container.register(RAGService, rag_service)
