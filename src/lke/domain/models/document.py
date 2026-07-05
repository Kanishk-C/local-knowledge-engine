"""Domain models for documents and parsed content."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from .source import DataSource


class DocumentStatus(StrEnum):
    """Processing status of a document."""

    PENDING = "pending"
    INDEXED = "indexed"
    ERROR = "error"
    PARTIAL = "partial"


class ContentType(StrEnum):
    """Types of content within a document chunk."""

    PROSE = "prose"
    CODE = "code"


class LinkType(StrEnum):
    """Types of links between documents."""

    WIKILINK = "wikilink"
    MARKDOWN = "markdown"
    EXTERNAL = "external"


@dataclass(frozen=True)
class Document:
    """Represents a lightweight reference to a document in the system."""

    document_id: str
    source: DataSource
    status: DocumentStatus = DocumentStatus.PENDING
    error_message: str | None = None
    last_indexed_at: datetime | None = None
    content_hash: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate document invariants."""
        if not self.document_id:
            raise ValueError("document_id cannot be empty")


@dataclass(frozen=True)
class DocumentChunk:
    """Represents a chunk of text extracted from a document, ready for embedding."""

    chunk_id: str
    document_id: str
    content: str
    chunk_index: int
    content_type: ContentType
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.content.strip():
            raise ValueError("Chunk content cannot be empty")
        if self.chunk_index < 0:
            raise ValueError("Chunk index must be non-negative")


@dataclass(frozen=True)
class ParsedContent:
    """Represents the rich structure extracted from a source before chunking."""

    document_id: str
    raw_text: str
    frontmatter: dict[str, Any] = field(default_factory=dict)
    links: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
