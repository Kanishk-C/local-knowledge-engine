"""Domain models for the journal (daily notes, people, events)."""

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class NoteRecord:
    """A note in the vault as seen by the journal index."""

    path: str  # vault-relative POSIX path, e.g. "journal/2026/2026-10-10.md"
    title: str
    note_date: date | None = None
    aliases: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Mention:
    """A note that references a person, event or any other note."""

    note: NoteRecord
    contexts: list[str]  # the lines where the mention occurs
    linked: bool = True  # False for plain-text (unlinked) mentions


@dataclass(frozen=True)
class FindHit:
    """A full-text search hit."""

    note: NoteRecord
    snippet: str  # matched terms are wrapped in MATCH_START / MATCH_END


@dataclass(frozen=True)
class LinkTarget:
    """A link target with usage statistics (e.g. a person or an event)."""

    name: str
    count: int  # number of notes linking to it
    last_date: date | None = None


MATCH_START = "\x02"
MATCH_END = "\x03"
