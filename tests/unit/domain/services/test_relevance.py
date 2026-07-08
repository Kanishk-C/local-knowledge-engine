"""Tests for the RelevanceScorer service."""

import pytest

from lke.domain.models.document import ContentType, DocumentChunk
from lke.domain.models.search import VectorSearchHit
from lke.domain.services.relevance import RelevanceScorer


@pytest.fixture
def dummy_chunk() -> DocumentChunk:
    """Provide a dummy DocumentChunk for testing."""
    return DocumentChunk(
        chunk_id="doc1_0",
        document_id="doc1",
        content="Hello world",
        chunk_index=0,
        content_type=ContentType.PROSE,
    )


def test_relevance_scorer_initialization() -> None:
    """Test RelevanceScorer initialization."""
    scorer = RelevanceScorer(metric="L2")
    assert scorer.metric == "l2"


def test_score_cosine_metric(dummy_chunk: DocumentChunk) -> None:
    """Test scoring with cosine distance."""
    scorer = RelevanceScorer(metric="cosine")

    hits = [
        VectorSearchHit(chunk=dummy_chunk, distance=0.0),  # Exact match
        VectorSearchHit(chunk=dummy_chunk, distance=1.0),  # Orthogonal
        VectorSearchHit(chunk=dummy_chunk, distance=2.0),  # Opposite
        VectorSearchHit(chunk=dummy_chunk, distance=3.0),  # Should be clamped to 0.0 score
    ]

    results = scorer.score(hits)

    # Results should be sorted by relevance descending
    assert len(results) == 4
    assert results[0].relevance_score == 1.0  # From distance 0.0
    assert results[1].relevance_score == 0.5  # From distance 1.0
    assert results[2].relevance_score == 0.0  # From distance 2.0
    assert results[3].relevance_score == 0.0  # From distance 3.0 clamped


def test_score_l2_metric(dummy_chunk: DocumentChunk) -> None:
    """Test scoring with L2 (or generic) distance."""
    scorer = RelevanceScorer(metric="l2")

    hits = [
        VectorSearchHit(chunk=dummy_chunk, distance=0.0),
        VectorSearchHit(chunk=dummy_chunk, distance=1.0),
        VectorSearchHit(chunk=dummy_chunk, distance=4.0),
    ]

    results = scorer.score(hits)

    # Results should be sorted by relevance descending
    assert len(results) == 3

    # distance 0.0 -> score 1.0
    assert results[0].relevance_score == 1.0
    # distance 1.0 -> score 0.5
    assert results[1].relevance_score == 0.5
    # distance 4.0 -> score 0.2
    assert results[2].relevance_score == 0.2


def test_score_empty_hits() -> None:
    """Test scoring with an empty list of hits."""
    scorer = RelevanceScorer()
    results = scorer.score([])
    assert len(results) == 0


def test_normalize_distance_negative() -> None:
    """Test distance normalization with negative values."""
    scorer = RelevanceScorer()
    # While VectorSearchHit forbids negative distances,
    # the internal _normalize_distance method clamps them to 0.0
    # We can test it directly or by mocking if we didn't want to test private methods.
    assert scorer._normalize_distance(-1.0) == 1.0
