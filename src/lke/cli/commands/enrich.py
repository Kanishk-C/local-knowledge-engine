"""Command for enriching documents with AI metadata."""

import time
from pathlib import Path

import typer
from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table

from lke.application.services.enrichment_pipeline import EnrichmentPipeline
from lke.cli.container import container
from lke.domain.events.base import DomainEvent
from lke.domain.events.enrichment import (
    EnrichmentCompleted,
    EnrichmentFailed,
    EnrichmentSkipped,
    EnrichmentStarted,
)

app = typer.Typer(name="enrich", help="Enrich documents with AI metadata (tags, folders, summary).")
console = Console()


def _handle_event(event: DomainEvent, progress: Progress, task_id: int, verbose: bool) -> None:
    """Handle domain events to update progress."""
    if isinstance(event, EnrichmentStarted):
        progress.update(task_id, total=event.total_files)

    elif isinstance(event, EnrichmentCompleted):
        progress.advance(task_id)
        if verbose:
            console.print(f"[green]✓[/green] Enriched {Path(event.file_path).name} (+{event.tags} tags)")

    elif isinstance(event, EnrichmentSkipped):
        progress.advance(task_id)
        if verbose:
            console.print(f"[dim]⏭[/dim] Skipped {Path(event.file_path).name} ({event.reason})")

    elif isinstance(event, EnrichmentFailed):
        progress.advance(task_id)
        if verbose:
            console.print(f"[red]✗[/red] Failed {Path(event.file_path).name}: {event.error}")


@app.callback(invoke_without_command=True)
def enrich(
    path: Path = typer.Argument(
        default=Path("."),
        exists=True,
        file_okay=False,
        dir_okay=True,
        help="Path to the vault directory.",
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show detailed progress for each file."
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Simulate enrichment without modifying files."
    ),
) -> None:
    """Enrich documents in PATH with AI metadata (tags, folders, summary)."""
    
    if dry_run:
        console.print("[yellow]Dry-run not fully implemented. Proceeding normally...[/yellow]")
        
    pipeline = container.resolve(EnrichmentPipeline)
    start_time = time.perf_counter()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task_id = progress.add_task("[cyan]Enriching vault...", total=None)

        def event_handler(event: DomainEvent) -> None:
            _handle_event(event, progress, task_id, verbose)

        result = pipeline.enrich_vault(path, event_handler)

    duration = time.perf_counter() - start_time

    # Print summary
    table = Table(title="Enrichment Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Total Files", str(result.total))
    table.add_row("Successfully Enriched", str(result.successful))
    table.add_row("Skipped", str(result.skipped))
    
    if result.failed > 0:
        table.add_row("Failed", f"[red]{result.failed}[/red]")
        
    table.add_row("Time Elapsed", f"{duration:.2f}s")

    console.print("\n")
    console.print(table)
