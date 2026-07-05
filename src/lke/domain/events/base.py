"""Domain events for the system."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Self
from uuid import UUID, uuid4


@dataclass(frozen=True)
class DomainEvent:
    """Base class for all domain events."""

    event_id: UUID
    occurred_at: datetime

    @classmethod
    def create(cls, **kwargs: Any) -> Self:
        """Factory method to create an event with automatic ID and timestamp."""
        return cls(event_id=uuid4(), occurred_at=datetime.now(UTC), **kwargs)


@dataclass(frozen=True)
class FileChanged(DomainEvent):
    """Event emitted when a file is modified on disk."""

    file_path: str


@dataclass(frozen=True)
class DocumentIndexed(DomainEvent):
    """Event emitted when a document is successfully indexed."""

    document_id: str
    file_path: str


@dataclass(frozen=True)
class DocumentDeleted(DomainEvent):
    """Event emitted when a document is deleted."""

    document_id: str
    file_path: str


@dataclass(frozen=True)
class IndexingFailed(DomainEvent):
    """Event emitted when indexing a document fails."""

    document_id: str
    file_path: str
    error_message: str
