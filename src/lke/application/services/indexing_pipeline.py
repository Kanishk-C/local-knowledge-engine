"""Application service for indexing documents."""

import hashlib
import json
import logging
import os
import time
from collections.abc import Callable
from datetime import timedelta
from pathlib import Path

from lke.config.models import PathsConfig
from lke.domain.events.base import DomainEvent
from lke.domain.events.indexing import (
    ChunksGenerated,
    DocumentParsed,
    EmbeddingsCreated,
    IndexCompleted,
    IndexSkipped,
    IndexStarted,
    VectorsStored,
)
from lke.domain.models.indexing import BatchIndexingResult, IndexingResult
from lke.domain.models.source import DataSource, SourceType
from lke.domain.protocols.parser import Parser
from lke.domain.repositories.vector_repository import VectorRepository
from lke.domain.services.chunking import ChunkingService
from lke.domain.services.embedding import EmbeddingService

logger = logging.getLogger(__name__)


class _MetadataStore:
    """Lightweight metadata store for incremental indexing tracking."""

    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path
        self._data: dict[str, str] = {}
        self.load()

    def load(self) -> None:
        """Load the JSON metadata."""
        if self.file_path.exists():
            try:
                with open(self.file_path, encoding="utf-8") as f:
                    self._data = json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Failed to load metadata file, starting fresh: {e}")
                self._data = {}

    def get_hash(self, document_id: str) -> str | None:
        """Get the stored content hash for a document."""
        return self._data.get(document_id)

    def set_hash(self, document_id: str, content_hash: str) -> None:
        """Set the content hash for a document."""
        self._data[document_id] = content_hash

    def remove(self, document_id: str) -> None:
        """Remove a document from the store."""
        if document_id in self._data:
            del self._data[document_id]

    def all_documents(self) -> list[str]:
        """Get a list of all tracked documents."""
        return list(self._data.keys())

    def save(self) -> None:
        """Atomically save the JSON metadata."""
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.file_path.with_suffix(".tmp")
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2)
            os.replace(temp_path, self.file_path)
        except OSError as e:
            logger.error(f"Failed to save metadata to {self.file_path}: {e}")


class IndexingPipeline:
    """Orchestrates the document ingestion and indexing process."""

    def __init__(
        self,
        parser: Parser,
        chunking_service: ChunkingService,
        embedding_service: EmbeddingService,
        vector_repo: VectorRepository,
        metadata_store: _MetadataStore,
    ) -> None:
        """Initialize the indexing pipeline.

        Args:
            parser: Parser to extract text and metadata from files.
            chunking_service: Service to split text into semantic chunks.
            embedding_service: Service to generate vector embeddings.
            vector_repo: Repository to store the embedded chunks.
            metadata_store: Store for tracking indexed files state.
        """
        self._parser = parser
        self._chunking = chunking_service
        self._embedder = embedding_service
        self._vector_repo = vector_repo
        self._metadata_store = metadata_store

    def index_document(
        self, file_path: Path, event_callback: Callable[[DomainEvent], None] | None = None
    ) -> IndexingResult:
        """Process a single document through the complete indexing pipeline."""
        start_time = time.perf_counter()
        document_id = None

        def emit(event: DomainEvent) -> None:
            if event_callback:
                event_callback(event)

        try:
            logger.info(f"Indexing document: {file_path}")

            document_id = str(file_path.absolute())

            # 1. Parse document to get clean body
            source = DataSource(uri=document_id, source_type=SourceType.MARKDOWN)
            parsed_content = self._parser.parse(source)
            
            # Compute hash of the clean body (without frontmatter or AI block)
            content_hash = hashlib.sha256(parsed_content.raw_text.encode("utf-8")).hexdigest()

            # 2. Check if skipped
            if self._metadata_store.get_hash(document_id) == content_hash:
                logger.info(f"Skipping {file_path} (unchanged)")
                emit(IndexSkipped.create(file_path=str(file_path), reason="content unchanged"))
                duration = timedelta(seconds=time.perf_counter() - start_time)
                return IndexingResult(
                    file_path=file_path,
                    document_id=document_id,
                    chunks_created=0,
                    embedded_chunks=0,
                    duration=duration,
                    success=True,
                )

            # 2. Delete ALL existing chunks to prevent orphans
            if self._vector_repo.exists(document_id):
                self._vector_repo.delete_document(document_id)

            emit(DocumentParsed.create(file_path=str(file_path)))

            chunks = self._chunking.chunk(parsed_content)
            chunks_created = len(chunks)
            emit(ChunksGenerated.create(file_path=str(file_path), chunk_count=chunks_created))

            if not chunks:
                logger.warning(f"No chunks generated for {file_path}")
                duration = timedelta(seconds=time.perf_counter() - start_time)
                # Update metadata even if empty to prevent repeated re-indexing
                self._metadata_store.set_hash(document_id, content_hash)
                self._metadata_store.save()
                return IndexingResult(
                    file_path=file_path,
                    document_id=document_id,
                    chunks_created=0,
                    embedded_chunks=0,
                    duration=duration,
                    success=True,
                )

            embedded_chunks = self._embedder.embed_chunks(chunks)
            embedded_count = len(embedded_chunks)
            emit(
                EmbeddingsCreated.create(file_path=str(file_path), embedding_count=embedded_count)
            )

            self._vector_repo.upsert(embedded_chunks)
            emit(VectorsStored.create(file_path=str(file_path), vector_count=embedded_count))

            # 3. Update metadata and persist atomically
            self._metadata_store.set_hash(document_id, content_hash)
            self._metadata_store.save()

            duration = timedelta(seconds=time.perf_counter() - start_time)
            logger.info(
                f"Successfully indexed {file_path} ({embedded_count} chunks) "
                f"in {duration.total_seconds():.2f}s"
            )

            return IndexingResult(
                file_path=file_path,
                document_id=document_id,
                chunks_created=chunks_created,
                embedded_chunks=embedded_count,
                duration=duration,
                success=True,
            )

        except Exception as e:  # noqa: BLE001
            logger.error(f"Failed to index {file_path}: {e}")
            duration = timedelta(seconds=time.perf_counter() - start_time)
            return IndexingResult(
                file_path=file_path,
                document_id=document_id,
                chunks_created=0,
                embedded_chunks=0,
                duration=duration,
                success=False,
                error_message=str(e),
            )

    def index_vault(
        self, vault_path: Path, event_callback: Callable[[DomainEvent], None] | None = None
    ) -> BatchIndexingResult:
        """Process an entire directory of documents."""
        result = BatchIndexingResult()

        if not vault_path.is_dir():
            logger.error(f"Vault path is not a directory: {vault_path}")
            return result

        # Ensure metadata is fresh
        self._metadata_store.load()

        markdown_files = list(vault_path.rglob("*.md"))
        logger.info(f"Found {len(markdown_files)} files to index in {vault_path}")

        # Cleanup deleted files
        current_doc_ids = {str(f.absolute()) for f in markdown_files}
        tracked_doc_ids = self._metadata_store.all_documents()

        for doc_id in tracked_doc_ids:
            if doc_id not in current_doc_ids:
                logger.info(f"Removing deleted document from index: {doc_id}")
                if self._vector_repo.exists(doc_id):
                    self._vector_repo.delete_document(doc_id)
                self._metadata_store.remove(doc_id)

        self._metadata_store.save()

        if event_callback:
            event_callback(
                IndexStarted.create(target_path=str(vault_path), total_files=len(markdown_files))
            )

        for file_path in markdown_files:
            doc_result = self.index_document(file_path, event_callback=event_callback)
            result.add_result(doc_result)

        logger.info(
            f"Vault indexing complete. "
            f"Success: {result.successful_documents}, "
            f"Failed: {result.failed_documents}, "
            f"Total Chunks: {result.total_chunks}"
        )

        if event_callback:
            event_callback(
                IndexCompleted.create(
                    target_path=str(vault_path),
                    successful=result.successful_documents,
                    failed=result.failed_documents,
                )
            )

        return result
