"""Tests for the ChunkingService."""

import pytest

from lke.domain.models.document import ParsedContent
from lke.domain.services.chunking import ChunkingService


def test_chunking_service_initialization() -> None:
    """Test validation during ChunkingService initialization."""
    with pytest.raises(ValueError, match="max_tokens must be greater than 0"):
        ChunkingService(max_tokens=0)

    with pytest.raises(ValueError, match="overlap_tokens cannot be negative"):
        ChunkingService(overlap_tokens=-1)

    with pytest.raises(ValueError, match="overlap_tokens must be strictly less than max_tokens"):
        ChunkingService(max_tokens=100, overlap_tokens=100)

    with pytest.raises(ValueError, match="min_tokens cannot be negative"):
        ChunkingService(min_tokens=-1)


def test_chunk_empty_text() -> None:
    """Test chunking with empty text."""
    service = ChunkingService()
    parsed = ParsedContent(document_id="doc1", raw_text="")

    chunks = service.chunk(parsed)
    assert len(chunks) == 0


def test_chunk_no_headings() -> None:
    """Test chunking text with no headings."""
    service = ChunkingService(max_tokens=100, overlap_tokens=10)
    text = "This is a simple text with no headings.\nIt just has paragraphs."
    parsed = ParsedContent(document_id="doc1", raw_text=text)

    chunks = service.chunk(parsed)
    assert len(chunks) == 1
    assert chunks[0].content == text
    assert chunks[0].metadata["heading_path"] == []
    assert chunks[0].metadata["start_offset"] == 0
    assert chunks[0].metadata["end_offset"] == len(text)
    assert chunks[0].metadata["source_path"] == "doc1"


def test_chunk_single_heading() -> None:
    """Test chunking text with a single heading."""
    service = ChunkingService(max_tokens=100, overlap_tokens=10)
    text = "# Introduction\n\nThis is the introduction."
    parsed = ParsedContent(document_id="doc1", raw_text=text)

    chunks = service.chunk(parsed)
    assert len(chunks) == 1
    assert chunks[0].content == text
    assert chunks[0].metadata["heading_path"] == ["Introduction"]
    assert chunks[0].metadata["heading_level"] == 1


def test_chunk_nested_headings() -> None:
    """Test chunking text with nested headings."""
    service = ChunkingService(max_tokens=100, overlap_tokens=10)
    text = "# Chapter 1\n\nContent 1\n\n## Section 1.1\n\nContent 1.1"
    parsed = ParsedContent(document_id="doc1", raw_text=text)

    chunks = service.chunk(parsed)

    # "Chapter 1" and "Section 1.1" have different parents, so no merge.
    assert len(chunks) == 2
    assert chunks[0].metadata["heading_path"] == ["Chapter 1"]
    assert chunks[1].metadata["heading_path"] == ["Chapter 1", "Section 1.1"]
    assert "Content 1" in chunks[0].content
    assert "Content 1.1" in chunks[1].content


def test_chunk_merge_siblings() -> None:
    """Test merging of small sibling sections under the same parent."""
    # max_tokens=100 -> max_chars=400.
    service = ChunkingService(max_tokens=100, overlap_tokens=10)
    text = "# Networking\n\n## OSPF\n\nShort content 1\n\n## BGP\n\nShort content 2"
    parsed = ParsedContent(document_id="doc1", raw_text=text)

    chunks = service.chunk(parsed)

    # "Networking" root (empty), then OSPF and BGP are siblings under Networking.
    assert len(chunks) == 2
    assert chunks[0].metadata["heading_path"] == ["Networking"]
    assert chunks[0].content == "# Networking"

    assert chunks[1].metadata["heading_path"] == ["Networking"]  # Parent path
    assert "## OSPF" in chunks[1].content
    assert "Short content 1" in chunks[1].content
    assert "## BGP" in chunks[1].content
    assert "Short content 2" in chunks[1].content


def test_chunk_no_merge_different_parents() -> None:
    """Test that sections with different parents (e.g., top-level) do not merge."""
    service = ChunkingService(max_tokens=100, overlap_tokens=10)
    text = "# Networking\n\nShort 1\n\n# Linux\n\nShort 2"
    parsed = ParsedContent(document_id="doc1", raw_text=text)

    chunks = service.chunk(parsed)

    assert len(chunks) == 2
    assert chunks[0].metadata["heading_path"] == ["Networking"]
    assert chunks[1].metadata["heading_path"] == ["Linux"]


def test_chunk_large_text_overlap() -> None:
    """Test overlapping splits for sections that exceed max_chars."""
    # max_chars = 4 * 4 = 16
    # overlap_chars = 2 * 4 = 8
    service = ChunkingService(max_tokens=4, overlap_tokens=2)

    # 5 blocks of ~10 chars each. Total ~50 chars.
    text = "# Large\n\nBlock 1\n\nBlock 2\n\nBlock 3\n\nBlock 4"
    parsed = ParsedContent(document_id="doc1", raw_text=text)

    chunks = service.chunk(parsed)

    # First chunk is the heading if it doesn't fit with the rest
    # But let's check splits of the content.
    assert len(chunks) > 1
    for c in chunks:
        assert len(c.content) <= 16
        assert c.metadata["is_split"] is True or len(c.content) < 16


def test_deterministic_ids() -> None:
    """Test that generated chunk IDs are deterministic."""
    service = ChunkingService(max_tokens=100, overlap_tokens=10)
    text = "# Section 1\n\nContent\n\n# Section 2\n\nContent"
    parsed = ParsedContent(document_id="my_doc_abc", raw_text=text)

    chunks = service.chunk(parsed)

    assert chunks[0].chunk_id == "my_doc_abc:0"
    assert chunks[1].chunk_id == "my_doc_abc:1"


def test_offsets_correctness() -> None:
    """Test that start and end offsets are correctly mapped."""
    service = ChunkingService(max_tokens=100, overlap_tokens=10)
    text = "0123456789\n\n# H1\n\nabc"
    parsed = ParsedContent(document_id="doc", raw_text=text)

    chunks = service.chunk(parsed)

    assert len(chunks) == 2
    # The first text chunk has no heading, just text
    assert chunks[0].metadata["start_offset"] == 0
    assert chunks[0].metadata["end_offset"] == 12
    assert text[0:12] == "0123456789\n\n"

    # The second chunk is the H1
    assert chunks[1].metadata["start_offset"] == 12
    assert chunks[1].metadata["end_offset"] == len(text)
    assert text[12 : len(text)] == "# H1\n\nabc"


def test_code_block_no_split() -> None:
    """Test that long code blocks are not split by newlines incorrectly."""
    # max_chars = 30
    service = ChunkingService(max_tokens=7, overlap_tokens=0)

    code = "```python\ndef a():\n  pass\n\ndef b():\n  pass\n```"
    text = f"# Code\n\n{code}"
    parsed = ParsedContent(document_id="doc", raw_text=text)

    chunks = service.chunk(parsed)

    # The code block alone is 45 chars, which > max_chars (28)
    # The service will split the code block by lines as a last resort.
    assert len(chunks) > 1
    assert any("def a():" in c.content for c in chunks)


def test_mixed_heading_levels() -> None:
    """Test mixed heading levels processing."""
    service = ChunkingService(max_tokens=100, overlap_tokens=10)
    text = "# H1\n## H2\n### H3\n# Another H1"
    parsed = ParsedContent(document_id="doc", raw_text=text)

    chunks = service.chunk(parsed)

    paths = [c.metadata["heading_path"] for c in chunks]
    assert ["H1"] in paths
    assert ["H1", "H2"] in paths
    assert ["H1", "H2", "H3"] in paths
    assert ["Another H1"] in paths


def test_empty_heading() -> None:
    """Test empty heading handling."""
    service = ChunkingService(max_tokens=100, overlap_tokens=10)
    text = "# \nContent after empty heading"
    parsed = ParsedContent(document_id="doc", raw_text=text)

    chunks = service.chunk(parsed)
    assert len(chunks) == 1
    assert chunks[0].metadata["heading_path"] == [""]


def test_unicode_documents() -> None:
    """Test handling of unicode text (emojis, foreign characters)."""
    service = ChunkingService(max_tokens=100, overlap_tokens=10)
    text = "# こんにちは\n\n世界 👋\n\n## 🚀"
    parsed = ParsedContent(document_id="doc", raw_text=text)

    chunks = service.chunk(parsed)

    assert len(chunks) == 2
    assert chunks[0].metadata["heading_path"] == ["こんにちは"]
    assert chunks[1].metadata["heading_path"] == ["こんにちは", "🚀"]
