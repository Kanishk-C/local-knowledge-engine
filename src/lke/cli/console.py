"""Rich console and formatting utilities for the CLI."""

from rich.console import Console
from rich.theme import Theme

# Define consistent color palette based on specification
_cli_theme = Theme(
    {
        "success": "green",
        "info": "cyan",
        "warning": "yellow",
        "error": "red",
        "header": "bright_white bold",
        "secondary": "dim white",
        "filepath": "blue",
        "command": "magenta",
    }
)

# Single global console instance to be used across the CLI
console = Console(theme=_cli_theme)
