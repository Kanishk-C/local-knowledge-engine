"""Typer CLI application entry point."""

import typer
from loguru import logger

from lke.infrastructure.logging.setup import setup_logging

app = typer.Typer(
    name="lke",
    help="Local Knowledge Engine - AI-powered semantic search for your local documents.",
    no_args_is_help=True,
)


@app.callback()
def main(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logging."),
    json_logs: bool = typer.Option(False, "--json-logs", help="Enable structured JSON logging."),
) -> None:
    """Local Knowledge Engine CLI."""
    level = "DEBUG" if verbose else "INFO"
    is_dev = not json_logs
    setup_logging(level=level, is_dev=is_dev)
    logger.debug("LKE CLI initialized.")


@app.command()
def init(
    path: str = typer.Argument(..., help="Path to initialize the knowledge vault."),
) -> None:
    """Initialize a new local knowledge engine vault in a directory."""
    logger.info(f"Initializing vault at {path}...")
    # TODO: Implement infrastructure wiring and initialization
    typer.echo(f"Initialized LKE vault at {path}")


@app.command()
def index(
    path: str = typer.Argument(".", help="Directory or file to parse and index."),
) -> None:
    """Parse and embed documents in the target path."""
    logger.info(f"Indexing path: {path}...")
    # TODO: Implement index workflow
    typer.echo(f"Finished indexing {path}")


@app.command()
def search(
    query: str = typer.Argument(..., help="The search query."),
    limit: int = typer.Option(5, "--limit", "-n", help="Number of results to return."),
) -> None:
    """Perform a semantic search across the knowledge vault."""
    logger.info(f"Searching for '{query}' (limit: {limit})...")
    # TODO: Implement search workflow
    typer.echo(f"Results for '{query}':")
    typer.echo("1. TODO")


if __name__ == "__main__":
    app()
