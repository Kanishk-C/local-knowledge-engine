"""Markdown parsing implementation."""

import re
from pathlib import Path

import yaml
from loguru import logger

from lke.domain.models.document import ParsedContent
from lke.domain.models.source import DataSource
from lke.domain.protocols.parser import Parser


class MarkdownParser(Parser):
    """Parser for standard Markdown documents.

    Extracts YAML frontmatter, markdown links, and tags.
    Preserves the raw text without the frontmatter.
    """

    # Matches YAML frontmatter block at the start of the file
    _FRONTMATTER_PATTERN = re.compile(r"^---\n(.*?)\n---", re.MULTILINE | re.DOTALL)

    # Matches standard markdown links and images: [Text](url) or ![Alt](url)
    _MD_LINK_PATTERN = re.compile(r"!?(?:\[[^\]]*\])\(([^)]+)\)")

    # Matches tags like #tag, #project/lke
    _TAG_PATTERN = re.compile(r"(?:^|\s)#([a-zA-Z0-9_\/-]+)")

    def parse(self, source: DataSource) -> ParsedContent:
        """Parse a markdown data source and extract structured content."""
        path = Path(source.uri)
        try:
            content = path.read_text(encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to read file {source.uri}: {e}")
            raise

        frontmatter = {}
        raw_text = content

        fm_match = self._FRONTMATTER_PATTERN.match(content)
        if fm_match:
            yaml_content = fm_match.group(1)
            try:
                parsed_yaml = yaml.safe_load(yaml_content)
                if isinstance(parsed_yaml, dict):
                    frontmatter = parsed_yaml
                else:
                    logger.warning(f"Frontmatter in {source.uri} is not a dictionary.")
            except yaml.YAMLError as e:
                logger.warning(f"Failed to parse frontmatter in {source.uri}: {e}")

            # Remove frontmatter from raw_text
            raw_text = content[fm_match.end() :].lstrip("\n")

        # Extract links
        links = [match.group(1) for match in self._MD_LINK_PATTERN.finditer(raw_text)]

        # Extract tags
        tags = [match.group(1) for match in self._TAG_PATTERN.finditer(raw_text)]

        # Extract tags from frontmatter if present
        if "tags" in frontmatter and isinstance(frontmatter["tags"], list):
            tags.extend(str(t) for t in frontmatter["tags"])
        elif "tag" in frontmatter and isinstance(frontmatter["tag"], list):
            tags.extend(str(t) for t in frontmatter["tag"])

        # Deduplicate
        links = sorted(list(set(links)))
        tags = sorted(list(set(tags)))

        return ParsedContent(
            document_id=source.uri,
            raw_text=raw_text,
            frontmatter=frontmatter,
            links=links,
            tags=tags,
        )
