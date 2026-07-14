"""Pydantic schemas for the REST API."""

from typing import List, Optional

from pydantic import BaseModel, Field

from lke.domain.models.search import SearchResult


class SearchRequest(BaseModel):
    """Request schema for /api/search"""
    query: str = Field(..., description="The query to search for.")
    limit: Optional[int] = Field(None, description="Maximum number of results to return.")
    threshold: Optional[float] = Field(None, description="Minimum similarity threshold.")


class SearchResponse(BaseModel):
    """Response schema for /api/search"""
    results: List[SearchResult]


class AskRequest(BaseModel):
    """Request schema for /api/ask"""
    query: str = Field(..., description="The user's question to answer.")


class AskResponse(BaseModel):
    """Response schema for /api/ask"""
    answer: str
    sources: List[SearchResult]
