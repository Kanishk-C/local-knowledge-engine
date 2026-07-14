"""Search API endpoint."""

from fastapi import APIRouter, Depends
from fastapi.concurrency import run_in_threadpool

from lke.api.models import SearchRequest, SearchResponse
from lke.application.services.search_service import SearchService
from lke.cli.container import container


router = APIRouter()


def get_search_service() -> SearchService:
    """Dependency to get the SearchService instance."""
    return container.resolve(SearchService)


@router.post("/search", response_model=SearchResponse)
async def search(
    request: SearchRequest,
    search_service: SearchService = Depends(get_search_service),
) -> SearchResponse:
    """Perform a semantic search over the document knowledge base."""
    # Run synchronous domain service in a threadpool to avoid blocking event loop
    results = await run_in_threadpool(
        search_service.search,
        query=request.query,
        top_k=request.limit,
    )
    
    return SearchResponse(results=results)
