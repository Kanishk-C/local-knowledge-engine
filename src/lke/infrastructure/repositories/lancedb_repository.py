"""LanceDB implementation of the VectorRepository protocol."""

import time

import lancedb  # type: ignore
import pyarrow as pa

from lke.config.models import EmbeddingsConfig, PathsConfig
from lke.domain.exceptions import InfrastructureError, InvalidEmbeddingDimensionError
from lke.domain.models.embedding import (
    EmbeddedChunk,
    EmbeddingVector,
    HealthStatus,
    RepositoryStats,
)
from lke.domain.models.search import VectorSearchHit
from lke.infrastructure.repositories.mappers.lance_mapper import LanceRowMapper


class LanceDBRepository:
    """LanceDB repository for storing embedded document chunks."""

    def __init__(self, paths_config: PathsConfig, embed_config: EmbeddingsConfig) -> None:
        """Initialize the LanceDB repository.

        Args:
            paths_config: Configuration containing the DB path.
            embed_config: Configuration containing embedding dimensions.
        """
        self._uri = str(paths_config.vector_db)
        self._dimensions = embed_config.embedding_dimensions
        self._table_name = "document_chunks"
        self._db = lancedb.connect(self._uri)
        self._schema = self._create_schema()

    def _create_schema(self) -> pa.Schema:
        """Create the PyArrow schema dynamically based on configured dimensions."""
        return pa.schema(
            [
                pa.field("chunk_id", pa.string()),
                pa.field("document_id", pa.string()),
                pa.field("content", pa.string()),
                pa.field("vector", pa.list_(pa.float32(), self._dimensions)),
                pa.field("source_path", pa.string(), nullable=True),
                pa.field("chunk_index", pa.int32()),
                pa.field("start_offset", pa.int32(), nullable=True),
                pa.field("end_offset", pa.int32(), nullable=True),
                pa.field("heading_path", pa.string(), nullable=True),
                pa.field("metadata", pa.string()),
            ]
        )

    def initialize(self) -> None:
        """Initialize the repository by creating the table if it doesn't exist."""
        try:
            if self._table_name not in self._db.table_names():
                self._db.create_table(self._table_name, schema=self._schema)
        except Exception as e:
            raise InfrastructureError(f"Failed to initialize LanceDB table: {e}") from e

    def search(
        self,
        embedding: EmbeddingVector,
        top_k: int,
    ) -> list[VectorSearchHit]:
        """Perform semantic search to find similar chunks."""
        if self._table_name not in self._db.table_names():
            return []

        if len(embedding.vector) != self._dimensions:
            raise InvalidEmbeddingDimensionError(
                f"Expected vector of dimension {self._dimensions}, got {len(embedding.vector)}"
            )

        try:
            table = self._db.open_table(self._table_name)
            # LanceDB defaults to L2 distance. For now, we return 1.0 / (1.0 + distance)
            # Alternatively, if distance is cosine, 1.0 - distance is better.
            # We'll use 1.0 / (1.0 + distance) as a safe fallback for similarity.
            results = table.search(embedding.vector).limit(top_k).to_arrow().to_pylist()
            hits = []
            for row in results:
                chunk = LanceRowMapper.from_row(row)
                distance = row.get("_distance", 0.0)
                # Ensure similarity is >= 0
                similarity = max(0.0, 1.0 / (1.0 + distance))
                hits.append(VectorSearchHit(chunk=chunk, similarity=similarity))
            return hits
        except Exception as e:
            raise InfrastructureError(f"Failed to search in LanceDB: {e}") from e

    def upsert(self, chunks: list[EmbeddedChunk]) -> None:
        """Upsert a list of embedded chunks into the repository."""
        if not chunks:
            return

        if self._table_name not in self._db.table_names():
            raise InfrastructureError("Repository not initialized. Call initialize() first.")

        rows = []
        for chunk in chunks:
            if len(chunk.embedding.vector) != self._dimensions:
                raise InvalidEmbeddingDimensionError(
                    f"Expected vector of dimension {self._dimensions}, "
                    f"got {len(chunk.embedding.vector)}"
                )
            rows.append(LanceRowMapper.to_row(chunk))

        try:
            table = self._db.open_table(self._table_name)
            table.merge_insert(
                "chunk_id"
            ).when_matched_update_all().when_not_matched_insert_all().execute(rows)
        except Exception as e:
            raise InfrastructureError(f"Failed to upsert chunks into LanceDB: {e}") from e

    def delete_document(self, document_id: str) -> None:
        """Delete all chunks belonging to a specific document."""
        if self._table_name not in self._db.table_names():
            return
        try:
            table = self._db.open_table(self._table_name)
            table.delete(f"document_id = '{document_id}'")
        except Exception as e:
            raise InfrastructureError(f"Failed to delete document from LanceDB: {e}") from e

    def get_document(self, document_id: str) -> list[EmbeddedChunk]:
        """Retrieve all embedded chunks for a given document ID."""
        if self._table_name not in self._db.table_names():
            return []

        try:
            table = self._db.open_table(self._table_name)
            results = table.search().where(f"document_id = '{document_id}'").to_arrow().to_pylist()
            return [LanceRowMapper.from_row(row) for row in results]
        except Exception as e:
            raise InfrastructureError(f"Failed to retrieve document from LanceDB: {e}") from e

    def exists(self, document_id: str) -> bool:
        """Check if a document exists in the repository."""
        if self._table_name not in self._db.table_names():
            return False

        try:
            table = self._db.open_table(self._table_name)
            results = table.search().where(f"document_id = '{document_id}'").limit(1).to_arrow()
            return len(results) > 0
        except Exception as e:
            raise InfrastructureError(f"Failed to check existence in LanceDB: {e}") from e

    def stats(self) -> RepositoryStats:
        """Get statistics about the vector repository."""
        if self._table_name not in self._db.table_names():
            return RepositoryStats(
                total_documents=0,
                total_chunks=0,
                total_vectors=0,
                dimensions=self._dimensions,
                table_name=self._table_name,
            )

        try:
            table = self._db.open_table(self._table_name)

            results = table.search().select(["document_id"]).to_arrow()
            if len(results) == 0:
                total_chunks = 0
                total_documents = 0
            else:
                doc_ids = results.column("document_id").to_pylist()
                total_chunks = len(doc_ids)
                total_documents = len(set(doc_ids))

            return RepositoryStats(
                total_documents=total_documents,
                total_chunks=total_chunks,
                total_vectors=total_chunks,
                dimensions=self._dimensions,
                table_name=self._table_name,
            )
        except Exception as e:
            raise InfrastructureError(f"Failed to retrieve repository stats: {e}") from e

    def health(self) -> HealthStatus:
        """Check the health of the repository."""
        start_time = time.perf_counter()

        try:
            is_healthy = True
            message = "Provider is healthy."

            if self._table_name not in self._db.table_names():
                is_healthy = False
                message = f"Table '{self._table_name}' does not exist."
            else:
                table = self._db.open_table(self._table_name)
                vector_field = table.schema.field("vector")
                if vector_field.type.list_size != self._dimensions:
                    is_healthy = False
                    message = (
                        f"Schema dimension mismatch. Expected {self._dimensions}, "
                        f"got {vector_field.type.list_size}."
                    )

            latency = (time.perf_counter() - start_time) * 1000
            return HealthStatus(
                healthy=is_healthy,
                latency_ms=latency,
                provider="lancedb",
                model="vector_repository",
                message=message,
            )
        except Exception as e:
            latency = (time.perf_counter() - start_time) * 1000
            return HealthStatus(
                healthy=False,
                latency_ms=latency,
                provider="lancedb",
                model="vector_repository",
                message=f"Health check failed: {e}",
            )
