import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from lke.api.app import create_app
from lke.domain.models.search import SearchResult
from lke.domain.exceptions import DomainError

@pytest.fixture
def mock_container():
    with patch("lke.api.routers.search.container") as mock_container:
        yield mock_container

@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def test_search_endpoint_success(client, mock_container):
    mock_search_service = MagicMock()
    
    def mock_resolve(interface):
        from lke.application.services.search_service import SearchService
        if interface == SearchService:
            return mock_search_service
        return MagicMock()
        
    mock_container.resolve.side_effect = mock_resolve
    
    mock_result = SearchResult(
        chunk_id="chunk-1",
        document_id="test.md",
        content="Test content",
        score=0.9,
        metadata={"source": "test.md"}
    )
    mock_search_service.search.return_value = [mock_result]
    
    response = client.post("/api/search", json={"query": "test"})
    assert response.status_code == 200
    
    data = response.json()
    assert "results" in data
    assert len(data["results"]) == 1
    assert data["results"][0]["document_id"] == "test.md"


def test_search_endpoint_domain_error(client, mock_container):
    mock_search_service = MagicMock()
    
    def mock_resolve(interface):
        from lke.application.services.search_service import SearchService
        if interface == SearchService:
            return mock_search_service
        return MagicMock()
        
    mock_container.resolve.side_effect = mock_resolve
    
    mock_search_service.search.side_effect = DomainError("Search query cannot be empty")
    
    response = client.post("/api/search", json={"query": "   "})
    assert response.status_code == 400
    assert "Search query cannot be empty" in response.json()["details"]
