"""Tests for the Markdown parser."""

from pathlib import Path

from lke.domain.models.source import DataSource, SourceType
from lke.infrastructure.parsing.markdown_parser import MarkdownParser


def test_markdown_parser_with_frontmatter(tmp_path: Path) -> None:
    """Test parsing a document with valid YAML frontmatter."""
    content = """---
title: Test Document
tags:
  - testing
  - markdown
---
# Heading
This is a [link](https://example.com) and a #tag in the text.
"""
    file_path = tmp_path / "test.md"
    file_path.write_text(content, encoding="utf-8")

    source = DataSource(uri=str(file_path), source_type=SourceType.MARKDOWN)
    parser = MarkdownParser()
    parsed = parser.parse(source)

    assert parsed.document_id == str(file_path)
    assert parsed.frontmatter == {"title": "Test Document", "tags": ["testing", "markdown"]}
    assert (
        parsed.raw_text.strip()
        == "# Heading\nThis is a [link](https://example.com) and a #tag in the text."
    )
    assert "https://example.com" in parsed.links
    assert set(parsed.tags) == {"testing", "markdown", "tag"}


def test_markdown_parser_malformed_frontmatter(tmp_path: Path) -> None:
    """Test parsing a document with malformed YAML frontmatter."""
    content = """---
title: [unclosed list
tags: testing
---
# Heading
Content here.
"""
    file_path = tmp_path / "test.md"
    file_path.write_text(content, encoding="utf-8")

    source = DataSource(uri=str(file_path), source_type=SourceType.MARKDOWN)
    parser = MarkdownParser()
    parsed = parser.parse(source)

    # Frontmatter should be empty due to failure to parse, but it shouldn't crash
    assert parsed.frontmatter == {}
    assert "# Heading\nContent here." in parsed.raw_text


def test_markdown_parser_no_frontmatter(tmp_path: Path) -> None:
    """Test parsing a document without frontmatter."""
    content = """# Just Content
No frontmatter here.
"""
    file_path = tmp_path / "test.md"
    file_path.write_text(content, encoding="utf-8")

    source = DataSource(uri=str(file_path), source_type=SourceType.MARKDOWN)
    parser = MarkdownParser()
    parsed = parser.parse(source)

    assert parsed.frontmatter == {}
    assert "No frontmatter here." in parsed.raw_text
    assert len(parsed.tags) == 0


def test_markdown_parser_links_and_images(tmp_path: Path) -> None:
    """Test extraction of various markdown links and images."""
    content = """
Here is a [normal link](/some/path).
And an ![image link](/img.png).
"""
    file_path = tmp_path / "test.md"
    file_path.write_text(content, encoding="utf-8")

    source = DataSource(uri=str(file_path), source_type=SourceType.MARKDOWN)
    parser = MarkdownParser()
    parsed = parser.parse(source)

    assert set(parsed.links) == {"/some/path", "/img.png"}
