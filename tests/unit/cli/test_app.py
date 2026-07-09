"""Tests for the Typer CLI app."""

from typer.testing import CliRunner

from lke.cli.app import app

runner = CliRunner()


def test_cli_help() -> None:
    """Test that the CLI help command executes."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Local Knowledge Engine" in result.stdout
