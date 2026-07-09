"""Tests for the SearchService."""

from unittest.mock import Mock

import pytest

from lke.application.services.search_service import SearchService
from lke.config.models import SearchConfig
from lke.domain.exceptions import DomainError
from lke.domain.models.document import ContentType, DocumentChunk
from lke.domain.models.embedding import EmbeddedChunk, EmbeddingVector
from lke.domain.models.search import SearchResult, VectorSearchHit
from lke.domain.repositories.vector_repository import VectorRepository
from lke.domain.services.relevance import RelevanceScorer


@pytest.fixture
def mock_embedding_provider() -> Mock:
    provider = Mock()
    provider.generate_embeddings.return_value = [EmbeddingVector(vector=[0.1, 0.2, 0.3])]
    return provider


@pytest.fixture
def mock_vector_repository() -> Mock:
    repo = Mock(spec=VectorRepository)
    chunk = DocumentChunk(
        chunk_id="doc1:0",
        document_id="doc1",
        content="Test content",
        chunk_index=0,
        content_type=ContentType.PROSE,
    )
    emb_chunk = EmbeddedChunk(chunk=chunk, embedding=EmbeddingVector(vector=[0.1, 0.2, 0.3]))
    hit = VectorSearchHit(chunk=emb_chunk, similarity=0.9)
    repo.search.return_value = [hit]
    return repo


@pytest.fixture
def mock_relevance_scorer() -> Mock:
    scorer = Mock(spec=RelevanceScorer)
    result = SearchResult(
        chunk_id="doc1:0",
        document_id="doc1",
        content="Test content",
        score=0.9,
        metadata={},
    )
    scorer.score.return_value = [result]
    return scorer


@pytest.fixture
def search_config() -> SearchConfig:
    return SearchConfig(top_k=5, min_similarity=0.5, max_results=20)


@pytest.fixture
def search_service(
    mock_embedding_provider: Mock,
    mock_vector_repository: Mock,
    mock_relevance_scorer: Mock,
    search_config: SearchConfig,
) -> SearchService:
    return SearchService(
        embedding_provider=mock_embedding_provider,
        vector_repository=mock_vector_repository,
        relevance_scorer=mock_relevance_scorer,
        config=search_config,
    )


def test_search_success(
    search_service: SearchService,
    mock_embedding_provider: Mock,
    mock_vector_repository: Mock,
    mock_relevance_scorer: Mock,
) -> None:
    """Test successful search execution."""
    results = search_service.search("test query")

    assert len(results) == 1
    assert results[0].document_id == "doc1"
    assert results[0].score == 0.9

    mock_embedding_provider.generate_embeddings.assert_called_once_with(["test query"])
    mock_vector_repository.search.assert_called_once()
    mock_relevance_scorer.score.assert_called_once()


def test_search_empty_query(search_service: SearchService) -> None:
    """Test search with empty query raises DomainError."""
    with pytest.raises(DomainError, match="cannot be empty"):
        search_service.search("")

    with pytest.raises(DomainError, match="cannot be empty"):
        search_service.search("   ")


def test_search_with_custom_top_k(
    search_service: SearchService,
    mock_vector_repository: Mock,
) -> None:
    """Test search with explicit top_k overrides config."""
    search_service.search("test query", top_k=10)
    mock_vector_repository.search.assert_called_once()
    _, kwargs = mock_vector_repository.search.call_args
    assert kwargs["top_k"] == 10


def test_search_top_k_exceeds_max(
    search_service: SearchService,
    mock_vector_repository: Mock,
) -> None:
    """Test top_k is capped at max_results."""
    search_service.search("test query", top_k=100)
    mock_vector_repository.search.assert_called_once()
    _, kwargs = mock_vector_repository.search.call_args
    assert kwargs["top_k"] == 20  # max_results from config


def test_search_invalid_top_k_uses_default(
    search_service: SearchService,
    mock_vector_repository: Mock,
) -> None:
    """Test invalid top_k falls back to config default."""
    search_service.search("test query", top_k=-5)
    mock_vector_repository.search.assert_called_once()
    _, kwargs = mock_vector_repository.search.call_args
    assert kwargs["top_k"] == 5  # default from config
