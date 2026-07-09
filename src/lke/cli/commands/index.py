"""Index command for parsing and embedding documents."""

from pathlib import Path

import typer
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    TextColumn,
    TimeElapsedColumn,
)

from lke.application.services.indexing_pipeline import IndexingPipeline
from lke.cli.console import console
from lke.cli.container import container
from lke.cli.formatting import create_summary_table, print_error
from lke.domain.events.base import DomainEvent
from lke.domain.events.indexing import (
    DocumentParsed,
    IndexStarted,
)

app = typer.Typer(name="index", help="Parse and embed documents into the vault.")


@app.callback(invoke_without_command=True)
def index_command(
    path: str = typer.Argument(".", help="Directory or file to parse and index."),
    force: bool = typer.Option(False, "--force", help="Force complete reindexing."),
    verbose: bool = typer.Option(False, "--verbose", help="Display detailed per-file progress."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Execute without writing to database."),
) -> None:
    """Parse and embed documents in the target path."""
    pipeline = container.resolve(IndexingPipeline)

    target_path = Path(path)
    if not target_path.exists():
        print_error(f"Path does not exist: {path}")
        raise typer.Exit(code=1)

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        MofNCompleteColumn(),
        TextColumn("documents"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task_id = progress.add_task("Indexing Vault", total=1)

        def event_callback(event: DomainEvent) -> None:
            if isinstance(event, IndexStarted):
                progress.update(task_id, total=event.total_files)
            elif isinstance(event, DocumentParsed):
                progress.advance(task_id)
                if verbose:
                    console.print(f"[secondary]Parsed {event.file_path}[/secondary]")

        try:
            if target_path.is_file():
                progress.update(task_id, total=1)
                single_result = pipeline.index_document(target_path, event_callback=event_callback)
                # Ensure progress bar completes
                if not progress.tasks[task_id].completed:
                    progress.advance(task_id)
                # Convert to BatchIndexingResult for uniform handling
                from lke.domain.models.indexing import BatchIndexingResult

                result = BatchIndexingResult()
                result.add_result(single_result)
            else:
                result = pipeline.index_vault(target_path, event_callback=event_callback)
        except Exception as e:
            print_error("Indexing Failed")
            console.print(f"[secondary]{str(e)}[/secondary]")
            raise typer.Exit(code=5) from e

    console.print()

    rows = [
        ["Documents Indexed", str(result.successful_documents + result.failed_documents)],
        ["Chunks Generated", str(result.total_chunks)],
        ["Embeddings Created", str(result.total_chunks)],  # Assuming 1:1 currently
        ["Duration", f"{result.total_duration.total_seconds():.1f} s"],
        ["Failures", str(result.failed_documents)],
    ]

    summary_table = create_summary_table("Index Complete", ["Metric", "Value"], rows)
    console.print(summary_table)
