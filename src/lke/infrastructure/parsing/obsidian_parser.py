"""Obsidian-specific parsing implementation."""

import re
from dataclasses import replace

from lke.domain.models.document import ParsedContent
from lke.domain.models.source import DataSource
from lke.infrastructure.parsing.markdown_parser import MarkdownParser


class ObsidianParser(MarkdownParser):
    """Parser for Obsidian Markdown documents.

    Inherits standard Markdown parsing and adds support for:
    - Wikilinks ([[Link]] or [[Link|Alias]])
    - Embedded notes/images (![[Image.png]])
    """

    # Matches [[Link]] or [[Link|Alias]] or ![[Image.png]]
    _WIKILINK_PATTERN = re.compile(r"!?\[\[([^|\]]+)(?:\|[^\]]+)?\]\]")

    def parse(self, source: DataSource) -> ParsedContent:
        """Parse an Obsidian data source and extract structured content."""
        # Call base MarkdownParser to handle frontmatter and standard markdown
        parsed = super().parse(source)

        # Extract wikilinks from the raw text
        wiki_links = [
            match.group(1).strip() for match in self._WIKILINK_PATTERN.finditer(parsed.raw_text)
        ]

        # Combine with standard markdown links and deduplicate
        all_links = sorted(list(set(parsed.links + wiki_links)))

        # Return a new ParsedContent instance with the updated links
        return replace(parsed, links=all_links)
