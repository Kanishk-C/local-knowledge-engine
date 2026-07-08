"""Tests for the Typer CLI app."""

from typer.testing import CliRunner

from lke.cli.app import app

runner = CliRunner()


def test_cli_help() -> None:
    """Test that the CLI help command executes."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Local Knowledge Engine" in result.stdout


def test_cli_init() -> None:
    """Test the init command scaffold."""
    result = runner.invoke(app, ["init", "/tmp/vault"])
    assert result.exit_code == 0
    assert "Initialized LKE vault at /tmp/vault" in result.stdout


def test_cli_index() -> None:
    """Test the index command scaffold."""
    result = runner.invoke(app, ["index", "."])
    assert result.exit_code == 0
    assert "Finished indexing ." in result.stdout


def test_cli_search() -> None:
    """Test the search command scaffold."""
    result = runner.invoke(app, ["search", "test query"])
    assert result.exit_code == 0
    assert "Results for 'test query'" in result.stdout
