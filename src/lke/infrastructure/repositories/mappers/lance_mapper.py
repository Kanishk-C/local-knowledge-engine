"""Mapper for converting domain models to LanceDB rows."""

import json
from typing import Any

from lke.domain.models.embedding import EmbeddedChunk


class LanceRowMapper:
    """Maps EmbeddedChunk models to flat dictionaries for LanceDB insertion."""

    @staticmethod
    def to_row(embedded_chunk: EmbeddedChunk) -> dict[str, Any]:
        """Convert an EmbeddedChunk to a dictionary matching the PyArrow schema.

        Args:
            embedded_chunk: The embedded chunk domain model.

        Returns:
            A dictionary mapped to the LanceDB schema.
        """
        chunk = embedded_chunk.chunk
        metadata = chunk.metadata.copy()

        # Extract frequently filtered fields if present
        source_path = metadata.pop("source_path", None)
        heading_path = metadata.pop("heading_path", None)

        # Convert list of headings to a path string for LanceDB if it's a list
        if isinstance(heading_path, list):
            heading_path = " > ".join(heading_path)

        start_offset = metadata.pop("start_offset", None)
        end_offset = metadata.pop("end_offset", None)

        # Store remaining metadata as JSON string
        metadata_json = json.dumps(metadata)

        return {
            "chunk_id": chunk.chunk_id,
            "document_id": chunk.document_id,
            "content": chunk.content,
            "vector": embedded_chunk.embedding.vector,
            "source_path": source_path,
            "chunk_index": chunk.chunk_index,
            "start_offset": start_offset,
            "end_offset": end_offset,
            "heading_path": heading_path,
            "metadata": metadata_json,
        }

    @staticmethod
    def from_row(row: dict[str, Any]) -> EmbeddedChunk:
        """Convert a LanceDB row dictionary back into an EmbeddedChunk domain model.

        Args:
            row: The dictionary representing a LanceDB row.

        Returns:
            The reconstructed EmbeddedChunk.
        """
        from lke.domain.models.document import ContentType, DocumentChunk
        from lke.domain.models.embedding import EmbeddingVector

        metadata = {}
        if row.get("metadata"):
            metadata = json.loads(row["metadata"])

        if row.get("source_path"):
            metadata["source_path"] = row["source_path"]
        if row.get("heading_path"):
            metadata["heading_path"] = row["heading_path"].split(" > ")
        if row.get("start_offset") is not None:
            metadata["start_offset"] = row["start_offset"]
        if row.get("end_offset") is not None:
            metadata["end_offset"] = row["end_offset"]

        chunk = DocumentChunk(
            chunk_id=row["chunk_id"],
            document_id=row["document_id"],
            content=row["content"],
            chunk_index=row["chunk_index"],
            content_type=ContentType.PROSE,  # LanceDB doesn't store this currently, assume PROSE
            metadata=metadata,
        )

        vector = EmbeddingVector(vector=list(row["vector"]))
        return EmbeddedChunk(chunk=chunk, embedding=vector)
