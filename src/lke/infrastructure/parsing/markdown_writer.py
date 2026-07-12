"""Markdown frontmatter and content writer."""

import os
import re
import logging
from datetime import datetime
from pathlib import Path

import yaml

from lke.domain.models.document import Document

logger = logging.getLogger(__name__)


class MarkdownFrontmatterWriter:
    """Writes metadata and related links back to a markdown file safely."""

    _FRONTMATTER_PATTERN = re.compile(r"^---\n(.*?)\n---", re.MULTILINE | re.DOTALL)
    _AI_RELATED_PATTERN = re.compile(
        r"\n*<!-- ai-related:start -->.*?<!-- ai-related:end -->\n*", re.DOTALL
    )

    def write_enrichment(
        self,
        file_path: Path,
        content_hash: str,
        tags: list[str],
        summary: str | None,
        related_links: list[str] | None = None,
        new_folder: str | None = None,
    ) -> Path:
        """Write enrichment metadata and related links to the file.

        Args:
            file_path: The path to the markdown file.
            content_hash: The hash of the clean body, stored in `ai_processed`.
            tags: The new or existing tags to place in `ai_tags`.
            summary: The AI-generated summary to place in `ai_summary`.
            related_links: A list of wikilinks for related notes.
            new_folder: If provided, move the file to this folder relative to the workspace.

        Returns:
            The final Path of the file (might be different if moved).
        """
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            raise

        frontmatter = {}
        raw_text = content

        # Parse existing frontmatter
        fm_match = self._FRONTMATTER_PATTERN.match(content)
        if fm_match:
            yaml_content = fm_match.group(1)
            try:
                parsed_yaml = yaml.safe_load(yaml_content)
                if isinstance(parsed_yaml, dict):
                    frontmatter = parsed_yaml
            except yaml.YAMLError:
                pass
            raw_text = content[fm_match.end() :].lstrip("\n")

        # Strip any existing related notes block to ensure we don't duplicate
        raw_text = self._AI_RELATED_PATTERN.sub("", raw_text).strip()

        # Update frontmatter
        frontmatter["ai_tags"] = tags
        if summary is not None:
            frontmatter["ai_summary"] = summary
        else:
            frontmatter.pop("ai_summary", None)
            
        frontmatter["ai_processed"] = content_hash
        frontmatter["ai_processed_at"] = datetime.utcnow().isoformat() + "Z"

        # Reconstruct file content
        new_yaml = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False).strip()
        
        # Build related notes block
        related_block = ""
        if related_links:
            links_text = "\n".join(f"- [[{link}]]" for link in related_links)
            related_block = f"\n\n<!-- ai-related:start -->\n### Related Notes\n{links_text}\n<!-- ai-related:end -->\n"

        final_content = f"---\n{new_yaml}\n---\n{raw_text}{related_block}"

        return self._atomic_write(file_path, final_content)

    def _atomic_write(self, target_path: Path, content: str) -> Path:
        """Atomically write content to target_path."""
        temp_path = target_path.with_suffix(".md.tmp")
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                f.write(content)
            os.replace(temp_path, target_path)
            return target_path
        except Exception:
            if temp_path.exists():
                temp_path.unlink()
            raise
            
    def move_file(self, source_path: Path, target_path: Path) -> Path:
        """Move a file checking for collisions."""
        if source_path == target_path:
            return source_path
            
        if target_path.exists():
            logger.warning(f"Target path {target_path} already exists. Aborting move for {source_path}")
            return source_path
            
        target_path.parent.mkdir(parents=True, exist_ok=True)
        os.replace(source_path, target_path)
        return target_path
