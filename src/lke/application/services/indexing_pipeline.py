"""Application service for indexing documents."""

import logging
import time
from datetime import timedelta
from pathlib import Path

from lke.domain.models.indexing import BatchIndexingResult, IndexingResult
from lke.domain.models.source import DataSource, SourceType
from lke.domain.protocols.parser import Parser
from lke.domain.repositories.vector_repository import VectorRepository
from lke.domain.services.chunking import ChunkingService
from lke.domain.services.embedding import EmbeddingService

logger = logging.getLogger(__name__)


class IndexingPipeline:
    """Orchestrates the document ingestion and indexing process."""

    def __init__(
        self,
        parser: Parser,
        chunking_service: ChunkingService,
        embedding_service: EmbeddingService,
        vector_repo: VectorRepository,
    ) -> None:
        """Initialize the indexing pipeline.

        Args:
            parser: Parser to extract text and metadata from files.
            chunking_service: Service to split text into semantic chunks.
            embedding_service: Service to generate vector embeddings.
            vector_repo: Repository to store the embedded chunks.
        """
        self._parser = parser
        self._chunking = chunking_service
        self._embedder = embedding_service
        self._vector_repo = vector_repo

    def index_document(self, file_path: Path) -> IndexingResult:
        """Process a single document through the complete indexing pipeline."""
        start_time = time.perf_counter()
        document_id = None

        try:
            logger.info(f"Indexing document: {file_path}")

            document_id = str(file_path.absolute())
            source = DataSource(uri=document_id, source_type=SourceType.MARKDOWN)
            parsed_content = self._parser.parse(source)

            chunks = self._chunking.chunk(parsed_content)
            chunks_created = len(chunks)

            if self._vector_repo.exists(document_id):
                self._vector_repo.delete_document(document_id)

            if not chunks:
                logger.warning(f"No chunks generated for {file_path}")
                duration = timedelta(seconds=time.perf_counter() - start_time)
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

            self._vector_repo.upsert(embedded_chunks)

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

        except Exception as e:
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

    def index_vault(self, vault_path: Path) -> BatchIndexingResult:
        """Process an entire directory of documents."""
        result = BatchIndexingResult()

        if not vault_path.is_dir():
            logger.error(f"Vault path is not a directory: {vault_path}")
            return result

        markdown_files = list(vault_path.rglob("*.md"))
        logger.info(f"Found {len(markdown_files)} files to index in {vault_path}")

        for file_path in markdown_files:
            doc_result = self.index_document(file_path)
            result.add_result(doc_result)

        logger.info(
            f"Vault indexing complete. "
            f"Success: {result.successful_documents}, "
            f"Failed: {result.failed_documents}, "
            f"Total Chunks: {result.total_chunks}"
        )

        return result
