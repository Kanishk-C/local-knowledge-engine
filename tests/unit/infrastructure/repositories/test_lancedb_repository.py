"""Tests for the LanceDBRepository."""

import time
from pathlib import Path

import pytest

from lke.config.models import EmbeddingsConfig, PathsConfig
from lke.domain.exceptions import InfrastructureError, InvalidEmbeddingDimensionError
from lke.domain.models.document import ContentType, DocumentChunk
from lke.domain.models.embedding import EmbeddedChunk, EmbeddingVector
from lke.infrastructure.repositories.lancedb_repository import LanceDBRepository


@pytest.fixture
def repo(tmp_path: Path) -> LanceDBRepository:
    paths = PathsConfig(vector_db=tmp_path / "test.lance")
    embeds = EmbeddingsConfig(embedding_dimensions=3)
    repository = LanceDBRepository(paths_config=paths, embed_config=embeds)
    repository.initialize()
    return repository


def create_embedded_chunk(doc_id: str, index: int, vector: list[float]) -> EmbeddedChunk:
    chunk = DocumentChunk(
        chunk_id=f"{doc_id}:{index}",
        document_id=doc_id,
        content=f"Content {index}",
        chunk_index=index,
        content_type=ContentType.PROSE,
        metadata={"source_path": f"/{doc_id}.md"},
    )
    return EmbeddedChunk(chunk=chunk, embedding=EmbeddingVector(vector=vector))


def test_repository_initialization(tmp_path: Path) -> None:
    paths = PathsConfig(vector_db=tmp_path / "init.lance")
    embeds = EmbeddingsConfig(embedding_dimensions=3)
    repo = LanceDBRepository(paths_config=paths, embed_config=embeds)

    assert not repo.exists("doc1")

    repo.initialize()
    stats = repo.stats()
    assert stats.total_documents == 0
    assert stats.table_name == "document_chunks"


def test_upsert_and_get_document(repo: LanceDBRepository) -> None:
    chunks = [
        create_embedded_chunk("doc1", 0, [0.1, 0.2, 0.3]),
        create_embedded_chunk("doc1", 1, [0.4, 0.5, 0.6]),
    ]
    repo.upsert(chunks)

    assert repo.exists("doc1")

    retrieved = repo.get_document("doc1")
    assert len(retrieved) == 2

    ids = [c.chunk.chunk_id for c in retrieved]
    assert "doc1:0" in ids
    assert "doc1:1" in ids

    stats = repo.stats()
    assert stats.total_documents == 1
    assert stats.total_chunks == 2


def test_overwrite_existing_chunk(repo: LanceDBRepository) -> None:
    chunks = [create_embedded_chunk("doc1", 0, [0.1, 0.2, 0.3])]
    repo.upsert(chunks)

    chunks_updated = [create_embedded_chunk("doc1", 0, [0.5, 0.5, 0.5])]
    repo.upsert(chunks_updated)

    retrieved = repo.get_document("doc1")
    assert len(retrieved) == 1
    assert retrieved[0].embedding.vector == [0.5, 0.5, 0.5]


def test_delete_document(repo: LanceDBRepository) -> None:
    chunks = [create_embedded_chunk("doc1", 0, [0.1, 0.2, 0.3])]
    repo.upsert(chunks)
    assert repo.exists("doc1")

    repo.delete_document("doc1")
    assert not repo.exists("doc1")
    assert len(repo.get_document("doc1")) == 0


def test_invalid_dimension(repo: LanceDBRepository) -> None:
    chunks = [create_embedded_chunk("doc1", 0, [0.1, 0.2])]
    with pytest.raises(InvalidEmbeddingDimensionError):
        repo.upsert(chunks)


def test_uninitialized_upsert(tmp_path: Path) -> None:
    paths = PathsConfig(vector_db=tmp_path / "uninit.lance")
    embeds = EmbeddingsConfig(embedding_dimensions=3)
    repo = LanceDBRepository(paths_config=paths, embed_config=embeds)

    chunks = [create_embedded_chunk("doc1", 0, [0.1, 0.2, 0.3])]
    with pytest.raises(InfrastructureError, match="not initialized"):
        repo.upsert(chunks)


def test_health_check(repo: LanceDBRepository) -> None:
    health = repo.health()
    assert health.healthy is True
    assert health.provider == "lancedb"


def test_health_check_dimension_mismatch(tmp_path: Path) -> None:
    paths = PathsConfig(vector_db=tmp_path / "mismatch.lance")
    config2 = EmbeddingsConfig(embedding_dimensions=2)
    repo2 = LanceDBRepository(paths_config=paths, embed_config=config2)
    repo2.initialize()

    config3 = EmbeddingsConfig(embedding_dimensions=3)
    repo3 = LanceDBRepository(paths_config=paths, embed_config=config3)
    health = repo3.health()

    assert health.healthy is False
    assert health.message is not None and "Schema dimension mismatch" in health.message


def test_performance_1000_chunks(repo: LanceDBRepository) -> None:
    """Benchmark inserting and retrieving 1000 chunks."""
    chunks = [create_embedded_chunk(f"doc_{i % 10}", i, [0.1, 0.2, 0.3]) for i in range(1000)]

    start_time = time.perf_counter()
    repo.upsert(chunks)
    insert_time = time.perf_counter() - start_time

    start_time = time.perf_counter()
    doc0_chunks = repo.get_document("doc_0")
    retrieve_time = time.perf_counter() - start_time

    assert len(doc0_chunks) == 100
    assert insert_time < 2.0
    assert retrieve_time < 0.5


def test_search(repo: LanceDBRepository) -> None:
    chunks = [
        create_embedded_chunk("doc1", 0, [0.1, 0.1, 0.1]),
        create_embedded_chunk("doc1", 1, [0.9, 0.9, 0.9]),
        create_embedded_chunk("doc2", 0, [0.5, 0.5, 0.5]),
    ]
    repo.upsert(chunks)

    # Search for something close to doc1:1
    query_vector = EmbeddingVector(vector=[0.8, 0.8, 0.8])
    hits = repo.search(query_vector, top_k=2)

    assert len(hits) == 2
    assert hits[0].chunk.chunk.chunk_id == "doc1:1"
    assert hits[1].chunk.chunk.chunk_id == "doc2:0"
    assert hits[0].similarity > hits[1].similarity


def test_search_invalid_dimension(repo: LanceDBRepository) -> None:
    query_vector = EmbeddingVector(vector=[0.1, 0.1])
    with pytest.raises(InvalidEmbeddingDimensionError):
        repo.search(query_vector, top_k=5)


def test_search_uninitialized(tmp_path: Path) -> None:
    paths = PathsConfig(vector_db=tmp_path / "uninit_search.lance")
    embeds = EmbeddingsConfig(embedding_dimensions=3)
    repo = LanceDBRepository(paths_config=paths, embed_config=embeds)

    query_vector = EmbeddingVector(vector=[0.1, 0.1, 0.1])
    hits = repo.search(query_vector, top_k=5)
    assert len(hits) == 0
