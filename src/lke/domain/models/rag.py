"""Domain models for RAG Pipeline."""

from dataclasses import dataclass
from typing import Sequence

from lke.domain.models.search import SearchResult


@dataclass
class RAGResponse:
    """The response from a RAG generation."""

    answer: str
    sources: Sequence[SearchResult]
