"""Tests for domain events."""

from datetime import datetime
from uuid import UUID

from lke.domain.events import DocumentIndexed, FileChanged


def test_event_creation() -> None:
    """Test that events can be created and get auto-assigned ids and timestamps."""
    event = FileChanged.create(file_path="/path/to/file.md")

    assert isinstance(event.event_id, UUID)
    assert isinstance(event.occurred_at, datetime)
    assert event.file_path == "/path/to/file.md"


def test_event_immutability() -> None:
    """Test that events are immutable."""
    event = DocumentIndexed.create(document_id="doc1", file_path="test.md")

    try:
        # Frozen dataclasses raise a FrozenInstanceError (subclass of Exception) when modified
        import dataclasses

        event.document_id = "doc2"  # type: ignore
        raise AssertionError("Should have raised exception")
    except dataclasses.FrozenInstanceError:
        pass
