"""Protocol defining the capabilities of an embedding provider."""

from typing import Protocol

from lke.domain.models.embedding import EmbeddingVector, HealthStatus


class EmbeddingProvider(Protocol):
    """Protocol for a provider that generates vector embeddings."""

    def generate_embeddings(self, texts: list[str]) -> list[EmbeddingVector]:
        """Generate embedding vectors for the given list of texts.

        Args:
            texts: A list of text strings to embed.

        Returns:
            A list of EmbeddingVector objects corresponding to the texts.

        Raises:
            EmbeddingGenerationError: If the provider fails to generate embeddings.
        """
        ...

    def health_check(self) -> HealthStatus:
        """Check the health and availability of the embedding provider."""
        ...
