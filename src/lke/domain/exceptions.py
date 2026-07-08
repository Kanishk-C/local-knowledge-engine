"""Base exception hierarchy for the domain."""


class LKEError(Exception):
    """Base exception for all LKE errors."""

    pass


class DomainError(LKEError):
    """Exception raised for domain logic errors."""

    pass


class InfrastructureError(LKEError):
    """Exception raised for infrastructure and external dependency errors."""

    pass


class ConfigurationError(LKEError):
    """Exception raised for configuration errors."""

    pass


class EmbeddingGenerationError(InfrastructureError):
    """Exception raised when an embedding provider fails to generate embeddings."""

    pass
