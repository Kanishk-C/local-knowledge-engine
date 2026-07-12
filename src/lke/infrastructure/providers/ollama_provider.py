"""Ollama implementation of the EmbeddingProvider protocol."""

import time
from typing import Any

import ollama

from lke.config.models import AIProviderConfig, EmbeddingsConfig, EnrichmentConfig
from lke.domain.exceptions import EmbeddingGenerationError
from lke.domain.models.embedding import (
    EmbeddingVector,
    HealthStatus,
)
from lke.domain.models.search import ProviderCapabilities
from lke.infrastructure.resilience.retry import RetryPolicy


class OllamaProvider:
    """Ollama provider for generating embeddings and structured data."""

    def __init__(
        self, 
        ai_config: AIProviderConfig, 
        embed_config: EmbeddingsConfig,
        enrich_config: EnrichmentConfig | None = None
    ) -> None:
        """Initialize the Ollama provider.

        Args:
            ai_config: Configuration for the AI provider (host, timeout).
            embed_config: Configuration for embeddings (model name).
            enrich_config: Configuration for enrichment (generation model name).
        """
        self._client = ollama.Client(host=ai_config.base_url)
        self._model_name = embed_config.model_name
        self._max_retries = ai_config.max_retries
        self._batch_size = embed_config.batch_size
        self._generation_model = enrich_config.generation_model if enrich_config else "llama3.2"

    def generate_embeddings(self, texts: list[str]) -> list[EmbeddingVector]:
        """Generate embeddings for a list of texts using Ollama.

        Args:
            texts: A list of text strings to embed.

        Returns:
            A list of EmbeddingVector objects.

        Raises:
            EmbeddingGenerationError: If the Ollama API call fails or returns invalid data.
        """
        if not texts:
            return []

        all_vectors: list[EmbeddingVector] = []
        batch_size = self._batch_size

        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i : i + batch_size]

            def _do_request(batch: list[str] = batch_texts) -> Any:
                return self._client.embed(model=self._model_name, input=batch)

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

            if len(embeddings_data) != len(batch_texts):
                raise EmbeddingGenerationError(
                    f"Expected {len(batch_texts)} embeddings, got {len(embeddings_data)}"
                )

            for vec in embeddings_data:
                if not isinstance(vec, list) or not all(isinstance(v, (int, float)) for v in vec):
                    raise EmbeddingGenerationError("Malformed embedding vector in response.")
                all_vectors.append(EmbeddingVector(vector=vec))

        return all_vectors

    def generate(self, prompt: str, schema: type) -> dict[str, Any]:
        """Generate structured output based on a prompt and Pydantic schema."""
        import json
        
        def _do_request() -> Any:
            return self._client.generate(
                model=self._generation_model,
                prompt=prompt,
                format=schema.model_json_schema(),
            )
            
        try:
            response = RetryPolicy.execute(
                func=_do_request,
                max_retries=self._max_retries,
                initial_backoff_ms=100,
                max_backoff_ms=2000,
                exceptions=(Exception,),
            )
            raw_text = response.response
            return json.loads(raw_text)
        except Exception as e:
            raise Exception(f"Failed to generate structured output: {e}") from e

    def get_capabilities(self) -> ProviderCapabilities:
        raise NotImplementedError()
        
    def generate_embedding(self, text: str) -> EmbeddingVector:
        raise NotImplementedError()
        
    def summarize(self, text: str) -> str:
        raise NotImplementedError()
        
    def extract_keywords(self, text: str) -> list[str]:
        raise NotImplementedError()
        
    def generate_metadata(self, text: str) -> dict[str, str]:
        raise NotImplementedError()

    def health_check(self) -> HealthStatus:
        """Check the health of the Ollama provider."""
        start_time = time.perf_counter()

        try:
            models_response = self._client.list()
            latency = (time.perf_counter() - start_time) * 1000

            models_data = getattr(models_response, "models", [])
            model_names = [getattr(m, "model", "") or getattr(m, "name", "") for m in models_data]

            has_model = any(
                m == self._model_name or str(m).startswith(f"{self._model_name}:") for m in model_names
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
