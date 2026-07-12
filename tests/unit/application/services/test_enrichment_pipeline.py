import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock

from lke.application.services.enrichment_pipeline import EnrichmentPipeline, EnrichmentResult
from lke.config.models import EnrichmentConfig
from lke.domain.models.document import ParsedContent
from lke.domain.protocols.ai_provider import AIProvider
from lke.domain.protocols.parser import Parser
from lke.domain.protocols.vocabulary import FolderVocabulary, TagVocabulary
from lke.domain.repositories.vector_repository import VectorRepository
from lke.domain.models.search import SearchResult
from lke.infrastructure.parsing.markdown_writer import MarkdownFrontmatterWriter
from lke.application.services.indexing_pipeline import _MetadataStore


@pytest.fixture
def mock_parser() -> Mock:
    return Mock(spec=Parser)


@pytest.fixture
def mock_ai() -> Mock:
    return Mock(spec=AIProvider)


@pytest.fixture
def mock_vector_repo() -> Mock:
    return Mock(spec=VectorRepository)


@pytest.fixture
def mock_tag_vocab() -> Mock:
    vocab = Mock(spec=TagVocabulary)
    vocab.get_all.return_value = ["python", "rust"]
    return vocab


@pytest.fixture
def mock_folder_vocab() -> Mock:
    vocab = Mock(spec=FolderVocabulary)
    vocab.get_all.return_value = ["programming"]
    return vocab


@pytest.fixture
def mock_writer() -> Mock:
    writer = Mock(spec=MarkdownFrontmatterWriter)
    writer.write_enrichment.side_effect = lambda file_path, **kwargs: file_path
    return writer


@pytest.fixture
def mock_metadata() -> Mock:
    metadata = Mock(spec=_MetadataStore)
    metadata.get_hash.return_value = "dummy-hash" # Pretend it's indexed
    return metadata


@pytest.fixture
def config() -> EnrichmentConfig:
    return EnrichmentConfig(
        generation_model="llama3.2",
        max_new_tags_per_note=2,
        max_new_folders_per_note=1,
        related_notes_threshold=0.75,
        related_notes_max=5,
        auto_file_enabled=False
    )


@pytest.fixture
def pipeline(
    mock_parser: Mock,
    mock_ai: Mock,
    mock_vector_repo: Mock,
    mock_tag_vocab: Mock,
    mock_folder_vocab: Mock,
    mock_writer: Mock,
    mock_metadata: Mock,
    config: EnrichmentConfig,
) -> EnrichmentPipeline:
    return EnrichmentPipeline(
        parser=mock_parser,
        ai_provider=mock_ai,
        vector_repo=mock_vector_repo,
        tag_vocab=mock_tag_vocab,
        folder_vocab=mock_folder_vocab,
        writer=mock_writer,
        metadata_store=mock_metadata,
        config=config,
    )


def test_enrich_document_success(
    pipeline: EnrichmentPipeline,
    mock_parser: Mock,
    mock_ai: Mock,
    mock_vector_repo: Mock,
    mock_writer: Mock,
    tmp_path: Path,
) -> None:
    doc_path = tmp_path / "test.md"
    doc_path.write_text("Hello world")
    
    doc_id = str(doc_path.absolute())
    parsed_content = ParsedContent(document_id=doc_id, raw_text="Hello world", frontmatter={})
    mock_parser.parse.return_value = parsed_content
    
    mock_ai.generate.return_value = {
        "tags": ["python", "new_tag"],
        "folder": "programming",
        "summary": "A test note"
    }
    
    # Mock some chunks and hits
    chunk = MagicMock()
    chunk.embedding = [0.1]
    mock_vector_repo.get_document.return_value = [chunk]
    
    hit = SearchResult(
        chunk_id="other:0",
        document_id="other.md",
        content="something",
        score=0.9,
        metadata={}
    )
    mock_vector_repo.search.return_value = [hit]
    
    result = pipeline.enrich_document(doc_path)
    
    assert result.success is True
    assert result.tags_added == 2
    assert result.related_notes_found == 1
    
    mock_writer.write_enrichment.assert_called_once()
    kwargs = mock_writer.write_enrichment.call_args[1]
    assert kwargs["tags"] == ["python", "new_tag"]
    assert kwargs["summary"] == "A test note"
    assert kwargs["related_links"] == ["[[other]]"]

def test_enrich_document_move_collision_reports_failure(
    pipeline: EnrichmentPipeline,
    mock_parser: Mock,
    mock_ai: Mock,
    mock_vector_repo: Mock,
    mock_writer: Mock,
    tmp_path: Path,
) -> None:
    pipeline._config.auto_file_enabled = True
    
    doc_path = tmp_path / "test.md"
    doc_path.write_text("Hello world")
    
    doc_id = str(doc_path.absolute())
    parsed_content = ParsedContent(document_id=doc_id, raw_text="Hello world", frontmatter={})
    mock_parser.parse.return_value = parsed_content
    
    mock_ai.generate.return_value = {
        "tags": ["python"],
        "folder": "programming",
        "summary": "A test note"
    }
    mock_vector_repo.get_document.return_value = []
    
    # Mock writer to return the original path, simulating a move collision
    mock_writer.write_enrichment.return_value = doc_path
    mock_vector_repo = Mock()
    mock_vector_repo.search.return_value = []
    pipeline._vector_repo = mock_vector_repo
    mock_vector_repo.get_document.return_value = []
    mock_writer.move_file.return_value = doc_path
    
    result = pipeline.enrich_document(doc_path)
    
    assert result.success is False
    assert "Move skipped" in result.error

def test_enrich_document_with_none_folder(
    pipeline: EnrichmentPipeline,
    mock_parser: Mock,
    mock_ai: Mock,
    mock_vector_repo: Mock,
    mock_writer: Mock,
    tmp_path: Path,
) -> None:
    doc_path = tmp_path / "test_none_folder.md"
    doc_path.write_text("Hello world")
    
    doc_id = str(doc_path.absolute())
    parsed_content = ParsedContent(document_id=doc_id, raw_text="Hello world", frontmatter={})
    mock_parser.parse.return_value = parsed_content
    
    # LLM returns an actual None for folder
    mock_ai.generate.return_value = {
        "tags": ["python"],
        "folder": None,
        "summary": "A test note"
    }
    mock_vector_repo.get_document.return_value = []
    
    # Ensure it writes correctly and folder normalizes to "" (or None)
    # The writer.write_enrichment is called with new_folder=None
    result = pipeline.enrich_document(doc_path)
    
    assert result.success is True
    
    mock_writer.write_enrichment.assert_called_once()
    kwargs = mock_writer.write_enrichment.call_args[1]
    assert kwargs["new_folder"] in (None, "")
    
    mock_writer.move_file.assert_not_called()

def test_enrich_document_empty_summary_retry_and_omit(
    pipeline: EnrichmentPipeline,
    mock_parser: Mock,
    mock_ai: Mock,
    mock_vector_repo: Mock,
    mock_writer: Mock,
    tmp_path: Path,
) -> None:
    doc_path = tmp_path / "test_empty_summary.md"
    doc_path.write_text("Hello world")
    
    doc_id = str(doc_path.absolute())
    parsed_content = ParsedContent(document_id=doc_id, raw_text="Hello world", frontmatter={})
    mock_parser.parse.return_value = parsed_content
    
    # LLM returns an empty summary on both tries
    mock_ai.generate.side_effect = [
        {"tags": ["python"], "folder": "tech", "summary": "   "},
        {"tags": ["python"], "folder": "tech", "summary": ""}
    ]
    mock_vector_repo.get_document.return_value = []
    
    result = pipeline.enrich_document(doc_path)
    
    assert result.success is True
    
    # Should retry once, meaning generate called twice
    assert mock_ai.generate.call_count == 2
    
    # And then summary should be omitted (passed as None)
    mock_writer.write_enrichment.assert_called_once()
    kwargs = mock_writer.write_enrichment.call_args[1]
    assert kwargs["summary"] is None


def test_enrich_document_auto_file_rekeys_vector_and_metadata(
    pipeline: EnrichmentPipeline,
    mock_parser: Mock,
    mock_ai: Mock,
    mock_vector_repo: Mock,
    mock_writer: Mock,
    mock_metadata: Mock,
    tmp_path: Path,
) -> None:
    from lke.domain.models.embedding import EmbeddedChunk
    
    pipeline._config.auto_file_enabled = True
    
    doc_path = tmp_path / "test_move.md"
    doc_path.write_text("Hello world")
    target_path = tmp_path / "tech" / "test_move.md"
    
    doc_id = str(doc_path.absolute())
    new_doc_id = str(target_path.absolute())
    
    parsed_content = ParsedContent(document_id=doc_id, raw_text="Hello world", frontmatter={})
    mock_parser.parse.return_value = parsed_content
    
    mock_ai.generate.return_value = {"tags": ["python"], "folder": "tech", "summary": "A test"}
    mock_writer.move_file.return_value = target_path
    
    # Mock vector chunk for re-keying
    mock_chunk = Mock(spec=EmbeddedChunk)
    mock_chunk.chunk = Mock()
    mock_chunk.embedding = Mock()
    mock_vector_repo.search.return_value = []
    mock_chunk.chunk.document_id = doc_id
    mock_vector_repo.get_document.return_value = [mock_chunk]
    
    # Mock metadata for re-keying
    mock_metadata.get_hash.return_value = "oldhash"
    
    result = pipeline.enrich_document(doc_path)
    
    assert result.success is True
    assert result.file_path == target_path
    
    # Verify Vector re-keying
    mock_vector_repo.delete_document.assert_called_once_with(doc_id)
    assert mock_chunk.chunk.document_id == new_doc_id
    mock_vector_repo.upsert.assert_called_once_with([mock_chunk])
    
    # Verify Metadata re-keying
    mock_metadata.remove.assert_called_once_with(doc_id)
    mock_metadata.set_hash.assert_called_once_with(new_doc_id, "oldhash")
    mock_metadata.save.assert_called_once()

def test_enrich_document_emits_file_write_starting(
    pipeline: EnrichmentPipeline,
    mock_parser: Mock,
    mock_ai: Mock,
    mock_writer: Mock,
    mock_vector_repo: Mock,
    tmp_path: Path,
) -> None:
    doc_path = tmp_path / "test.md"
    doc_path.write_text("Hello world")
    
    doc_id = str(doc_path.absolute())
    parsed_content = ParsedContent(document_id=doc_id, raw_text="Hello world", frontmatter={})
    mock_parser.parse.return_value = parsed_content
    mock_ai.generate.return_value = {"tags": ["python"], "summary": "A test"}
    mock_writer.write_enrichment.return_value = doc_path
    
    mock_vector_repo.search.return_value = []
    mock_vector_repo.get_document.return_value = []
    
    # We will record all events emitted
    emitted_events = []
    def callback(event):
        emitted_events.append(event)
        
    result = pipeline.enrich_document(doc_path, event_callback=callback)
    
    assert result.success is True
    
    # Verify that FileWriteStarting was emitted
    from lke.domain.events.filesystem import FileWriteStarting
    write_events = [e for e in emitted_events if isinstance(e, FileWriteStarting)]
    assert len(write_events) >= 1
    assert write_events[0].original_path == doc_id
    assert write_events[0].final_path == doc_id

def test_enrich_document_emits_two_file_write_starting_on_move(
    pipeline: EnrichmentPipeline,
    mock_parser: Mock,
    mock_ai: Mock,
    mock_writer: Mock,
    mock_vector_repo: Mock,
    tmp_path: Path,
) -> None:
    pipeline._config.auto_file_enabled = True
    
    doc_path = tmp_path / "test.md"
    doc_path.write_text("Hello world")
    target_path = tmp_path / "tech" / "test.md"
    
    doc_id = str(doc_path.absolute())
    target_id = str(target_path.absolute())
    
    parsed_content = ParsedContent(document_id=doc_id, raw_text="Hello world", frontmatter={})
    mock_parser.parse.return_value = parsed_content
    mock_ai.generate.return_value = {"tags": ["python"], "summary": "A test", "folder": "tech"}
    mock_writer.write_enrichment.return_value = doc_path
    mock_writer.move_file.return_value = target_path
    
    mock_vector_repo.search.return_value = []
    mock_vector_repo.get_document.return_value = []
    
    emitted_events = []
    def callback(event):
        emitted_events.append(event)
        
    result = pipeline.enrich_document(doc_path, event_callback=callback)
    
    assert result.success is True
    
    from lke.domain.events.filesystem import FileWriteStarting
    write_events = [e for e in emitted_events if isinstance(e, FileWriteStarting)]
    
    # One for the original write, one for the move
    assert len(write_events) >= 2
    
    # First write
    assert write_events[0].original_path == doc_id
    assert write_events[0].final_path == doc_id
    
    # Second write (move)
    assert write_events[1].original_path == doc_id
    assert write_events[1].final_path == target_id
