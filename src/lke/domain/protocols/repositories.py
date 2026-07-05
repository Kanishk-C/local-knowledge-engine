"""Repository protocols for the domain."""

from typing import Protocol

from lke.domain.models.document import Document
from lke.domain.models.embedding import EmbeddingVector


class DocumentRepository(Protocol):
    """Protocol for storing and retrieving Document metadata."""

    def get_by_id(self, document_id: str) -> Document | None:
        """Retrieve a document by its unique identifier."""
        ...

    def save(self, document: Document) -> None:
        """Save a document to the repository."""
        ...

    def delete(self, document_id: str) -> None:
        """Delete a document by its unique identifier."""
        ...


class EmbeddingRepository(Protocol):
    """Protocol for storing document chunk embeddings."""

    def store_embedding(self, chunk_id: str, document_id: str, vector: EmbeddingVector) -> None:
        """Store an embedding vector associated with a chunk."""
        ...

    def delete_by_document(self, document_id: str) -> None:
        """Delete all embeddings associated with a document."""
        ...


class MetadataRepository(Protocol):
    """Protocol for querying document metadata."""

    def get_documents_by_tag(self, tag: str) -> list[Document]:
        """Retrieve all documents containing a specific tag."""
        ...
