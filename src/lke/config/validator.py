"""Configuration validation logic."""

from typing import Any

from pydantic import ValidationError

from lke.config.exceptions import ConfigValidationError
from lke.config.models import ApplicationConfig


def validate_config(config_dict: dict[str, Any]) -> ApplicationConfig:
    """Validate a configuration dictionary against the application models."""
    try:
        return ApplicationConfig(**config_dict)
    except ValidationError as e:
        raise ConfigValidationError(f"Configuration validation failed: {e}") from e
