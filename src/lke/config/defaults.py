"""Default configuration factories."""

from lke.config.models import ApplicationConfig


def get_default_config() -> ApplicationConfig:
    """Get the base default application configuration."""
    return ApplicationConfig()
