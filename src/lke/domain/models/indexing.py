"""Domain models for indexing results."""

from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path


@dataclass(frozen=True)
class IndexingResult:
    """Result of indexing a single document."""

    file_path: Path
    document_id: str | None
    chunks_created: int
    embedded_chunks: int
    duration: timedelta
    success: bool
    error_message: str | None = None


@dataclass
class BatchIndexingResult:
    """Result of a batch indexing operation."""

    successful_documents: int = 0
    failed_documents: int = 0
    total_chunks: int = 0
    total_duration: timedelta = field(default_factory=timedelta)
    results: list[IndexingResult] = field(default_factory=list)
    errors: dict[Path, str] = field(default_factory=dict)

    def add_result(self, result: IndexingResult) -> None:
        """Add a single indexing result to the batch."""
        self.results.append(result)
        self.total_duration += result.duration

        if result.success:
            self.successful_documents += 1
            self.total_chunks += result.chunks_created
        else:
            self.failed_documents += 1
            if result.error_message:
                self.errors[result.file_path] = result.error_message
