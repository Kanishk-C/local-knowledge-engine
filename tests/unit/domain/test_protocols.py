"""Tests for domain protocols."""

from lke.domain.models import EmbeddingVector, ProviderCapabilities
from lke.domain.protocols import AIProvider


def test_protocol_imports_and_instantiation() -> None:
    """Test that protocols can be imported."""
    pass


def test_ai_provider_protocol() -> None:
    """Test AIProvider protocol capabilities."""

    class MockProvider:
        def get_capabilities(self) -> ProviderCapabilities:
            return ProviderCapabilities(
                model_name="test", supports_embeddings=True, supports_chat=False
            )

        def generate_embedding(self, text: str) -> EmbeddingVector:
            return EmbeddingVector([0.1])

        def summarize(self, text: str) -> str:
            return "summary"

        def extract_keywords(self, text: str) -> list[str]:
            return ["key"]

        def generate_metadata(self, text: str) -> dict[str, str]:
            return {"key": "value"}

    provider: AIProvider = MockProvider()
    assert provider.get_capabilities().model_name == "test"
