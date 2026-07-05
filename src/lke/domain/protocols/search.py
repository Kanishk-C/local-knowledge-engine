"""Search protocol for the domain."""

from typing import Protocol

from lke.domain.models.search import SearchQuery, SearchResult


class SearchEngine(Protocol):
    """Protocol for executing search queries against the knowledge base."""

    def search(self, query: SearchQuery) -> list[SearchResult]:
        """Execute a search query and return scored results."""
        ...
