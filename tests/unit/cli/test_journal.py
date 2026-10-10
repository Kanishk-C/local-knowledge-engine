"""Tests for the journal CLI commands."""

import subprocess
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from lke.cli.app import app

runner = CliRunner()


@pytest.fixture
def vault(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("LKE_JOURNAL__VAULT_PATH", str(tmp_path))
    monkeypatch.setenv("COLUMNS", "200")
    monkeypatch.setenv("LKE_CONFIG", str(tmp_path / "none.toml"))
    (tmp_path / "people").mkdir()
    (tmp_path / "people" / "Alice.md").write_text("# Alice\n", encoding="utf-8")
    return tmp_path


def test_today_creates_and_prints_path(vault: Path) -> None:
    result = runner.invoke(app, ["today", "2026-10-10"])
    assert result.exit_code == 0, result.output
    assert "Created journal/2026/2026-10-10.md" in result.output
    assert (vault / "journal" / "2026" / "2026-10-10.md").exists()


def test_log_find_who_links_day(vault: Path) -> None:
    assert runner.invoke(app, ["log", "Coffee", "with", "[[Alice]]", "#social"]).exit_code == 0

    result = runner.invoke(app, ["find", "coffee"])
    assert result.exit_code == 0 and "Coffee with [[Alice]]" in result.output

    result = runner.invoke(app, ["find", "--tag", "social"])
    assert result.exit_code == 0 and "journal/" in result.output

    result = runner.invoke(app, ["who", "alice"])
    assert result.exit_code == 0
    assert "people/Alice.md" in result.output and "1 note(s)" in result.output

    result = runner.invoke(app, ["links", "--folder", "people"])
    assert result.exit_code == 0 and "Alice" in result.output

    result = runner.invoke(app, ["day", "today"])
    assert result.exit_code == 0 and "Coffee with" in result.output


def test_empty_results_and_bad_input(vault: Path) -> None:
    assert "No matching notes" in runner.invoke(app, ["find", "zebra"]).output
    assert "Try --unlinked" in runner.invoke(app, ["who", "nobody"]).output
    assert "Nothing written" in runner.invoke(app, ["day", "2001-01-01"]).output
    assert "No earlier entries" in runner.invoke(app, ["onthisday"]).output
    assert runner.invoke(app, ["day", "someday"]).exit_code == 2
    assert runner.invoke(app, ["find"]).exit_code == 2


def test_missing_vault(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LKE_JOURNAL__VAULT_PATH", str(tmp_path / "missing"))
    result = runner.invoke(app, ["find", "x"])
    assert result.exit_code == 1 and "Vault folder not found" in result.output


def test_cli_import_does_not_load_ai_stack() -> None:
    code = (
        "import sys, lke.cli.app;"
        "heavy = {'lancedb', 'ollama', 'torch', 'sentence_transformers', 'fastapi', 'watchdog'};"
        "print(sorted(heavy & set(sys.modules)))"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "[]"
