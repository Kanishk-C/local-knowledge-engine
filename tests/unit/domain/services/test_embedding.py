"""Tests for the EmbeddingService."""

from unittest.mock import MagicMock

import pytest

from lke.config.models import EmbeddingsConfig
from lke.domain.exceptions import EmbeddingGenerationError
from lke.domain.models.document import ContentType, DocumentChunk
from lke.domain.models.embedding import EmbeddingVector
from lke.domain.services.embedding import EmbeddingService


@pytest.fixture
def mock_provider() -> MagicMock:
    provider = MagicMock()

    def fake_embed(texts: list[str]) -> list[EmbeddingVector]:
        return [EmbeddingVector(vector=[float(len(t))]) for t in texts]

    provider.generate_embeddings.side_effect = fake_embed
    return provider


@pytest.fixture
def service(mock_provider: MagicMock) -> EmbeddingService:
    config = EmbeddingsConfig(batch_size=2)
    return EmbeddingService(provider=mock_provider, config=config)


def create_chunk(content: str, index: int = 0) -> DocumentChunk:
    return DocumentChunk(
        chunk_id=f"doc:{index}",
        document_id="doc",
        content=content,
        chunk_index=index,
        content_type=ContentType.PROSE,
        metadata={},
    )


def test_embedding_service_empty_input(service: EmbeddingService) -> None:
    """Test with empty input."""
    result = service.embed_chunks([])
    assert result == []


def test_embedding_service_one_chunk(service: EmbeddingService) -> None:
    """Test with a single chunk."""
    chunk = create_chunk("hello")
    result = service.embed_chunks([chunk])

    assert len(result) == 1
    assert result[0].chunk == chunk
    assert result[0].embedding.vector == [5.0]


def test_embedding_service_batch_overflow(
    service: EmbeddingService, mock_provider: MagicMock
) -> None:
    """Test that chunks are properly batched."""
    chunks = [create_chunk(f"text{i}", i) for i in range(5)]

    result = service.embed_chunks(chunks)

    assert len(result) == 5
    assert mock_provider.generate_embeddings.call_count == 3
    mock_provider.generate_embeddings.assert_any_call(["text0", "text1"])
    mock_provider.generate_embeddings.assert_any_call(["text2", "text3"])
    mock_provider.generate_embeddings.assert_any_call(["text4"])


def test_embedding_service_preserves_ordering(service: EmbeddingService) -> None:
    """Test that the output strictly preserves the input ordering."""
    chunks = [create_chunk(f"t{i}", i) for i in range(10)]

    result = service.embed_chunks(chunks)

    assert len(result) == 10
    for i in range(10):
        assert result[i].chunk.chunk_id == f"doc:{i}"
        assert result[i].embedding.vector == [float(len(f"t{i}"))]


def test_embedding_service_provider_exception(
    service: EmbeddingService, mock_provider: MagicMock
) -> None:
    """Test that provider exceptions bubble up correctly."""
    mock_provider.generate_embeddings.side_effect = EmbeddingGenerationError("Failed")

    with pytest.raises(EmbeddingGenerationError, match="Failed"):
        service.embed_chunks([create_chunk("hello")])
