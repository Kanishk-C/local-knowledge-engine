"""Tests for the journal service."""

from datetime import date, datetime
from pathlib import Path

import pytest

from lke.application.services.journal_service import JournalService, parse_day
from lke.config.models import JournalConfig


@pytest.fixture
def service(tmp_path: Path) -> JournalService:
    return JournalService(JournalConfig(vault_path=tmp_path))


def test_parse_day() -> None:
    ref = date(2026, 10, 10)
    assert parse_day("today", ref) == ref
    assert parse_day("Yesterday", ref) == date(2026, 10, 9)
    assert parse_day("-10", ref) == date(2026, 9, 30)
    assert parse_day("2024-02-29", ref) == date(2024, 2, 29)
    with pytest.raises(ValueError, match="Unrecognised date"):
        parse_day("next week", ref)


def test_ensure_daily_creates_once_from_default_template(service: JournalService) -> None:
    path, created = service.ensure_daily(date(2026, 10, 10))
    assert created
    assert path == service.vault / "journal" / "2026" / "2026-10-10.md"
    text = path.read_text(encoding="utf-8")
    assert "date: 2026-10-10" in text
    assert "# Saturday, 10 October 2026" in text
    path.write_text("edited", encoding="utf-8")
    assert service.ensure_daily(date(2026, 10, 10)) == (path, False)
    assert path.read_text(encoding="utf-8") == "edited"


def test_custom_template_and_format(tmp_path: Path) -> None:
    (tmp_path / "tpl.md").write_text("{{title}} / {{date}} / {{weekday}}\n", encoding="utf-8")
    config = JournalConfig(
        vault_path=tmp_path, daily_folder="Daily", daily_format="%Y-%m-%d", template=Path("tpl.md")
    )
    path, _ = JournalService(config).ensure_daily(date(2026, 1, 5))
    assert path == tmp_path.resolve() / "Daily" / "2026-01-05.md"
    assert path.read_text(encoding="utf-8") == "2026-01-05 / 2026-01-05 / Monday\n"


def test_log_appends_and_is_searchable(service: JournalService) -> None:
    when = datetime(2026, 10, 10, 9, 5)
    path, _ = service.ensure_daily(when.date())
    path.write_text("no trailing newline", encoding="utf-8")
    service.log("  Met [[Alice]] for coffee ", when=when)
    service.log("Dentist", when=when.replace(hour=14))
    assert path.read_text(encoding="utf-8").endswith(
        "no trailing newline\n- 09:05 Met [[Alice]] for coffee\n- 14:05 Dentist\n"
    )
    assert [m.note.path for m in service.mentions("alice")] == ["journal/2026/2026-10-10.md"]
    assert service.find("coffee")
    assert [n.path for n in service.notes_for_day(when.date())] == ["journal/2026/2026-10-10.md"]


def test_read_strips_frontmatter(service: JournalService) -> None:
    path, _ = service.ensure_daily(date(2026, 10, 10))
    note = service.notes_for_day(date(2026, 10, 10))[0]
    assert service.read(note).startswith("# Saturday")
    assert path.read_text(encoding="utf-8").startswith("---")
