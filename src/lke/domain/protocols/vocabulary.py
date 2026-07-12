"""Vocabulary protocols for tagging and categorization."""

from typing import Protocol


class TagVocabulary(Protocol):
    """Protocol for managing available tags and validating new ones."""

    def get_all(self) -> list[str]:
        """Retrieve all known tags."""
        ...

    def add(self, tag: str) -> None:
        """Add a new tag to the vocabulary."""
        ...


class FolderVocabulary(Protocol):
    """Protocol for managing available folders and validating new ones."""

    def get_all(self) -> list[str]:
        """Retrieve all known folders."""
        ...

    def add(self, folder: str) -> None:
        """Add a new folder to the vocabulary."""
        ...
