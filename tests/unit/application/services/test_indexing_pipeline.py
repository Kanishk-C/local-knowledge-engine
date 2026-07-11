"""Tests for the IndexingPipeline."""

from datetime import timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from lke.application.services.indexing_pipeline import IndexingPipeline
from lke.config.models import PathsConfig
from lke.domain.models.document import ContentType, DocumentChunk, ParsedContent
from lke.domain.models.embedding import EmbeddedChunk, EmbeddingVector
from lke.domain.models.indexing import IndexingResult
from lke.domain.models.source import DataSource, SourceType
from lke.domain.protocols.parser import Parser
from lke.domain.repositories.vector_repository import VectorRepository
from lke.domain.services.chunking import ChunkingService
from lke.domain.services.embedding import EmbeddingService


@pytest.fixture
def parser_mock() -> Mock:
    return Mock(spec=Parser)


@pytest.fixture
def chunking_mock() -> Mock:
    return Mock(spec=ChunkingService)


@pytest.fixture
def embedding_mock() -> Mock:
    return Mock(spec=EmbeddingService)


@pytest.fixture
def vector_repo_mock() -> Mock:
    return Mock(spec=VectorRepository)


@pytest.fixture
def paths_config_mock(tmp_path: Path) -> PathsConfig:
    return PathsConfig(metadata_file=tmp_path / ".lke" / "metadata.json")


@pytest.fixture
def pipeline(
    parser_mock: Mock,
    chunking_mock: Mock,
    embedding_mock: Mock,
    vector_repo_mock: Mock,
    paths_config_mock: PathsConfig,
) -> IndexingPipeline:
    return IndexingPipeline(
        parser=parser_mock,
        chunking_service=chunking_mock,
        embedding_service=embedding_mock,
        vector_repo=vector_repo_mock,
        paths_config=paths_config_mock,
    )


def test_index_document_success(
    pipeline: IndexingPipeline,
    parser_mock: Mock,
    chunking_mock: Mock,
    embedding_mock: Mock,
    vector_repo_mock: Mock,
    tmp_path: Path,
) -> None:
    doc_path = tmp_path / "test.md"
    doc_path.write_text("Hello world")

    doc_id = str(doc_path.absolute())
    parsed_content = ParsedContent(document_id=doc_id, raw_text="Hello world")
    parser_mock.parse.return_value = parsed_content

    chunk = DocumentChunk(
        chunk_id=f"{doc_id}:0",
        document_id=doc_id,
        content="Hello world",
        chunk_index=0,
        content_type=ContentType.PROSE,
    )
    chunking_mock.chunk.return_value = [chunk]

    embedded = EmbeddedChunk(chunk=chunk, embedding=EmbeddingVector(vector=[0.1, 0.2]))
    embedding_mock.embed_chunks.return_value = [embedded]

    vector_repo_mock.exists.return_value = False

    result = pipeline.index_document(doc_path)

    assert result.success is True
    assert result.file_path == doc_path
    assert result.document_id == doc_id
    assert result.chunks_created == 1
    assert result.embedded_chunks == 1
    assert result.error_message is None

    parser_mock.parse.assert_called_once_with(
        DataSource(uri=doc_id, source_type=SourceType.MARKDOWN)
    )
    chunking_mock.chunk.assert_called_once_with(parsed_content)
    embedding_mock.embed_chunks.assert_called_once_with([chunk])
    vector_repo_mock.upsert.assert_called_once_with([embedded])
    vector_repo_mock.delete_document.assert_not_called()


def test_index_document_existing(
    pipeline: IndexingPipeline,
    parser_mock: Mock,
    chunking_mock: Mock,
    vector_repo_mock: Mock,
    tmp_path: Path,
) -> None:
    doc_path = tmp_path / "test.md"
    doc_path.write_text("Hello world")

    vector_repo_mock.exists.return_value = True
    chunking_mock.chunk.return_value = []

    pipeline.index_document(doc_path)

    doc_id = str(doc_path.absolute())
    vector_repo_mock.delete_document.assert_called_once_with(doc_id)


def test_index_document_no_chunks(
    pipeline: IndexingPipeline,
    chunking_mock: Mock,
    embedding_mock: Mock,
    vector_repo_mock: Mock,
    tmp_path: Path,
) -> None:
    doc_path = tmp_path / "empty.md"
    doc_path.write_text("")

    chunking_mock.chunk.return_value = []

    result = pipeline.index_document(doc_path)

    assert result.success is True
    assert result.chunks_created == 0

    embedding_mock.embed_chunks.assert_not_called()
    vector_repo_mock.upsert.assert_not_called()


def test_index_document_error_handling(
    pipeline: IndexingPipeline,
    parser_mock: Mock,
    tmp_path: Path,
) -> None:
    doc_path = tmp_path / "error.md"
    doc_path.write_text("content")

    parser_mock.parse.side_effect = ValueError("Parse error")

    result = pipeline.index_document(doc_path)

    assert result.success is False
    assert result.error_message == "Parse error"
    assert result.chunks_created == 0


def test_index_vault(
    pipeline: IndexingPipeline,
    tmp_path: Path,
) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "file1.md").write_text("1")
    (vault / "file2.md").write_text("2")
    (vault / "not_md.txt").write_text("3")

    with patch.object(pipeline, "index_document") as mock_index:
        mock_index.return_value = IndexingResult(
            file_path=Path("dummy"),
            document_id="dummy",
            chunks_created=2,
            embedded_chunks=2,
            duration=timedelta(seconds=1),
            success=True,
        )

        result = pipeline.index_vault(vault)

        assert mock_index.call_count == 2
        assert result.successful_documents == 2
        assert result.failed_documents == 0
        assert result.total_chunks == 4
        assert result.total_duration == timedelta(seconds=2)


def test_index_vault_not_dir(
    pipeline: IndexingPipeline,
    tmp_path: Path,
) -> None:
    file = tmp_path / "file.md"
    file.write_text("")

    result = pipeline.index_vault(file)
    assert result.successful_documents == 0
    assert result.failed_documents == 0


def test_index_document_skip_unchanged(
    pipeline: IndexingPipeline,
    parser_mock: Mock,
    chunking_mock: Mock,
    embedding_mock: Mock,
    vector_repo_mock: Mock,
    tmp_path: Path,
) -> None:
    doc_path = tmp_path / "unchanged.md"
    doc_path.write_text("content")
    doc_id = str(doc_path.absolute())

    parser_mock.parse.return_value = ParsedContent(document_id=doc_id, raw_text="content")
    chunk = DocumentChunk(
        chunk_id=f"{doc_id}:0",
        document_id=doc_id,
        content="content",
        chunk_index=0,
        content_type=ContentType.PROSE,
    )
    chunking_mock.chunk.return_value = [chunk]
    embedding_mock.embed_chunks.return_value = [
        EmbeddedChunk(chunk=chunk, embedding=EmbeddingVector(vector=[0.1]))
    ]

    # First index
    res1 = pipeline.index_document(doc_path)
    assert res1.success is True
    assert res1.chunks_created == 1
    assert vector_repo_mock.upsert.call_count == 1

    # Reset mocks
    vector_repo_mock.upsert.reset_mock()
    vector_repo_mock.delete_document.reset_mock()

    # Second index (should skip)
    res2 = pipeline.index_document(doc_path)
    assert res2.success is True
    assert res2.chunks_created == 0
    assert vector_repo_mock.upsert.call_count == 0
    assert vector_repo_mock.delete_document.call_count == 0


from lke.config.models import EmbeddingsConfig, PathsConfig  # noqa: E402
from lke.infrastructure.repositories.lancedb_repository import LanceDBRepository  # noqa: E402


def test_index_document_orphaned_chunks_removed(
    tmp_path: Path,
    parser_mock: Mock,
    chunking_mock: Mock,
    embedding_mock: Mock,
) -> None:
    # Use actual LanceDB to verify chunk counts
    paths_config = PathsConfig(
        vector_db=tmp_path / "vectors.lance", metadata_file=tmp_path / "metadata.json"
    )
    repo = LanceDBRepository(paths_config, EmbeddingsConfig(embedding_dimensions=2))
    repo.initialize()

    pipeline = IndexingPipeline(
        parser=parser_mock,
        chunking_service=chunking_mock,
        embedding_service=embedding_mock,
        vector_repo=repo,
        paths_config=paths_config,
    )

    doc_path = tmp_path / "shortened.md"
    doc_id = str(doc_path.absolute())

    # Run 1: 5 chunks
    doc_path.write_text("long content")
    parser_mock.parse.return_value = ParsedContent(document_id=doc_id, raw_text="long content")

    chunks = []
    embedded_chunks = []
    for i in range(5):
        chunk = DocumentChunk(
            chunk_id=f"{doc_id}:{i}",
            document_id=doc_id,
            content=f"content {i}",
            chunk_index=i,
            content_type=ContentType.PROSE,
        )
        chunks.append(chunk)
        embedded_chunks.append(
            EmbeddedChunk(chunk=chunk, embedding=EmbeddingVector(vector=[0.1, 0.2]))
        )

    chunking_mock.chunk.return_value = chunks
    embedding_mock.embed_chunks.return_value = embedded_chunks

    pipeline.index_document(doc_path)
    assert len(repo.get_document(doc_id)) == 5

    # Run 2: 2 chunks (file modified and became shorter)
    doc_path.write_text("short content")
    parser_mock.parse.return_value = ParsedContent(document_id=doc_id, raw_text="short content")

    chunks = []
    embedded_chunks = []
    for i in range(2):
        chunk = DocumentChunk(
            chunk_id=f"{doc_id}:{i}",
            document_id=doc_id,
            content=f"content {i}",
            chunk_index=i,
            content_type=ContentType.PROSE,
        )
        chunks.append(chunk)
        embedded_chunks.append(
            EmbeddedChunk(chunk=chunk, embedding=EmbeddingVector(vector=[0.1, 0.2]))
        )

    chunking_mock.chunk.return_value = chunks
    embedding_mock.embed_chunks.return_value = embedded_chunks

    pipeline.index_document(doc_path)

    # Assert total chunk count is exactly 2, not 5 or 7
    final_chunks = repo.get_document(doc_id)
    assert len(final_chunks) == 2
