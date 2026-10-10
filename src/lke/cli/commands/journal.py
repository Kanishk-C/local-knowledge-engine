"""Journal commands: today, log, find, who, day, onthisday, links.

These commands only need the standard library plus the CLI basics, so they
work without Ollama or any of the optional AI dependencies installed.
"""

import os
import shlex
import subprocess
import sys
from datetime import date
from pathlib import Path
from urllib.parse import quote

import typer
from rich.markdown import Markdown
from rich.rule import Rule
from rich.text import Text

from lke.application.services.journal_service import JournalService, parse_day
from lke.cli.console import console
from lke.cli.formatting import print_error, print_info, print_success, print_warning
from lke.config.loader import load_configuration
from lke.domain.models.journal import MATCH_END, MATCH_START, NoteRecord


def get_journal_service() -> JournalService:
    """Build the journal service from configuration (no AI dependencies)."""
    config = load_configuration().journal
    vault = config.vault_path.expanduser()
    if not vault.is_dir():
        print_error(f"Vault folder not found: {vault}")
        console.print(
            "[secondary]Set journal.vault_path in your config"
            " or LKE_JOURNAL__VAULT_PATH.[/secondary]"
        )
        raise typer.Exit(code=1)
    return JournalService(config)


def _day_option(value: str) -> date:
    try:
        return parse_day(value)
    except ValueError as e:
        raise typer.BadParameter(str(e)) from e


def _open_note(path: Path, open_with: str) -> None:
    if open_with == "editor":
        editor = os.environ.get("VISUAL") or os.environ.get("EDITOR")
        if not editor:
            print_warning("Set $EDITOR (or $VISUAL) to open notes in your editor.")
            return
        subprocess.call([*shlex.split(editor), str(path)])
    elif open_with == "obsidian":
        uri = f"obsidian://open?path={quote(str(path.resolve()), safe='')}"
        if sys.platform == "darwin":
            subprocess.Popen(["open", uri])
        elif sys.platform == "win32":
            os.startfile(uri)  # type: ignore[attr-defined]
        else:
            subprocess.Popen(
                ["xdg-open", uri], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )


def _note_label(note: NoteRecord) -> Text:
    label = Text()
    label.append(note.note_date.isoformat() if note.note_date else "----------", style="info")
    label.append("  ")
    label.append(note.title, style="header")
    label.append(f"  {note.path}", style="filepath")
    return label


def _highlight(snippet: str) -> Text:
    text = Text()
    rest = snippet
    while MATCH_START in rest:
        before, _, rest = rest.partition(MATCH_START)
        match, _, rest = rest.partition(MATCH_END)
        text.append(before)
        text.append(match, style="bold yellow")
    text.append(rest)
    return text


def today(
    day: str = typer.Argument("today", help="today, yesterday, -N (days ago) or YYYY-MM-DD."),
    open_with: str | None = typer.Option(
        None, "--open", "-o", help="print, editor or obsidian (default from config)."
    ),
) -> None:
    """Create (if needed) and open the daily note."""
    service = get_journal_service()
    path, created = service.ensure_daily(_day_option(day))
    if created:
        print_success(f"Created {path.relative_to(service.vault)}")
    mode = open_with or load_configuration().journal.open_with
    if mode == "print":
        console.print(str(path), highlight=False, soft_wrap=True)
    else:
        _open_note(path, mode)


def log(
    text: list[str] = typer.Argument(  # noqa: B008
        ..., help="What happened. Use [[Name]] to link people/events."
    ),
) -> None:
    """Quick capture: append a timestamped line to today's note."""
    service = get_journal_service()
    path = service.log(" ".join(text))
    print_success(f"Logged to {path.relative_to(service.vault)}")


def find(
    query: list[str] = typer.Argument(  # noqa: B008
        None, help="Words to search for (all must match)."
    ),
    tag: str | None = typer.Option(None, "--tag", "-t", help="Only notes with this tag."),
    limit: int = typer.Option(20, "--limit", "-n", help="Maximum number of results."),
) -> None:
    """Instant full-text search across all notes."""
    words = " ".join(query or [])
    if not words and not tag:
        raise typer.BadParameter("Give some words to search for and/or --tag.")
    hits = get_journal_service().find(words, tag=tag, limit=limit)
    if not hits:
        print_warning("No matching notes.")
        return
    for hit in hits:
        console.print(_note_label(hit.note))
        if hit.snippet:
            console.print(Text("    ").append(_highlight(hit.snippet)))


def who(
    name: str = typer.Argument(..., help="Person, event, place... (note name or alias)."),
    unlinked: bool = typer.Option(
        False, "--unlinked", "-u", help="Also include plain-text mentions without [[links]]."
    ),
) -> None:
    """Timeline of every note that mentions a person, event or note."""
    service = get_journal_service()
    mentions = service.mentions(name, unlinked=unlinked)
    _, target = service.index.resolve_keys(name)
    if target:
        print_info(f"[[{Path(target.path).stem}]]  {target.path}")
    if not mentions:
        print_warning(f"No notes mention '{name}'." + ("" if unlinked else " Try --unlinked."))
        return
    for mention in mentions:
        label = _note_label(mention.note)
        if not mention.linked:
            label.append("  (unlinked)", style="secondary")
        console.print(label)
        for context in mention.contexts[:3]:
            console.print(Text("    ").append(_highlight(context)), style="secondary")
    console.print(Text(f"{len(mentions)} note(s)", style="secondary"))


def day(
    when: str = typer.Argument("today", help="today, yesterday, -N (days ago) or YYYY-MM-DD."),
) -> None:
    """Show the note(s) written on a given day."""
    service = get_journal_service()
    the_day = _day_option(when)
    notes = service.notes_for_day(the_day)
    if not notes:
        print_warning(f"Nothing written on {the_day.isoformat()}.")
        return
    for note in notes:
        console.print(Rule(_note_label(note)))
        console.print(Markdown(service.read(note)))


def onthisday(
    when: str = typer.Argument("today", help="today, yesterday, -N (days ago) or YYYY-MM-DD."),
) -> None:
    """What you wrote on this day in previous years."""
    service = get_journal_service()
    the_day = _day_option(when)
    notes = service.on_this_day(the_day)
    if not notes:
        print_warning(f"No earlier entries for {the_day.strftime('%d %B')}.")
        return
    for note in notes:
        console.print(Rule(_note_label(note)))
        console.print(Markdown(service.read(note)))


def links(
    folder: str | None = typer.Option(
        None, "--folder", "-f", help="Only targets whose note lives here, e.g. people."
    ),
    limit: int = typer.Option(30, "--limit", "-n", help="Maximum number of entries."),
) -> None:
    """Most-mentioned people, events and notes, with when you last mentioned them."""
    targets = get_journal_service().link_targets(limit=limit, folder=folder)
    if not targets:
        print_warning("No [[links]] found yet.")
        return
    for target in targets:
        line = Text()
        line.append(f"{target.count:>4}  ", style="info")
        line.append(target.name, style="header")
        if target.last_date:
            line.append(f"  last {target.last_date.isoformat()}", style="secondary")
        console.print(line)


def register(app: typer.Typer) -> None:
    """Register the journal commands on the root CLI app."""
    app.command(rich_help_panel="Journal")(today)
    app.command(rich_help_panel="Journal")(log)
    app.command(rich_help_panel="Journal")(find)
    app.command(rich_help_panel="Journal")(who)
    app.command(rich_help_panel="Journal")(day)
    app.command(rich_help_panel="Journal")(onthisday)
    app.command(rich_help_panel="Journal")(links)
