"""Tests for the RelevanceScorer service."""

import pytest

from lke.domain.models.document import ContentType, DocumentChunk
from lke.domain.models.embedding import EmbeddedChunk, EmbeddingVector
from lke.domain.models.search import VectorSearchHit
from lke.domain.services.relevance import RelevanceScorer


@pytest.fixture
def dummy_chunk() -> EmbeddedChunk:
    """Provide a dummy EmbeddedChunk for testing."""
    chunk = DocumentChunk(
        chunk_id="doc1_0",
        document_id="doc1",
        content="Hello world",
        chunk_index=0,
        content_type=ContentType.PROSE,
    )
    return EmbeddedChunk(chunk=chunk, embedding=EmbeddingVector(vector=[0.1, 0.2, 0.3]))


def test_relevance_scorer_initialization() -> None:
    """Test RelevanceScorer initialization."""
    scorer = RelevanceScorer(min_similarity=0.5)
    assert scorer.min_similarity == 0.5


def test_score_normalization_and_sorting(dummy_chunk: EmbeddedChunk) -> None:
    """Test scoring sorts by similarity and clamps to bounds."""
    scorer = RelevanceScorer()

    hits = [
        VectorSearchHit(chunk=dummy_chunk, similarity=1.5),  # Clamped to 1.0
        VectorSearchHit(chunk=dummy_chunk, similarity=0.8),
        VectorSearchHit(chunk=dummy_chunk, similarity=0.2),
    ]

    results = scorer.score(hits)

    # Results should be sorted by relevance descending
    assert len(results) == 3
    assert results[0].score == 1.0  # From 1.5 clamped
    assert results[1].score == 0.8
    assert results[2].score == 0.2


def test_score_min_similarity_filtering(dummy_chunk: EmbeddedChunk) -> None:
    """Test scoring filters out results below the minimum similarity."""
    scorer = RelevanceScorer(min_similarity=0.75)

    hits = [
        VectorSearchHit(chunk=dummy_chunk, similarity=0.9),
        VectorSearchHit(chunk=dummy_chunk, similarity=0.75),
        VectorSearchHit(chunk=dummy_chunk, similarity=0.74),
        VectorSearchHit(chunk=dummy_chunk, similarity=0.5),
    ]

    results = scorer.score(hits)

    assert len(results) == 2
    assert results[0].score == 0.9
    assert results[1].score == 0.75


def test_score_empty_hits() -> None:
    """Test scoring with an empty list of hits."""
    scorer = RelevanceScorer()
    results = scorer.score([])
    assert len(results) == 0
