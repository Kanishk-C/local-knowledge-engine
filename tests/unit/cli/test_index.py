"""Tests for the index CLI command."""

from datetime import timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from lke.application.services.indexing_pipeline import IndexingPipeline
from lke.cli.app import app
from lke.domain.models.indexing import IndexingResult

runner = CliRunner()


@patch("lke.cli.commands.index.container.resolve")
@patch("pathlib.Path.exists", return_value=True)
@patch("pathlib.Path.is_file", return_value=True)
def test_index_command_file(
    mock_is_file: MagicMock, mock_exists: MagicMock, mock_resolve: MagicMock
) -> None:
    """Test index command on a single file."""
    mock_pipeline = MagicMock(spec=IndexingPipeline)

    mock_result = IndexingResult(
        file_path=Path("test.md"),
        document_id="test.md",
        chunks_created=5,
        embedded_chunks=5,
        duration=timedelta(seconds=1),
        success=True,
    )
    mock_pipeline.index_document.return_value = mock_result

    mock_resolve.return_value = mock_pipeline

    result = runner.invoke(app, ["index", "test.md"])
    assert result.exit_code == 0
    assert "Documents Indexed" in result.stdout
    assert "Chunks Generated" in result.stdout
