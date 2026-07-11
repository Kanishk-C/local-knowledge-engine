"""Tests for the init CLI command."""

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from lke.cli.app import app
from lke.config.models import ApplicationConfig
from lke.domain.models.embedding import HealthStatus
from lke.domain.protocols.embedding_provider import EmbeddingProvider
from lke.domain.repositories.vector_repository import VectorRepository

runner = CliRunner()


@patch("lke.cli.commands.init.container.resolve")
def test_init_command_success(mock_resolve: MagicMock) -> None:
    """Test init command when all dependencies are healthy."""

    mock_config = MagicMock()
    mock_config.embeddings.embedding_model = "test-model"
    mock_config.paths.vector_db = "test-path"

    mock_provider = MagicMock(spec=EmbeddingProvider)
    mock_provider.health_check.return_value = HealthStatus(
        healthy=True, latency_ms=10, provider="ollama", model="test-model", message="OK"
    )

    mock_repo = MagicMock(spec=VectorRepository)
    class MockRepoHealth:
        def __init__(self):
            self.calls = 0
        def __call__(self):
            self.calls += 1
            if self.calls == 1:
                return HealthStatus(healthy=False, latency_ms=10, provider="lancedb", model="vector", message="Table not found")
            return HealthStatus(healthy=True, latency_ms=10, provider="lancedb", model="vector", message="OK")
    
    mock_repo.health.side_effect = MockRepoHealth()

    def resolve_side_effect(interface: type) -> MagicMock:
        if interface == ApplicationConfig:
            return mock_config
        elif interface == EmbeddingProvider:
            return mock_provider
        elif interface == VectorRepository:
            return mock_repo
        raise KeyError(f"Unexpected interface: {interface}")

    mock_resolve.side_effect = resolve_side_effect

    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0
    assert "Configuration" in result.stdout
    assert "Ollama" in result.stdout
    assert "LanceDB" in result.stdout
    mock_repo.initialize.assert_called_once()
