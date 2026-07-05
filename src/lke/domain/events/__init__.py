"""Events package."""

from .base import DocumentDeleted, DocumentIndexed, DomainEvent, FileChanged, IndexingFailed

__all__ = [
    "DomainEvent",
    "FileChanged",
    "DocumentIndexed",
    "DocumentDeleted",
    "IndexingFailed",
]
