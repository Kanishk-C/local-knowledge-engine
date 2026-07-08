"""Tests for the LanceRowMapper."""

import json

from lke.domain.models.document import ContentType, DocumentChunk
from lke.domain.models.embedding import EmbeddedChunk, EmbeddingVector
from lke.infrastructure.repositories.mappers.lance_mapper import LanceRowMapper


def test_mapper_to_row_and_from_row() -> None:
    """Test mapping to LanceDB row format and back."""
    metadata = {
        "source_path": "/path/to/file.md",
        "heading_path": ["H1", "H2"],
        "start_offset": 10,
        "end_offset": 50,
        "custom_tag": "test",
    }
    chunk = DocumentChunk(
        chunk_id="doc1:0",
        document_id="doc1",
        content="Hello world",
        chunk_index=0,
        content_type=ContentType.PROSE,
        metadata=metadata,
    )
    vector = EmbeddingVector(vector=[0.1, 0.2, 0.3])
    embedded = EmbeddedChunk(chunk=chunk, embedding=vector)

    row = LanceRowMapper.to_row(embedded)
    assert row["chunk_id"] == "doc1:0"
    assert row["document_id"] == "doc1"
    assert row["content"] == "Hello world"
    assert row["vector"] == [0.1, 0.2, 0.3]
    assert row["source_path"] == "/path/to/file.md"
    assert row["heading_path"] == "H1 > H2"
    assert row["start_offset"] == 10
    assert row["end_offset"] == 50
    assert json.loads(row["metadata"]) == {"custom_tag": "test"}

    reconstructed = LanceRowMapper.from_row(row)
    assert reconstructed.chunk.chunk_id == "doc1:0"
    assert reconstructed.chunk.document_id == "doc1"
    assert reconstructed.chunk.content == "Hello world"
    assert reconstructed.embedding.vector == [0.1, 0.2, 0.3]

    rmeta = reconstructed.chunk.metadata
    assert rmeta["source_path"] == "/path/to/file.md"
    assert rmeta["heading_path"] == ["H1", "H2"]
    assert rmeta["start_offset"] == 10
    assert rmeta["end_offset"] == 50
    assert rmeta["custom_tag"] == "test"
