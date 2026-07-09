"""Domain models for search queries and results."""

from dataclasses import dataclass, field
from typing import Any

from .embedding import EmbeddedChunk


@dataclass(frozen=True)
class SearchQuery:
    """Represents a user's search query."""

    text: str
    top_k: int = 10
    filters: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("Search query text cannot be empty")
        if self.top_k <= 0:
            raise ValueError("top_k must be greater than 0")


@dataclass(frozen=True)
class VectorSearchHit:
    """Represents a raw hit from the vector database."""

    chunk: EmbeddedChunk
    similarity: float

    def __post_init__(self) -> None:
        if self.similarity < 0:
            raise ValueError("Similarity cannot be negative")


@dataclass(frozen=True)
class SearchResult:
    """Represents a scored and formatted result for the end user."""

    chunk_id: str
    document_id: str
    content: str
    score: float
    metadata: dict[str, Any]

    def __post_init__(self) -> None:
        if not (0.0 <= self.score <= 1.0):
            raise ValueError("Score must be between 0.0 and 1.0")


@dataclass(frozen=True)
class ProviderCapabilities:
    """Capabilities supported by the currently configured AI Provider."""

    model_name: str
    supports_embeddings: bool
    supports_chat: bool
    embedding_dimensions: int | None = None
