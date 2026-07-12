"""AI Provider protocol for the domain."""

from typing import Protocol, Any

from lke.domain.models.embedding import EmbeddingVector
from lke.domain.models.search import ProviderCapabilities


class AIProvider(Protocol):
    """Protocol defining the capabilities of an AI provider."""

    def get_capabilities(self) -> ProviderCapabilities:
        """Retrieve the capabilities of the configured AI provider."""
        ...

    def generate_embedding(self, text: str) -> EmbeddingVector:
        """Generate an embedding vector for the given text."""
        ...

    def summarize(self, text: str) -> str:
        """Generate a concise summary of the provided text."""
        ...

    def extract_keywords(self, text: str) -> list[str]:
        """Extract relevant keywords from the provided text."""
        ...

    def generate_metadata(self, text: str) -> dict[str, str]:
        """Generate general metadata based on the text."""
        ...

    def generate(self, prompt: str, schema: type) -> dict[str, Any]:
        """Generate structured output based on a prompt and Pydantic schema.
        
        Args:
            prompt: The full prompt with context and instructions.
            schema: A Pydantic BaseModel class defining the expected JSON structure.
            
        Returns:
            A dictionary matching the schema structure.
        """
        ...
