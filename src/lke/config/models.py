"""Configuration models using Pydantic."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(default="INFO")
    file_path: Path | None = Field(default=None, description="Path to log file (None=stdout).")
    retention: str = Field(default="7 days", description="Log file retention policy.")


class EmbeddingsConfig(BaseModel):
    """Configuration for vector embeddings."""

    model_name: str = Field(default="nomic-embed-text")
    dimensions: int = Field(default=768, ge=1)
    chunk_size: int = Field(default=512, ge=100)
    min_chunk_size: int = Field(default=100, ge=1)
    chunk_overlap: int = Field(default=50, ge=0)


class AIProviderConfig(BaseModel):
    """Configuration for the AI provider (e.g., Ollama)."""

    base_url: str = Field(default="http://localhost:11434")
    timeout_seconds: int = Field(default=30, ge=1)
    max_retries: int = Field(default=3, ge=0)


class ParsingConfig(BaseModel):
    """Configuration for document parsing."""

    supported_extensions: list[str] = Field(default_factory=lambda: [".md", ".txt"])
    exclude_patterns: list[str] = Field(default_factory=lambda: [".git", "node_modules"])


class SearchConfig(BaseModel):
    """Configuration for vector search."""

    max_results: int = Field(default=10, ge=1)
    similarity_threshold: float = Field(default=0.5, ge=0.0, le=1.0)


class WatcherConfig(BaseModel):
    """Configuration for filesystem watcher."""

    enabled: bool = Field(default=False)
    debounce_seconds: float = Field(default=1.0, ge=0.1)


class PathsConfig(BaseModel):
    """Configuration for paths."""

    vector_db: Path = Field(default=Path(".lke/vectors.lance"))
    metadata_db: Path = Field(default=Path(".lke/metadata.duckdb"))
    cache_dir: Path = Field(default=Path(".lke/cache"))


class ApplicationConfig(BaseModel):
    """Root configuration model containing all sub-configurations."""

    environment: Literal["development", "production", "testing"] = Field(default="production")
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    embeddings: EmbeddingsConfig = Field(default_factory=EmbeddingsConfig)
    ai_provider: AIProviderConfig = Field(default_factory=AIProviderConfig)
    parsing: ParsingConfig = Field(default_factory=ParsingConfig)
    search: SearchConfig = Field(default_factory=SearchConfig)
    watcher: WatcherConfig = Field(default_factory=WatcherConfig)
    paths: PathsConfig = Field(default_factory=PathsConfig)
