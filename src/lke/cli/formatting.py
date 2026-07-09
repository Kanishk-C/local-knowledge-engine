"""Formatting helpers and standardized visual components for the CLI."""

from rich.panel import Panel
from rich.table import Table

from lke.cli.console import console
from lke.domain.models.search import SearchResult


def print_success(message: str) -> None:
    """Print a success message with a checkmark."""
    console.print(f"[success]✓[/success] {message}")


def print_error(message: str) -> None:
    """Print an error message with a cross."""
    console.print(f"[error]✗[/error] {message}")


def print_warning(message: str) -> None:
    """Print a warning message with an exclamation point."""
    console.print(f"[warning]![/warning] {message}")


def print_info(message: str) -> None:
    """Print an informational message with a bullet."""
    console.print(f"[info]•[/info] {message}")


def create_summary_table(title: str, columns: list[str], rows: list[list[str]]) -> Table:
    """Create a standard, minimal table for summary output."""
    table = Table(
        title=title,
        show_header=True,
        header_style="header",
        show_edge=False,
        show_lines=False,
        pad_edge=False,
    )
    for col in columns:
        table.add_column(col, justify="left")

    for row in rows:
        table.add_row(*row)

    return table


def format_search_result(result: SearchResult) -> Panel:
    """Format a single search result into a compact panel."""
    score_percentage = int(result.score * 100)

    content = (
        f"[header]{score_percentage}%[/header]\n\n"
        f"[secondary]Source[/secondary]\n"
        f"[filepath]{result.document_id}[/filepath]\n\n"
    )

    # We don't have heading_path extracted fully in DocumentChunk currently,
    # but we can simulate or show metadata if available. For now we skip or
    # check metadata.
    heading = result.metadata.get("heading")
    if heading:
        content += f"[secondary]Heading[/secondary]\n{heading}\n\n"

    # Show preview snippet
    snippet = result.content[:150].strip()
    if len(result.content) > 150:
        snippet += "..."

    content += f"[secondary]Preview[/secondary]\n{snippet}"

    return Panel(content, border_style="secondary", padding=(1, 2))
