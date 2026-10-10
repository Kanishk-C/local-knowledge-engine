"""SQLite FTS5 index over a Markdown vault: full-text search, links and dates.

Uses only the Python standard library (sqlite3) so the journal core stays
lightweight. The index is a cache: it can be deleted at any time and is
rebuilt incrementally from the Markdown files on the next sync.
"""

import json
import os
import re
import sqlite3
from collections.abc import Iterator
from datetime import date, datetime
from pathlib import Path
from typing import Any

from lke.domain.models.journal import (
    MATCH_END,
    MATCH_START,
    FindHit,
    LinkTarget,
    Mention,
    NoteRecord,
)
from lke.domain.models.source import DataSource, SourceType
from lke.infrastructure.parsing.markdown_parser import MarkdownParser

_SCHEMA_VERSION = 1

_SCHEMA = """
CREATE TABLE IF NOT EXISTS notes (
    path TEXT PRIMARY KEY,
    key TEXT NOT NULL,
    title TEXT NOT NULL,
    note_date TEXT,
    mtime_ns INTEGER NOT NULL,
    size INTEGER NOT NULL,
    aliases TEXT NOT NULL DEFAULT '[]',
    tags TEXT NOT NULL DEFAULT '[]'
);
CREATE INDEX IF NOT EXISTS notes_key ON notes(key);
CREATE INDEX IF NOT EXISTS notes_date ON notes(note_date);
CREATE TABLE IF NOT EXISTS links (
    src TEXT NOT NULL,
    target TEXT NOT NULL,
    name TEXT NOT NULL,
    context TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS links_target ON links(target);
CREATE INDEX IF NOT EXISTS links_src ON links(src);
CREATE TABLE IF NOT EXISTS tags (
    path TEXT NOT NULL,
    tag TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS tags_tag ON tags(tag);
CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(
    path UNINDEXED, title, body, tokenize = 'porter unicode61'
);
"""

# [[Target]], [[folder/Target#Heading|Alias]], ![[embed.png]]
_WIKILINK = re.compile(r"!?\[\[([^\]|#]*)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")
_DATE_IN_NAME = re.compile(r"(\d{4}-\d{2}-\d{2})")
_H1 = re.compile(r"^#\s+(.+)$", re.MULTILINE)
_FTS_TOKEN = re.compile(r"\w+\*?", re.UNICODE)
_MAX_CONTEXT = 240


def link_key(name: str) -> str:
    """Normalise a link target or note name to its lookup key.

    ``[[people/Alice.md]]``, ``[[Alice]]`` and ``alice`` all map to ``alice``.
    """
    name = name.strip().replace("\\", "/").rsplit("/", 1)[-1]
    if name.lower().endswith(".md"):
        name = name[:-3]
    return name.strip().casefold()


def _to_fts_query(text: str) -> str:
    """Turn free text into a safe FTS5 query: every word must match (AND).

    A trailing ``*`` on a word keeps prefix matching (``dent*``).
    """
    terms = []
    for token in _FTS_TOKEN.findall(text):
        prefix = token.endswith("*")
        word = token.rstrip("*").replace('"', "")
        if word:
            terms.append(f'"{word}"*' if prefix else f'"{word}"')
    return " ".join(terms)


def _parse_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        match = _DATE_IN_NAME.search(value)
        if match:
            try:
                return date.fromisoformat(match.group(1))
            except ValueError:
                return None
    return None


def _as_str_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(v) for v in value if v is not None]
    return []


class NoteIndex:
    """Incremental full-text and link index for a Markdown vault."""

    def __init__(
        self,
        vault_path: Path,
        db_path: Path,
        exclude_patterns: list[str] | None = None,
    ) -> None:
        self._vault = vault_path
        self._db_path = db_path
        self._exclude = set(exclude_patterns or [])
        self._parser = MarkdownParser()
        self._conn: sqlite3.Connection | None = None

    # ------------------------------------------------------------------ setup

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(self._db_path)
            conn.row_factory = sqlite3.Row
            version = conn.execute("PRAGMA user_version").fetchone()[0]
            if version != _SCHEMA_VERSION:
                # The index is a disposable cache: rebuild on schema change.
                for table in ("notes", "links", "tags", "notes_fts"):
                    conn.execute(f"DROP TABLE IF EXISTS {table}")
                conn.execute(f"PRAGMA user_version = {_SCHEMA_VERSION}")
            conn.executescript(_SCHEMA)
            self._conn = conn
        return self._conn

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    # ------------------------------------------------------------------- sync

    def _iter_markdown(self) -> Iterator[Path]:
        for root, dirs, files in os.walk(self._vault):
            # Skip hidden dirs (.obsidian, .lke, .git, .trash) and excluded ones.
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in self._exclude]
            for name in files:
                if name.lower().endswith(".md") and not name.startswith("."):
                    yield Path(root) / name

    def sync(self) -> int:
        """Bring the index up to date with the vault. Returns notes (re)indexed."""
        conn = self.conn
        known = {
            row["path"]: (row["mtime_ns"], row["size"])
            for row in conn.execute("SELECT path, mtime_ns, size FROM notes")
        }
        seen: set[str] = set()
        changed = 0
        with conn:
            for file in self._iter_markdown():
                rel = file.relative_to(self._vault).as_posix()
                seen.add(rel)
                try:
                    stat = file.stat()
                except OSError:
                    continue
                if known.get(rel) == (stat.st_mtime_ns, stat.st_size):
                    continue
                self._index_file(file, rel, stat.st_mtime_ns, stat.st_size)
                changed += 1
            for rel in known.keys() - seen:
                self._delete(rel)
                changed += 1
        return changed

    def _delete(self, rel: str) -> None:
        conn = self.conn
        conn.execute("DELETE FROM notes WHERE path = ?", (rel,))
        conn.execute("DELETE FROM links WHERE src = ?", (rel,))
        conn.execute("DELETE FROM tags WHERE path = ?", (rel,))
        conn.execute("DELETE FROM notes_fts WHERE path = ?", (rel,))

    def _index_file(self, file: Path, rel: str, mtime_ns: int, size: int) -> None:
        try:
            parsed = self._parser.parse(DataSource(uri=str(file), source_type=SourceType.OBSIDIAN))
        except Exception:
            return
        fm = parsed.frontmatter
        body = parsed.raw_text

        title_match = _H1.search(body)
        title = str(fm.get("title") or (title_match.group(1) if title_match else file.stem))
        note_date = _parse_date(file.stem) or _parse_date(fm.get("date"))
        aliases = _as_str_list(fm.get("aliases") or fm.get("alias"))
        tags = sorted({t.lstrip("#").casefold() for t in parsed.tags})

        self._delete(rel)
        conn = self.conn
        conn.execute(
            "INSERT INTO notes (path, key, title, note_date, mtime_ns, size, aliases, tags)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                rel,
                link_key(file.stem),
                title,
                note_date.isoformat() if note_date else None,
                mtime_ns,
                size,
                json.dumps(aliases),
                json.dumps(tags),
            ),
        )
        conn.execute(
            "INSERT INTO notes_fts (path, title, body) VALUES (?, ?, ?)", (rel, title, body)
        )
        conn.executemany("INSERT INTO tags (path, tag) VALUES (?, ?)", [(rel, t) for t in tags])

        lines = [(line.strip(), line) for line in body.splitlines()]
        # Frontmatter links count too, e.g. `people: ["[[Alice]]"]`
        lines += [(f"(frontmatter) {item}", item) for v in fm.values() for item in _as_str_list(v)]
        links: list[tuple[str, str, str, str]] = []
        for context, line in lines:
            for match in _WIKILINK.finditer(line):
                name = match.group(1).strip().rsplit("/", 1)[-1].removesuffix(".md")
                if name:
                    links.append((rel, link_key(name), name, context[:_MAX_CONTEXT]))
        conn.executemany(
            "INSERT INTO links (src, target, name, context) VALUES (?, ?, ?, ?)", links
        )

    # ---------------------------------------------------------------- queries

    @staticmethod
    def _record(row: sqlite3.Row) -> NoteRecord:
        return NoteRecord(
            path=row["path"],
            title=row["title"],
            note_date=date.fromisoformat(row["note_date"]) if row["note_date"] else None,
            aliases=json.loads(row["aliases"]),
            tags=json.loads(row["tags"]),
        )

    def get(self, rel_path: str) -> NoteRecord | None:
        row = self.conn.execute("SELECT * FROM notes WHERE path = ?", (rel_path,)).fetchone()
        return self._record(row) if row else None

    def find(self, query: str, tag: str | None = None, limit: int = 20) -> list[FindHit]:
        """Full-text search (all words must match), optionally filtered by tag."""
        fts_query = _to_fts_query(query)
        params: list[Any] = []
        if fts_query:
            sql = (
                "SELECT n.*, snippet(notes_fts, 2, ?, ?, '…', 16) AS snip"
                " FROM notes_fts JOIN notes n ON n.path = notes_fts.path"
                " WHERE notes_fts MATCH ?"
            )
            params += [MATCH_START, MATCH_END, fts_query]
            order = " ORDER BY bm25(notes_fts, 0, 5.0, 1.0)"
        elif tag:
            sql = "SELECT n.*, '' AS snip FROM notes n WHERE 1"
            order = " ORDER BY n.note_date DESC, n.path"
        else:
            return []
        if tag:
            sql += " AND n.path IN (SELECT path FROM tags WHERE tag = ?)"
            params.append(tag.lstrip("#").casefold())
        sql += order + " LIMIT ?"
        params.append(limit)
        return [
            FindHit(note=self._record(row), snippet=row["snip"].replace("\n", " "))
            for row in self.conn.execute(sql, params)
        ]

    def resolve_keys(self, name: str) -> tuple[set[str], NoteRecord | None]:
        """Resolve a name (or alias) to every link key that refers to it."""
        key = link_key(name)
        keys = {key}
        target: NoteRecord | None = None
        rows = self.conn.execute("SELECT * FROM notes WHERE key = ?", (key,)).fetchall()
        if not rows:
            # Try aliases: a note `Alice.md` with `aliases: [Ali]` answers "Ali".
            for row in self.conn.execute("SELECT * FROM notes WHERE aliases != '[]'"):
                if key in {link_key(a) for a in json.loads(row["aliases"])}:
                    rows = [row]
                    break
        if rows:
            target = self._record(rows[0])
            keys.add(link_key(Path(target.path).stem))
            keys.update(link_key(a) for a in target.aliases)
        return keys, target

    def mentions(self, name: str, unlinked: bool = False) -> list[Mention]:
        """Every note linking to ``name`` (newest first), plus optional text mentions."""
        keys, target = self.resolve_keys(name)
        own_path = target.path if target else None
        placeholders = ",".join("?" * len(keys))
        rows = self.conn.execute(
            f"SELECT n.*, l.context FROM links l JOIN notes n ON n.path = l.src"
            f" WHERE l.target IN ({placeholders})",
            sorted(keys),
        ).fetchall()

        grouped: dict[str, tuple[sqlite3.Row, list[str]]] = {}
        for row in rows:
            if row["path"] == own_path:
                continue
            entry = grouped.setdefault(row["path"], (row, []))
            if row["context"] not in entry[1]:
                entry[1].append(row["context"])
        result = [Mention(note=self._record(r), contexts=c) for r, c in grouped.values()]

        if unlinked:
            seen = set(grouped) | {own_path}
            terms = {name, *(target.aliases if target else [])}
            if target:
                terms.add(Path(target.path).stem)
            for term in sorted(terms):
                for hit in self.find(term, limit=200):
                    if hit.note.path not in seen:
                        seen.add(hit.note.path)
                        result.append(Mention(note=hit.note, contexts=[hit.snippet], linked=False))

        return _newest_first(result)

    def note_for_date(self, day: date) -> list[NoteRecord]:
        rows = self.conn.execute(
            "SELECT * FROM notes WHERE note_date = ? ORDER BY path", (day.isoformat(),)
        )
        return [self._record(r) for r in rows]

    def notes_on_month_day(self, day: date) -> list[NoteRecord]:
        """Notes dated on the same month and day as ``day`` in earlier years."""
        rows = self.conn.execute(
            "SELECT * FROM notes WHERE substr(note_date, 6) = ? AND note_date < ?"
            " ORDER BY note_date DESC, path",
            (day.isoformat()[5:], day.isoformat()),
        )
        return [self._record(r) for r in rows]

    def link_targets(self, limit: int = 50, folder: str | None = None) -> list[LinkTarget]:
        """Most-linked targets (people, events, places...) with last-mentioned date."""
        rows = self.conn.execute(
            "SELECT l.target AS target, MIN(l.name) AS name,"
            " COUNT(DISTINCT l.src) AS cnt, MAX(n.note_date) AS last"
            " FROM links l JOIN notes n ON n.path = l.src"
            " GROUP BY l.target ORDER BY cnt DESC, last DESC LIMIT ?",
            (limit if folder is None else -1,),
        ).fetchall()
        names = {
            row["key"]: (row["path"], Path(row["path"]).stem)
            for row in self.conn.execute("SELECT key, path FROM notes")
        }
        prefix = folder.strip("/") + "/" if folder else None
        result: list[LinkTarget] = []
        for row in rows:
            path, display = names.get(row["target"], (None, row["name"]))
            if prefix and not (path and path.startswith(prefix)):
                continue
            result.append(
                LinkTarget(
                    name=display,
                    count=row["cnt"],
                    last_date=date.fromisoformat(row["last"]) if row["last"] else None,
                )
            )
            if len(result) >= limit:
                break
        return result


def _newest_first(mentions: list[Mention]) -> list[Mention]:
    """Dated notes newest first, then undated notes alphabetically."""
    dated = [m for m in mentions if m.note.note_date]
    undated = [m for m in mentions if not m.note.note_date]
    dated.sort(key=lambda m: (m.note.note_date, m.note.path), reverse=True)
    undated.sort(key=lambda m: m.note.path)
    return dated + undated
