"""Domain models for embeddings."""

from dataclasses import dataclass, field
from datetime import datetime

from lke.domain.models.document import DocumentChunk


@dataclass(frozen=True)
class EmbeddingVector:
    """Represents a mathematical vector for an embedding."""

    vector: list[float]
    dimensions: int = field(init=False)

    def __post_init__(self) -> None:
        if not self.vector:
            raise ValueError("Embedding vector cannot be empty")
        # Bypass frozen constraint for init=False field
        object.__setattr__(self, "dimensions", len(self.vector))


@dataclass(frozen=True)
class EmbeddedChunk:
    """Represents a chunk of text that has been embedded."""

    chunk: DocumentChunk
    embedding: EmbeddingVector
    created_at: datetime = field(default_factory=lambda: datetime.now().astimezone())


@dataclass(frozen=True)
class HealthStatus:
    """Health status of a provider or repository."""

    healthy: bool
    latency_ms: float
    provider: str
    model: str
    message: str | None = None


@dataclass(frozen=True)
class RepositoryStats:
    """Statistics for the vector repository."""

    total_documents: int
    total_chunks: int
    total_vectors: int
    dimensions: int
    table_name: str
