"""Domain models for data sources."""

from dataclasses import dataclass
from enum import StrEnum


class SourceType(StrEnum):
    """Types of document sources."""

    MARKDOWN = "markdown"
    OBSIDIAN = "obsidian"
    PDF = "pdf"
    CODE = "code"


@dataclass(frozen=True)
class DataSource:
    """Represents a source of information (e.g., a file, a URL)."""

    uri: str
    source_type: SourceType
