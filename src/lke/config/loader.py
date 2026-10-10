"""Configuration loader."""

import os
import tomllib
from pathlib import Path
from typing import Any

from lke.config.defaults import get_default_config
from lke.config.exceptions import ConfigLoadError
from lke.config.hierarchy import get_env_overrides, merge_configs
from lke.config.models import ApplicationConfig
from lke.config.validator import validate_config


def load_toml(path: Path) -> dict[str, Any]:
    """Load configuration from a TOML file."""
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except Exception as e:
        raise ConfigLoadError(f"Failed to load TOML from {path}: {e}") from e


def find_config_file() -> Path | None:
    """Locate the config file.

    Order: ``$LKE_CONFIG``, ``./.lke/config.toml``, ``~/.config/lke/config.toml``.
    """
    env_path = os.environ.get("LKE_CONFIG")
    candidates = [Path(env_path).expanduser()] if env_path else []
    candidates += [Path(".lke/config.toml"), Path.home() / ".config" / "lke" / "config.toml"]
    return next((p for p in candidates if p.is_file()), None)


def load_configuration(config_path: Path | None = None) -> ApplicationConfig:
    """Load the full configuration hierarchy.

    Precedence:
    1. Built-in defaults
    2. File configuration (if provided and exists)
    3. Environment variables
    """
    if config_path is None:
        config_path = find_config_file()

    # 1. Start with defaults
    base_dict = get_default_config().model_dump()

    # 2. Apply file overrides if path provided and exists
    file_overrides = {}
    if config_path and config_path.exists():
        file_overrides = load_toml(config_path)

    merged = merge_configs(base_dict, file_overrides)

    # 3. Apply environment overrides
    env_overrides = get_env_overrides()
    merged = merge_configs(merged, env_overrides)

    # Validate and return
    return validate_config(merged)
