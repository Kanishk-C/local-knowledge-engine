"""Configuration hierarchy and merging logic."""

import os
from typing import Any


def merge_configs(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge two configuration dictionaries."""
    merged = base.copy()
    for key, value in override.items():
        if isinstance(value, dict) and key in merged and isinstance(merged[key], dict):
            merged[key] = merge_configs(merged[key], value)
        else:
            merged[key] = value
    return merged


def get_env_overrides(prefix: str = "LKE_") -> dict[str, Any]:
    """Extract configuration overrides from environment variables.

    Environment variables should use double underscore for nesting.
    For example: LKE_LOGGING__LEVEL=DEBUG
    """
    overrides: dict[str, Any] = {}
    for env_var, value in os.environ.items():
        if not env_var.startswith(prefix):
            continue

        key_path = env_var[len(prefix) :].lower().split("__")

        # Build nested dictionary
        current_level = overrides
        for i, key in enumerate(key_path):
            if i == len(key_path) - 1:
                # Type conversion heuristic (basic)
                if value.lower() in ("true", "1"):
                    current_level[key] = True
                elif value.lower() in ("false", "0"):
                    current_level[key] = False
                elif value.isdigit():
                    current_level[key] = int(value)
                else:
                    try:
                        current_level[key] = float(value)
                    except ValueError:
                        current_level[key] = value
            else:
                if key not in current_level or not isinstance(current_level[key], dict):
                    current_level[key] = {}
                current_level = current_level[key]

    return overrides
