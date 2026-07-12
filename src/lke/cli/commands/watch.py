"""Watch command for continuous monitoring and auto-enrichment."""

from pathlib import Path
import signal
import sys
import time
import typer

from lke.application.services.watcher_service import WatcherService
from lke.application.services.indexing_pipeline import IndexingPipeline
from lke.application.services.enrichment_pipeline import EnrichmentPipeline
from lke.cli.console import console
from lke.cli.container import container
from lke.cli.formatting import print_error

app = typer.Typer(name="watch", help="Watch a vault for changes and process them automatically.")

@app.callback(invoke_without_command=True)
def watch_command(
    path: str = typer.Argument(".", help="Directory to watch for changes."),
    verbose: bool = typer.Option(False, "--verbose", help="Display detailed per-file progress."),
) -> None:
    """Watch a vault for changes and process them automatically."""
    target_path = Path(path).resolve()
    
    if not target_path.exists() or not target_path.is_dir():
        print_error(f"Path does not exist or is not a directory: {path}")
        raise typer.Exit(code=1)
        
    indexing = container.resolve(IndexingPipeline)
    enrichment = container.resolve(EnrichmentPipeline)
    
    watcher = WatcherService(
        vault_path=target_path,
        indexing_pipeline=indexing,
        enrichment_pipeline=enrichment,
    )
    
    console.print(f"[bold green]Starting watch mode on:[/bold green] [cyan]{target_path}[/cyan]")
    console.print("Press Ctrl+C to stop.")
    
    def handle_sigterm(signum, frame):
        console.print("\n[yellow]Stopping watch mode (SIGTERM)...[/yellow]")
        watcher.stop()
        console.print("[green]Watch mode stopped.[/green]")
        sys.exit(0)
        
    signal.signal(signal.SIGTERM, handle_sigterm)
    
    watcher.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopping watch mode...[/yellow]")
        watcher.stop()
        console.print("[green]Watch mode stopped.[/green]")
