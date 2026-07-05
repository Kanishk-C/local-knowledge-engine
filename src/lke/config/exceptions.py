"""Configuration exceptions for LKE."""


class ConfigError(Exception):
    """Base class for configuration errors."""

    pass


class ConfigLoadError(ConfigError):
    """Raised when a configuration file cannot be loaded."""

    pass


class ConfigValidationError(ConfigError):
    """Raised when configuration validation fails."""

    pass
