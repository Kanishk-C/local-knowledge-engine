"""Journal service: daily notes, quick capture, search and mentions."""

import re
from datetime import date, datetime, timedelta
from pathlib import Path

from lke.config.models import JournalConfig
from lke.domain.models.journal import FindHit, LinkTarget, Mention, NoteRecord
from lke.infrastructure.journal.note_index import NoteIndex

_FRONTMATTER = re.compile(r"\A---\n.*?\n---\n?", re.DOTALL)

DEFAULT_TEMPLATE = """---
date: {{date}}
tags: [daily]
---
# {{weekday}}, {{long_date}}

"""


def parse_day(value: str, today: date | None = None) -> date:
    """Parse ``today``, ``yesterday``, ``-N`` (days ago) or ``YYYY-MM-DD``."""
    today = today or date.today()
    text = value.strip().lower()
    if text in ("", "today"):
        return today
    if text == "yesterday":
        return today - timedelta(days=1)
    if text == "tomorrow":
        return today + timedelta(days=1)
    if text.startswith("-") and text[1:].isdigit():
        return today - timedelta(days=int(text[1:]))
    try:
        return date.fromisoformat(text)
    except ValueError as e:
        raise ValueError(
            f"Unrecognised date '{value}'. Use YYYY-MM-DD, today, yesterday or -N."
        ) from e


class JournalService:
    """Daily-note workflow on top of a plain Markdown vault."""

    def __init__(self, config: JournalConfig, index: NoteIndex | None = None) -> None:
        self._config = config
        self.vault = config.vault_path.expanduser().resolve()
        self._index = index or NoteIndex(self.vault, self.vault / config.index_file)
        self._synced = False

    @property
    def index(self) -> NoteIndex:
        """The note index, synced with the vault once per service lifetime."""
        if not self._synced:
            self._index.sync()
            self._synced = True
        return self._index

    # ------------------------------------------------------------ daily notes

    def daily_path(self, day: date) -> Path:
        rel = day.strftime(self._config.daily_format) + ".md"
        return self.vault / self._config.daily_folder / rel

    def _render_template(self, day: date) -> str:
        template = DEFAULT_TEMPLATE
        if self._config.template:
            template_path = self.vault / self._config.template
            template = template_path.read_text(encoding="utf-8")
        values = {
            "date": day.isoformat(),
            "title": self.daily_path(day).stem,
            "weekday": day.strftime("%A"),
            "long_date": f"{day.day} {day.strftime('%B %Y')}",
            "time": datetime.now().strftime("%H:%M"),
        }
        for key, value in values.items():
            template = template.replace("{{" + key + "}}", value)
        return template

    def ensure_daily(self, day: date) -> tuple[Path, bool]:
        """Return the daily note path, creating it from the template if missing."""
        path = self.daily_path(day)
        if path.exists():
            return path, False
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self._render_template(day), encoding="utf-8")
        self._synced = False
        return path, True

    def log(self, text: str, when: datetime | None = None) -> Path:
        """Append a timestamped bullet to the day's note (creating it if needed)."""
        when = when or datetime.now()
        path, _ = self.ensure_daily(when.date())
        existing = path.read_text(encoding="utf-8")
        separator = "" if existing.endswith("\n") or not existing else "\n"
        with path.open("a", encoding="utf-8") as f:
            f.write(f"{separator}- {when.strftime('%H:%M')} {text.strip()}\n")
        self._synced = False
        return path

    # ---------------------------------------------------------------- queries

    def find(self, query: str, tag: str | None = None, limit: int = 20) -> list[FindHit]:
        return self.index.find(query, tag=tag, limit=limit)

    def mentions(self, name: str, unlinked: bool = False) -> list[Mention]:
        return self.index.mentions(name, unlinked=unlinked)

    def notes_for_day(self, day: date) -> list[NoteRecord]:
        return self.index.note_for_date(day)

    def on_this_day(self, day: date) -> list[NoteRecord]:
        return self.index.notes_on_month_day(day)

    def link_targets(self, limit: int = 50, folder: str | None = None) -> list[LinkTarget]:
        return self.index.link_targets(limit=limit, folder=folder)

    def read(self, note: NoteRecord) -> str:
        """The note's Markdown body, without YAML frontmatter."""
        text = (self.vault / note.path).read_text(encoding="utf-8")
        return _FRONTMATTER.sub("", text, count=1).lstrip("\n")
