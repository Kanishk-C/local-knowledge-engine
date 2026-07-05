"""Tests for domain protocols."""

from typing import Any

from lke.domain.models import (
    EmbeddingVector,
    ProviderCapabilities,
)
from lke.domain.protocols import (
    AIProvider,
    Storage,
)


def test_protocol_imports_and_instantiation() -> None:
    """Test that protocols can be imported and mock implementations created."""

    class MockStorage:
        def get(self, key: str) -> Any:
            return None

        def set(self, key: str, value: Any) -> None:
            pass

        def exists(self, key: str) -> bool:
            return False

        def delete(self, key: str) -> None:
            pass

    # If the protocol is correct, this type hint should pass mypy
    storage: Storage = MockStorage()
    assert storage is not None


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
