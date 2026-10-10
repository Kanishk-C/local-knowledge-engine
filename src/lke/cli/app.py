"""Typer CLI application entry point."""

import typer
from loguru import logger

from lke.cli.commands import ask, enrich, eval, index, init, journal, search, serve, watch
from lke.cli.container import MissingExtraError
from lke.cli.formatting import print_error
from lke.infrastructure.logging.setup import setup_logging

app = typer.Typer(
    name="lke",
    help=(
        "Local Knowledge Engine - a local-first journal and knowledge base for Markdown"
        " vaults.\n\n"
        "Journal commands work offline with no extra dependencies. "
        "AI commands need the optional 'ai' extra and a running Ollama."
    ),
    no_args_is_help=True,
)

journal.register(app)

for module in (init, index, search, ask, enrich, watch, eval, serve):
    app.add_typer(module.app, rich_help_panel="AI (optional extra: ai)")


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


def run() -> None:
    """Console-script entry point with a friendly message for missing extras."""
    try:
        app()
    except MissingExtraError as e:
        print_error(str(e))
        raise SystemExit(5) from None


if __name__ == "__main__":
    run()
