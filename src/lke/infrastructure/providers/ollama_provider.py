"""Ollama implementation of the EmbeddingProvider protocol."""

import time
from typing import Any

import ollama

from lke.config.models import AIProviderConfig, EmbeddingsConfig
from lke.domain.exceptions import EmbeddingGenerationError
from lke.domain.models.embedding import EmbeddingVector, HealthStatus
from lke.infrastructure.resilience.retry import RetryPolicy


class OllamaProvider:
    """Ollama provider for generating embeddings."""

    def __init__(self, ai_config: AIProviderConfig, embed_config: EmbeddingsConfig) -> None:
        """Initialize the Ollama provider.

        Args:
            ai_config: Configuration for the AI provider (host, timeout).
            embed_config: Configuration for embeddings (model name).
        """
        self._client = ollama.Client(host=ai_config.base_url)
        self._model_name = embed_config.model_name
        self._max_retries = ai_config.max_retries

    def generate_embeddings(self, texts: list[str]) -> list[EmbeddingVector]:
        """Generate embeddings using the configured Ollama model."""
        if not texts:
            return []

        def _do_request() -> Any:
            return self._client.embed(model=self._model_name, input=texts)

        try:
            response = RetryPolicy.execute(
                func=_do_request,
                max_retries=self._max_retries,
                initial_backoff_ms=100,
                max_backoff_ms=2000,
                exceptions=(Exception,),
            )
        except Exception as e:
            raise EmbeddingGenerationError(
                f"Failed to generate embeddings from Ollama: {e}"
            ) from e

        embeddings_data = response.get("embeddings")
        if not embeddings_data or not isinstance(embeddings_data, list):
            raise EmbeddingGenerationError("Invalid response format from Ollama.")

        if len(embeddings_data) != len(texts):
            raise EmbeddingGenerationError(
                f"Expected {len(texts)} embeddings, got {len(embeddings_data)}"
            )

        vectors = []
        for vec in embeddings_data:
            if not isinstance(vec, list) or not all(isinstance(v, (int, float)) for v in vec):
                raise EmbeddingGenerationError("Malformed embedding vector in response.")
            vectors.append(EmbeddingVector(vector=vec))

        return vectors

    def health_check(self) -> HealthStatus:
        """Check the health of the Ollama provider."""
        start_time = time.perf_counter()

        try:
            models_response = self._client.list()
            latency = (time.perf_counter() - start_time) * 1000

            models_data = models_response.get("models", [])
            model_names = [m.get("model", "") for m in models_data if isinstance(m, dict)]

            has_model = any(
                m == self._model_name or m.startswith(f"{self._model_name}:") for m in model_names
            )

            if not has_model:
                return HealthStatus(
                    healthy=False,
                    latency_ms=latency,
                    provider="ollama",
                    model=self._model_name,
                    message=f"Model '{self._model_name}' is not pulled.",
                )

            return HealthStatus(
                healthy=True,
                latency_ms=latency,
                provider="ollama",
                model=self._model_name,
                message="Provider is healthy.",
            )

        except Exception as e:
            latency = (time.perf_counter() - start_time) * 1000
            return HealthStatus(
                healthy=False,
                latency_ms=latency,
                provider="ollama",
                model=self._model_name,
                message=f"Connection failed: {e}",
            )
