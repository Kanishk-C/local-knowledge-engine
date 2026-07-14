import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from lke.api.app import create_app
from lke.domain.models.search import SearchResult
from lke.domain.models.rag import RAGResponse
from lke.domain.exceptions import InfrastructureError

@pytest.fixture
def mock_container():
    with patch("lke.api.routers.ask.container") as mock_container:
        yield mock_container

@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def test_ask_endpoint_success(client, mock_container):
    mock_rag_service = MagicMock()
    
    def mock_resolve(interface):
        from lke.application.services.rag_service import RAGService
        if interface == RAGService:
            return mock_rag_service
        return MagicMock()
        
    mock_container.resolve.side_effect = mock_resolve
    
    mock_source = SearchResult(
        chunk_id="chunk-1",
        document_id="test.md",
        content="Test content",
        score=0.9,
        metadata={"source": "test.md"}
    )
    mock_rag_service.ask.return_value = RAGResponse(
        answer="Mock answer",
        sources=[mock_source]
    )
    
    response = client.post("/api/ask", json={"query": "test"})
    assert response.status_code == 200
    
    data = response.json()
    assert data["answer"] == "Mock answer"
    assert len(data["sources"]) == 1
    assert data["sources"][0]["document_id"] == "test.md"


def test_ask_endpoint_ai_error(client, mock_container):
    mock_rag_service = MagicMock()
    
    def mock_resolve(interface):
        from lke.application.services.rag_service import RAGService
        if interface == RAGService:
            return mock_rag_service
        return MagicMock()
        
    mock_container.resolve.side_effect = mock_resolve
    
    mock_rag_service.ask.side_effect = InfrastructureError("Ollama down")
    
    response = client.post("/api/ask", json={"query": "test"})
    assert response.status_code == 503
    assert "Service Unavailable" in response.json()["error"]
