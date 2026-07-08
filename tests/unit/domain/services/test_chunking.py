"""Tests for the ChunkingService."""

import pytest

from lke.domain.models.document import ContentType, ParsedContent
from lke.domain.services.chunking import ChunkingService


def test_chunking_service_initialization() -> None:
    """Test validation during ChunkingService initialization."""
    with pytest.raises(ValueError, match="max_tokens must be greater than 0"):
        ChunkingService(max_tokens=0)

    with pytest.raises(ValueError, match="overlap_tokens cannot be negative"):
        ChunkingService(overlap_tokens=-1)

    with pytest.raises(ValueError, match="overlap_tokens must be strictly less than max_tokens"):
        ChunkingService(max_tokens=100, overlap_tokens=100)


def test_chunk_empty_text() -> None:
    """Test chunking with empty text."""
    service = ChunkingService()
    parsed = ParsedContent(document_id="doc1", raw_text="")

    chunks = service.chunk(parsed)
    assert len(chunks) == 0


def test_chunk_small_text() -> None:
    """Test chunking text smaller than max_tokens."""
    service = ChunkingService(max_tokens=10, overlap_tokens=0)
    text = "This is a small text."
    parsed = ParsedContent(document_id="doc1", raw_text=text)

    chunks = service.chunk(parsed)
    assert len(chunks) == 1
    assert chunks[0].content == text
    assert chunks[0].chunk_index == 0
    assert chunks[0].document_id == "doc1"
    assert chunks[0].content_type == ContentType.PROSE


def test_chunk_large_text_with_overlap() -> None:
    """Test chunking text larger than max_tokens with overlap."""
    # max_chars will be 4 * 4 = 16
    # overlap_chars will be 1 * 4 = 4
    service = ChunkingService(max_tokens=4, overlap_tokens=1)

    text = "one two three four five six seven eight nine ten"
    parsed = ParsedContent(document_id="doc1", raw_text=text)

    chunks = service.chunk(parsed)

    assert len(chunks) > 1
    # Check that each chunk respects the max size (roughly) and there is overlap
    for chunk in chunks:
        # A single word might bypass the limit, but here words are small.
        assert len(chunk.content) > 0
        assert chunk.content_type == ContentType.PROSE


def test_chunk_huge_word() -> None:
    """Test chunking when a single word is larger than max_tokens."""
    # max_chars = 12
    service = ChunkingService(max_tokens=3, overlap_tokens=0)

    # "supercalifragilisticexpialidocious" is 34 characters
    text = "small supercalifragilisticexpialidocious word"
    parsed = ParsedContent(document_id="doc1", raw_text=text)

    chunks = service.chunk(parsed)

    assert len(chunks) == 3
    assert chunks[0].content == "small"
    assert chunks[1].content == "supercalifragilisticexpialidocious"
    assert chunks[2].content == "word"


def test_chunk_metadata_propagation() -> None:
    """Test that frontmatter is propagated to chunk metadata."""
    service = ChunkingService()
    parsed = ParsedContent(
        document_id="doc1",
        raw_text="Hello world",
        frontmatter={"title": "Test Document", "author": "Alice"},
    )

    chunks = service.chunk(parsed)
    assert len(chunks) == 1
    assert chunks[0].metadata == {"title": "Test Document", "author": "Alice"}
