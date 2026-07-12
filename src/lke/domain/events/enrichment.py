"""Enrichment domain events."""

from dataclasses import dataclass
from lke.domain.events.base import DomainEvent


@dataclass(frozen=True)
class EnrichmentStarted(DomainEvent):
    """Event emitted when vault enrichment begins."""
    
    target_path: str
    total_files: int


@dataclass(frozen=True)
class EnrichmentCompleted(DomainEvent):
    """Event emitted when a document is successfully enriched."""
    
    file_path: str
    tags: int


@dataclass(frozen=True)
class EnrichmentSkipped(DomainEvent):
    """Event emitted when enrichment is skipped."""
    
    file_path: str
    reason: str


@dataclass(frozen=True)
class EnrichmentFailed(DomainEvent):
    """Event emitted when enrichment fails."""
    
    file_path: str
    error: str
