"""Tests for the Obsidian parser."""

from pathlib import Path

from lke.domain.models.source import DataSource, SourceType
from lke.infrastructure.parsing.obsidian_parser import ObsidianParser


def test_obsidian_parser_wikilinks(tmp_path: Path) -> None:
    """Test extraction of wikilinks."""
    content = """
This is a standard [[Wikilink]].
This is an aliased [[Wikilink|Alias]].
This is an embedded note ![[Embedded Note]].
This is an embedded image ![[image.png]].
And a normal [Markdown Link](https://example.com).
"""
    file_path = tmp_path / "test.md"
    file_path.write_text(content, encoding="utf-8")

    source = DataSource(uri=str(file_path), source_type=SourceType.OBSIDIAN)
    parser = ObsidianParser()
    parsed = parser.parse(source)

    expected_links = {"Wikilink", "Embedded Note", "image.png", "https://example.com"}
    assert set(parsed.links) == expected_links


def test_obsidian_parser_with_frontmatter(tmp_path: Path) -> None:
    """Test Obsidian parser still correctly handles frontmatter."""
    content = """---
title: Obsidian Note
tag: [obsidian, test]
---
# Content
[[Link 1]] and [[Link 2|Alias]]
"""
    file_path = tmp_path / "test.md"
    file_path.write_text(content, encoding="utf-8")

    source = DataSource(uri=str(file_path), source_type=SourceType.OBSIDIAN)
    parser = ObsidianParser()
    parsed = parser.parse(source)

    assert parsed.frontmatter == {"title": "Obsidian Note", "tag": ["obsidian", "test"]}
    assert set(parsed.tags) == {"obsidian", "test"}
    assert set(parsed.links) == {"Link 1", "Link 2"}
