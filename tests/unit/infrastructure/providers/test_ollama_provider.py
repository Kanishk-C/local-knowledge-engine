"""Tests for OllamaProvider."""

from unittest.mock import MagicMock, patch

import pytest
from httpx import ConnectError, TimeoutException

from lke.config.models import AIProviderConfig, EmbeddingsConfig
from lke.domain.exceptions import EmbeddingGenerationError
from lke.infrastructure.providers.ollama_provider import OllamaProvider


@pytest.fixture
def provider() -> OllamaProvider:
    ai_config = AIProviderConfig(base_url="http://localhost:11434", max_retries=1)
    embed_config = EmbeddingsConfig(model_name="nomic-embed-text")
    return OllamaProvider(ai_config=ai_config, embed_config=embed_config)


def test_ollama_provider_empty_batch(provider: OllamaProvider) -> None:
    """Test empty batch handling."""
    result = provider.generate_embeddings([])
    assert result == []


@patch("ollama.Client.embed")
def test_ollama_provider_success(mock_embed: MagicMock, provider: OllamaProvider) -> None:
    """Test successful embedding generation."""
    mock_embed.return_value = {"embeddings": [[0.1, 0.2], [0.3, 0.4]]}

    result = provider.generate_embeddings(["text1", "text2"])

    assert len(result) == 2
    assert result[0].vector == [0.1, 0.2]
    assert result[1].vector == [0.3, 0.4]
    mock_embed.assert_called_once_with(model="nomic-embed-text", input=["text1", "text2"])


@patch("ollama.Client.embed")
def test_ollama_provider_malformed_json(mock_embed: MagicMock, provider: OllamaProvider) -> None:
    """Test handling of malformed response."""
    # Missing 'embeddings' key
    mock_embed.return_value = {"error": "bad request"}

    with pytest.raises(EmbeddingGenerationError, match="Invalid response format"):
        provider.generate_embeddings(["text1"])

    # Wrong length
    mock_embed.return_value = {"embeddings": [[0.1, 0.2]]}
    with pytest.raises(EmbeddingGenerationError, match="Expected 2 embeddings, got 1"):
        provider.generate_embeddings(["text1", "text2"])

    # Malformed vector
    mock_embed.return_value = {"embeddings": [["not_a_float"]]}
    with pytest.raises(EmbeddingGenerationError, match="Malformed embedding vector"):
        provider.generate_embeddings(["text1"])


@patch("ollama.Client.embed")
def test_ollama_provider_offline(mock_embed: MagicMock, provider: OllamaProvider) -> None:
    """Test handling of Ollama offline."""
    mock_embed.side_effect = ConnectError("Connection refused")

    with pytest.raises(EmbeddingGenerationError, match="Failed to generate embeddings"):
        provider.generate_embeddings(["text1"])


@patch("ollama.Client.embed")
def test_ollama_provider_timeout(mock_embed: MagicMock, provider: OllamaProvider) -> None:
    """Test handling of timeout."""
    mock_embed.side_effect = TimeoutException("Read timeout")

    with pytest.raises(EmbeddingGenerationError, match="Failed to generate embeddings"):
        provider.generate_embeddings(["text1"])


class MockModel:
    def __init__(self, name: str):
        self.model = name

class MockListResponse:
    def __init__(self, models: list[MockModel]):
        self.models = models

@patch("ollama.Client.list")
def test_health_check_healthy(mock_list: MagicMock, provider: OllamaProvider) -> None:
    """Test health check when healthy and model exists."""
    mock_list.return_value = MockListResponse([MockModel("nomic-embed-text:latest")])

    status = provider.health_check()
    assert status.healthy is True
    assert status.model == "nomic-embed-text"
    assert status.provider == "ollama"
    assert status.message == "Provider is healthy."


@patch("ollama.Client.list")
def test_health_check_model_missing(mock_list: MagicMock, provider: OllamaProvider) -> None:
    """Test health check when model is missing."""
    mock_list.return_value = MockListResponse([MockModel("llama3:latest")])

    status = provider.health_check()
    assert status.healthy is False
    assert status.message is not None and "not pulled" in status.message


@patch("ollama.Client.list")
def test_health_check_offline(mock_list: MagicMock, provider: OllamaProvider) -> None:
    """Test health check when Ollama is offline."""
    mock_list.side_effect = ConnectError("Connection refused")

    status = provider.health_check()
    assert status.healthy is False
    assert status.message is not None and "Connection failed" in status.message
