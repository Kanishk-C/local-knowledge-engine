"""Tests for the SQLite FTS5 journal index."""

import os
from datetime import date
from pathlib import Path

import pytest

from lke.domain.models.journal import MATCH_END, MATCH_START
from lke.infrastructure.journal.note_index import NoteIndex, _to_fts_query, link_key


def _write(vault: Path, rel: str, text: str) -> Path:
    path = vault / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    _write(tmp_path, "people/Alice.md", "---\naliases: [Ali]\n---\n# Alice\nCollege friend.\n")
    _write(
        tmp_path, "events/Goa trip.md", "# Goa trip\nWith [[Alice]] and [[people/Bob.md|Bobby]].\n"
    )
    _write(
        tmp_path,
        "journal/2025/2025-10-10.md",
        "Went to the dentist. Ali called. #health\n",
    )
    _write(
        tmp_path,
        "journal/2026/2026-10-10.md",
        "---\npeople: ['[[Bob]]']\n---\n- 09:00 Coffee with [[Alice#Work|Al]] #Health\n"
        "- 10:00 Booked [[Goa trip]]\n",
    )
    _write(tmp_path, ".obsidian/workspace.md", "[[Alice]] should be ignored")
    _write(tmp_path, "undated.md", "---\ndate: 2024-01-02\n---\nMentions [[Alice]] too.\n")
    return tmp_path


@pytest.fixture
def index(vault: Path) -> NoteIndex:
    idx = NoteIndex(vault, vault / ".lke" / "journal.db")
    idx.sync()
    return idx


def test_link_key_normalises_paths_and_case() -> None:
    assert link_key("people/Alice.md") == "alice"
    assert link_key(" Alice ") == "alice"


def test_fts_query_quotes_words_and_keeps_prefix() -> None:
    assert _to_fts_query('dent* "OR" -x') == '"dent"* "OR" "x"'
    assert _to_fts_query("!!!") == ""


def test_sync_skips_hidden_dirs_and_reads_dates(index: NoteIndex) -> None:
    assert index.get(".obsidian/workspace.md") is None
    note = index.get("journal/2026/2026-10-10.md")
    assert note is not None
    assert note.note_date == date(2026, 10, 10)
    assert note.tags == ["health"]
    undated = index.get("undated.md")
    assert undated is not None and undated.note_date == date(2024, 1, 2)
    alice = index.get("people/Alice.md")
    assert alice is not None and alice.title == "Alice" and alice.aliases == ["Ali"]


def test_sync_is_incremental_and_handles_deletes(vault: Path, index: NoteIndex) -> None:
    assert index.sync() == 0
    path = vault / "undated.md"
    path.write_text("changed content here", encoding="utf-8")
    os.utime(path, ns=(1, 1))
    assert index.sync() == 1
    assert index.find("changed")
    path.unlink()
    assert index.sync() == 1
    assert index.get("undated.md") is None
    assert not index.find("changed")


def test_find_highlights_and_filters_by_tag(index: NoteIndex) -> None:
    hits = index.find("dentist")
    assert [h.note.path for h in hits] == ["journal/2025/2025-10-10.md"]
    assert f"{MATCH_START}dentist{MATCH_END}" in hits[0].snippet
    assert [h.note.path for h in index.find("dent*")] == ["journal/2025/2025-10-10.md"]
    tagged = {h.note.path for h in index.find("", tag="#health")}
    assert tagged == {"journal/2025/2025-10-10.md", "journal/2026/2026-10-10.md"}
    assert index.find("") == []


def test_mentions_resolves_aliases_and_sorts_newest_first(index: NoteIndex) -> None:
    mentions = index.mentions("Ali")
    assert [m.note.path for m in mentions] == [
        "journal/2026/2026-10-10.md",
        "undated.md",
        "events/Goa trip.md",
    ]
    assert mentions[0].contexts == ["- 09:00 Coffee with [[Alice#Work|Al]] #Health"]


def test_mentions_unlinked_finds_plain_text(index: NoteIndex) -> None:
    mentions = index.mentions("alice", unlinked=True)
    unlinked = [m for m in mentions if not m.linked]
    assert [m.note.path for m in unlinked] == ["journal/2025/2025-10-10.md"]


def test_mentions_includes_frontmatter_links(index: NoteIndex) -> None:
    paths = {m.note.path for m in index.mentions("Bob")}
    assert paths == {"journal/2026/2026-10-10.md", "events/Goa trip.md"}


def test_dates_and_on_this_day(index: NoteIndex) -> None:
    assert [n.path for n in index.note_for_date(date(2025, 10, 10))] == [
        "journal/2025/2025-10-10.md"
    ]
    assert [n.path for n in index.notes_on_month_day(date(2026, 10, 10))] == [
        "journal/2025/2025-10-10.md"
    ]


def test_link_targets_counts_and_folder_filter(index: NoteIndex) -> None:
    targets = {t.name: t for t in index.link_targets()}
    assert targets["Alice"].count == 3
    assert targets["Alice"].last_date == date(2026, 10, 10)
    assert targets["Bob"].count == 2  # no note for Bob: keeps the written name
    assert [t.name for t in index.link_targets(folder="people")] == ["Alice"]


def test_schema_version_mismatch_rebuilds(vault: Path, index: NoteIndex) -> None:
    index.conn.execute("PRAGMA user_version = 999")
    index.close()
    fresh = NoteIndex(vault, vault / ".lke" / "journal.db")
    assert fresh.get("people/Alice.md") is None
    fresh.sync()
    assert fresh.get("people/Alice.md") is not None
