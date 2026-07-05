"""Domain models for embeddings."""

from dataclasses import dataclass, field


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
