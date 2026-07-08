"""Vector repository protocol."""

from typing import Protocol

from lke.domain.models.embedding import EmbeddedChunk, HealthStatus, RepositoryStats


class VectorRepository(Protocol):
    """Protocol for storing document embeddings in a vector database."""

    def upsert(self, chunks: list[EmbeddedChunk]) -> None:
        """Upsert a list of embedded chunks into the repository.

        Args:
            chunks: A list of EmbeddedChunk objects to store.
        """
        ...

    def delete_document(self, document_id: str) -> None:
        """Delete all chunks belonging to a specific document.

        Args:
            document_id: The ID of the document to delete.
        """
        ...

    def get_document(self, document_id: str) -> list[EmbeddedChunk]:
        """Retrieve all embedded chunks for a given document ID.

        Args:
            document_id: The ID of the document to retrieve.

        Returns:
            A list of EmbeddedChunk objects for the document.
        """
        ...

    def exists(self, document_id: str) -> bool:
        """Check if a document exists in the repository.

        Args:
            document_id: The ID of the document to check.

        Returns:
            True if the document exists, False otherwise.
        """
        ...

    def stats(self) -> RepositoryStats:
        """Get statistics about the vector repository.

        Returns:
            RepositoryStats containing document, chunk, and vector counts.
        """
        ...

    def health(self) -> HealthStatus:
        """Check the health of the repository.

        Returns:
            HealthStatus indicating if the repository is accessible and healthy.
        """
        ...
