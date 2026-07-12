"""Typer CLI application entry point."""

import typer
from loguru import logger

from lke.cli.commands import index, init, search, enrich, watch, eval
from lke.infrastructure.logging.setup import setup_logging

app = typer.Typer(
    name="lke",
    help="Local Knowledge Engine - AI-powered semantic search for your local documents.",
    no_args_is_help=True,
)

app.add_typer(init.app)
app.add_typer(index.app)
app.add_typer(search.app)
app.add_typer(enrich.app)
app.add_typer(watch.app)
app.add_typer(eval.app)


@app.callback()
def main(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logging."),
    json_logs: bool = typer.Option(False, "--json-logs", help="Enable structured JSON logging."),
) -> None:
    """Local Knowledge Engine CLI."""
    level = "DEBUG" if verbose else "INFO"
    is_dev = not json_logs
    setup_logging(level=level, is_dev=is_dev)

    from lke.cli.container import initialize_container

    initialize_container()

    logger.debug("LKE CLI initialized.")


if __name__ == "__main__":
    app()
