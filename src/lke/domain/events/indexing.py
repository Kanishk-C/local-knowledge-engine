"""Fine-grained events for the indexing pipeline."""

from dataclasses import dataclass

from lke.domain.events.base import DomainEvent


@dataclass(frozen=True)
class IndexStarted(DomainEvent):
    """Emitted when indexing begins for a document or vault."""

    target_path: str
    total_files: int = 1


@dataclass(frozen=True)
class DocumentParsed(DomainEvent):
    """Emitted after a document is parsed."""

    file_path: str


@dataclass(frozen=True)
class ChunksGenerated(DomainEvent):
    """Emitted after a document is split into chunks."""

    file_path: str
    chunk_count: int


@dataclass(frozen=True)
class EmbeddingsCreated(DomainEvent):
    """Emitted after chunks are embedded."""

    file_path: str
    embedding_count: int


@dataclass(frozen=True)
class VectorsStored(DomainEvent):
    """Emitted after vectors are stored in the repository."""

    file_path: str
    vector_count: int


@dataclass(frozen=True)
class IndexCompleted(DomainEvent):
    """Emitted when indexing is complete."""

    target_path: str
    successful: int
    failed: int


@dataclass(frozen=True)
class IndexSkipped(DomainEvent):
    """Emitted when a file is skipped during indexing because it has not changed."""

    file_path: str
    reason: str
