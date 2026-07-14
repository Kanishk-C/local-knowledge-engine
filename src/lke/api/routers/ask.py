"""Ask API endpoint for RAG generation."""

from fastapi import APIRouter, Depends
from fastapi.concurrency import run_in_threadpool

from lke.api.models import AskRequest, AskResponse
from lke.application.services.rag_service import RAGService
from lke.cli.container import container


router = APIRouter()


def get_rag_service() -> RAGService:
    """Dependency to get the RAGService instance."""
    return container.resolve(RAGService)


@router.post("/ask", response_model=AskResponse)
async def ask(
    request: AskRequest,
    rag_service: RAGService = Depends(get_rag_service),
) -> AskResponse:
    """Generate an answer to a question using Retrieval-Augmented Generation."""
    # Run synchronous domain service in a threadpool to avoid blocking event loop
    rag_response = await run_in_threadpool(
        rag_service.ask,
        query=request.query,
    )
    
    return AskResponse(
        answer=rag_response.answer,
        sources=rag_response.sources,
    )
