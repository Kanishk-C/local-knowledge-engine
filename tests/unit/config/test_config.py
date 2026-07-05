"""Unit tests for the configuration system."""

from pathlib import Path

import pytest

from lke.config.defaults import get_default_config
from lke.config.exceptions import ConfigLoadError, ConfigValidationError
from lke.config.hierarchy import get_env_overrides, merge_configs
from lke.config.loader import load_configuration, load_toml
from lke.config.models import ApplicationConfig


def test_default_config_loading() -> None:
    """Test that defaults are correctly loaded."""
    config = get_default_config()
    assert isinstance(config, ApplicationConfig)
    assert config.logging.level == "INFO"
    assert config.embeddings.model_name == "nomic-embed-text"
    assert config.paths.vector_db == Path(".lke/vectors.lance")


def test_config_validation_success() -> None:
    """Test successful validation of valid overrides."""
    valid_data = {"logging": {"level": "DEBUG"}, "embeddings": {"dimensions": 1024}}
    # Create with defaults and overrides
    base = get_default_config().model_dump()
    merged = merge_configs(base, valid_data)
    config = ApplicationConfig(**merged)

    assert config.logging.level == "DEBUG"
    assert config.embeddings.dimensions == 1024
    assert config.search.max_results == 10  # Default preserved


def test_config_validation_failure() -> None:
    """Test validation catches invalid data."""
    invalid_data = {"logging": {"level": "INVALID_LEVEL"}}
    base = get_default_config().model_dump()
    merged = merge_configs(base, invalid_data)

    with pytest.raises(ValueError):
        ApplicationConfig(**merged)


def test_merge_configs() -> None:
    """Test recursive merging of dictionaries."""
    base = {"a": {"b": 1, "c": 2}, "d": 3}
    override = {"a": {"c": 4}, "e": 5}
    merged = merge_configs(base, override)

    assert merged == {"a": {"b": 1, "c": 4}, "d": 3, "e": 5}


def test_env_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test extracting environment variable overrides."""
    monkeypatch.setenv("LKE_LOGGING__LEVEL", "DEBUG")
    monkeypatch.setenv("LKE_EMBEDDINGS__DIMENSIONS", "1024")
    monkeypatch.setenv("LKE_WATCHER__ENABLED", "true")
    monkeypatch.setenv("LKE_SEARCH__SIMILARITY_THRESHOLD", "0.8")

    overrides = get_env_overrides()
    assert overrides["logging"]["level"] == "DEBUG"
    assert overrides["embeddings"]["dimensions"] == 1024
    assert overrides["watcher"]["enabled"] is True
    assert overrides["search"]["similarity_threshold"] == 0.8


def test_load_toml(tmp_path: Path) -> None:
    """Test loading configuration from a TOML file."""
    config_file = tmp_path / "config.toml"
    config_file.write_text("""
[logging]
level = "ERROR"

[embeddings]
chunk_size = 1024
""")

    data = load_toml(config_file)
    assert data["logging"]["level"] == "ERROR"
    assert data["embeddings"]["chunk_size"] == 1024


def test_load_toml_invalid_file(tmp_path: Path) -> None:
    """Test loading a non-existent or invalid TOML file."""
    with pytest.raises(ConfigLoadError):
        load_toml(tmp_path / "does_not_exist.toml")


def test_load_configuration_full_precedence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test the full precedence: Default -> TOML -> Env"""
    # 1. Defaults will have logging level INFO, max_results 10

    # 2. TOML overrides logging to WARNING and max_results to 20
    config_file = tmp_path / "config.toml"
    config_file.write_text("""
[logging]
level = "WARNING"

[search]
max_results = 20
""")

    # 3. Env overrides max_results to 30 and dimensions to 2048
    monkeypatch.setenv("LKE_SEARCH__MAX_RESULTS", "30")
    monkeypatch.setenv("LKE_EMBEDDINGS__DIMENSIONS", "2048")

    config = load_configuration(config_file)

    # Assert precedence
    assert config.logging.level == "WARNING"  # From TOML
    assert config.search.max_results == 30  # From Env (overrides TOML)
    assert config.embeddings.dimensions == 2048  # From Env
    assert config.ai_provider.timeout_seconds == 30  # From Default


def test_load_configuration_validation_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test load_configuration raises ConfigValidationError on invalid data."""
    monkeypatch.setenv("LKE_LOGGING__LEVEL", "SUPER_DEBUG")

    with pytest.raises(ConfigValidationError):
        load_configuration()


def test_serialization() -> None:
    """Test serialization of config back to dict."""
    config = get_default_config()
    dumped = config.model_dump()
    assert isinstance(dumped, dict)
    assert dumped["logging"]["level"] == "INFO"
    assert "vector_db" in dumped["paths"]
