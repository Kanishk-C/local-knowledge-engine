"""Tests for the search CLI command."""

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from lke.application.services.search_service import SearchService
from lke.cli.app import app
from lke.domain.models.search import SearchResult

runner = CliRunner()


@patch("lke.cli.commands.search.container.resolve")
def test_search_command_success(mock_resolve: MagicMock) -> None:
    """Test search command."""
    mock_service = MagicMock(spec=SearchService)

    mock_result = SearchResult(
        chunk_id="test-1",
        document_id="doc-1",
        content="Test content",
        score=0.9,
        metadata={"source_path": "test.md"},
    )
    mock_service.search.return_value = [mock_result]

    mock_resolve.return_value = mock_service

    result = runner.invoke(app, ["search", "test query"])
    assert result.exit_code == 0
    assert "Test content" in result.stdout
