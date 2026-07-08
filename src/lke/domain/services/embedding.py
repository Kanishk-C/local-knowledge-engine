"""Domain service for generating embeddings from document chunks."""

from lke.config.models import EmbeddingsConfig
from lke.domain.models.document import DocumentChunk
from lke.domain.models.embedding import EmbeddedChunk
from lke.domain.protocols.embedding_provider import EmbeddingProvider


class EmbeddingService:
    """Service to orchestrate embedding generation."""

    def __init__(self, provider: EmbeddingProvider, config: EmbeddingsConfig) -> None:
        """Initialize the embedding service.

        Args:
            provider: The embedding provider to use for generating vectors.
            config: Configuration containing batch size limits.
        """
        self._provider = provider
        self._batch_size = config.batch_size

    def embed_chunks(self, chunks: list[DocumentChunk]) -> list[EmbeddedChunk]:
        """Generate embedded chunks from document chunks.

        Processes chunks in batches and strictly preserves ordering.

        Args:
            chunks: List of document chunks to embed.

        Returns:
            List of embedded chunks in the exact same order as input.

        Raises:
            EmbeddingGenerationError: If the provider fails for any batch.
        """
        if not chunks:
            return []

        embedded_chunks = []

        for i in range(0, len(chunks), self._batch_size):
            batch = chunks[i : i + self._batch_size]
            texts = [chunk.content for chunk in batch]

            vectors = self._provider.generate_embeddings(texts)

            for chunk, vector in zip(batch, vectors, strict=True):
                embedded_chunks.append(EmbeddedChunk(chunk=chunk, embedding=vector))

        return embedded_chunks
