import pytest
from unittest.mock import Mock

from lke.config.models import RAGConfig
from lke.domain.exceptions import DomainError
from lke.domain.models.search import SearchResult
from lke.domain.models.rag import RAGResponse
from lke.application.services.rag_service import RAGService

@pytest.fixture
def search_service_mock():
    return Mock()

@pytest.fixture
def ai_provider_mock():
    return Mock()

@pytest.fixture
def rag_config():
    return RAGConfig(system_prompt="Test system prompt", top_k=2)

@pytest.fixture
def rag_service(search_service_mock, ai_provider_mock, rag_config):
    return RAGService(search_service_mock, ai_provider_mock, rag_config)


def test_ask_empty_query(rag_service):
    with pytest.raises(DomainError, match="Query cannot be empty or whitespace."):
        rag_service.ask("   ")


def test_ask_success(rag_service, search_service_mock, ai_provider_mock):
    # Setup mocks
    search_service_mock.search.return_value = [
        SearchResult(document_id="doc1", chunk_id="chunk1", content="Content 1", score=0.9, metadata={"title": "Doc 1"}),
        SearchResult(document_id="doc2", chunk_id="chunk2", content="Content 2", score=0.8, metadata={})
    ]
    ai_provider_mock.generate_text.return_value = "This is the generated answer."

    # Call service
    response = rag_service.ask("What is the meaning of life?")

    # Assertions
    assert isinstance(response, RAGResponse)
    assert response.answer == "This is the generated answer."
    assert len(response.sources) == 2
    
    search_service_mock.search.assert_called_once_with("What is the meaning of life?", top_k=2)
    ai_provider_mock.generate_text.assert_called_once()
    
    # Check that context building works
    call_args = ai_provider_mock.generate_text.call_args[1]
    assert "Doc 1" in call_args["prompt"]
    assert "Content 1" in call_args["prompt"]
    assert "doc2" in call_args["prompt"]
    assert "Content 2" in call_args["prompt"]
    assert call_args["system_prompt"] == "Test system prompt"


def test_ask_no_search_results(rag_service, search_service_mock, ai_provider_mock):
    search_service_mock.search.return_value = []
    
    response = rag_service.ask("Unknown query")

    assert response.answer == "I don't know. I couldn't find any relevant information in the provided context."
    assert response.sources == []
    ai_provider_mock.generate_text.assert_not_called()

def test_ask_ai_provider_error(rag_service, search_service_mock, ai_provider_mock):
    # We must return at least one source to trigger the LLM call
    mock_source = Mock()
    mock_source.document_id = "doc_1"
    mock_source.content = "Test content"
    mock_source.metadata = {"title": "Test"}
    search_service_mock.search.return_value = [mock_source]
    
    ai_provider_mock.generate_text.side_effect = Exception("API down")

    with pytest.raises(DomainError, match="Failed to generate answer: API down"):
        rag_service.ask("Tell me about API down")
