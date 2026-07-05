"""Generic storage protocol for the domain."""

from typing import Any, Protocol


class Storage(Protocol):
    """Generic key-value style storage protocol for arbitrary persistence."""

    def get(self, key: str) -> Any:
        """Retrieve a value by key."""
        ...

    def set(self, key: str, value: Any) -> None:
        """Store a value by key."""
        ...

    def exists(self, key: str) -> bool:
        """Check if a key exists."""
        ...

    def delete(self, key: str) -> None:
        """Delete a value by key."""
        ...
