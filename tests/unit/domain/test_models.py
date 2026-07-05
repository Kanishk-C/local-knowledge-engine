"""Tests for domain models."""

import pytest

from lke.domain.models import (
    ContentType,
    DataSource,
    Document,
    DocumentChunk,
    DocumentStatus,
    EmbeddingVector,
    ParsedContent,
    SearchQuery,
    SearchResult,
    SourceType,
)


def test_document_creation() -> None:
    """Test Document creation and validation."""
    source = DataSource(uri="test.md", source_type=SourceType.MARKDOWN)
    doc = Document(document_id="doc1", source=source)

    assert doc.document_id == "doc1"
    assert doc.status == DocumentStatus.PENDING

    with pytest.raises(ValueError, match="document_id cannot be empty"):
        Document(document_id="", source=source)


def test_document_chunk_validation() -> None:
    """Test DocumentChunk validation."""
    with pytest.raises(ValueError, match="Chunk content cannot be empty"):
        DocumentChunk(
            chunk_id="c1",
            document_id="d1",
            content="   ",
            chunk_index=0,
            content_type=ContentType.PROSE,
        )

    with pytest.raises(ValueError, match="Chunk index must be non-negative"):
        DocumentChunk(
            chunk_id="c1",
            document_id="d1",
            content="valid",
            chunk_index=-1,
            content_type=ContentType.PROSE,
        )


def test_embedding_vector_validation() -> None:
    """Test EmbeddingVector validation and dimensions logic."""
    vec = EmbeddingVector(vector=[0.1, 0.2, 0.3])
    assert vec.dimensions == 3

    with pytest.raises(ValueError, match="Embedding vector cannot be empty"):
        EmbeddingVector(vector=[])


def test_search_query_validation() -> None:
    """Test SearchQuery validation."""
    with pytest.raises(ValueError, match="Search query text cannot be empty"):
        SearchQuery(text="")

    with pytest.raises(ValueError, match="top_k must be greater than 0"):
        SearchQuery(text="valid", top_k=0)


def test_search_result_validation() -> None:
    """Test SearchResult validation."""
    chunk = DocumentChunk("c1", "d1", "text", 0, ContentType.PROSE)

    with pytest.raises(ValueError, match="Relevance score must be between 0.0 and 1.0"):
        SearchResult(document_id="d1", chunk=chunk, relevance_score=1.5)

    with pytest.raises(ValueError, match="Relevance score must be between 0.0 and 1.0"):
        SearchResult(document_id="d1", chunk=chunk, relevance_score=-0.1)


def test_parsed_content_defaults() -> None:
    """Test ParsedContent defaults."""
    content = ParsedContent(document_id="doc1", raw_text="text")
    assert content.frontmatter == {}
    assert content.links == []
    assert content.tags == []
