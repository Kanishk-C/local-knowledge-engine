"""Domain service for text chunking."""

import math
import re
from dataclasses import dataclass
from typing import Any

from lke.domain.models.document import ContentType, DocumentChunk, ParsedContent


@dataclass(slots=True)
class Section:
    """Internal representation of a parsed markdown section."""

    heading: str
    level: int
    path: list[str]
    content: str
    start_offset: int
    end_offset: int


class ChunkingService:
    """Service to split parsed content into smaller document chunks."""

    # Matches Markdown headings (e.g., # Heading)
    _HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.*)", re.MULTILINE)

    def __init__(
        self,
        max_tokens: int = 500,
        overlap_tokens: int = 50,
        min_tokens: int = 100,
    ) -> None:
        """Initialize the chunking service.

        Args:
            max_tokens: Maximum estimated tokens per chunk.
            overlap_tokens: Number of tokens to overlap between chunks.
            min_tokens: Minimum estimated tokens per chunk (for merging).
        """
        if max_tokens <= 0:
            raise ValueError("max_tokens must be greater than 0")
        if overlap_tokens < 0:
            raise ValueError("overlap_tokens cannot be negative")
        if overlap_tokens >= max_tokens:
            raise ValueError("overlap_tokens must be strictly less than max_tokens")
        if min_tokens < 0:
            raise ValueError("min_tokens cannot be negative")

        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
        self.min_tokens = min_tokens

        # Simple estimation: 1 token ≈ 4 characters
        self.max_chars = self.max_tokens * 4
        self.overlap_chars = self.overlap_tokens * 4
        self.min_chars = self.min_tokens * 4

    def chunk(self, parsed_content: ParsedContent) -> list[DocumentChunk]:
        """Split a ParsedContent object into multiple DocumentChunks."""
        text = parsed_content.raw_text
        if not text.strip():
            return []

        # 1. Markdown -> Section[]
        sections = self._build_sections(text)

        # 2. Merge Small Sections
        merged_sections = self._merge_sections(sections)

        # 3. Split Large Sections
        final_sections = self._split_large_sections(merged_sections)

        # 4. Chunk Builder
        return self._build_chunks(parsed_content, final_sections)

    def _count_tokens(self, text: str) -> int:
        return math.ceil(len(text) / 4)

    def _build_sections(self, text: str) -> list[Section]:
        lines = text.splitlines(keepends=True)
        sections: list[Section] = []

        in_code_block = False
        path_stack: list[tuple[int, str]] = []

        current_content: list[str] = []
        current_heading = ""
        current_level = 0
        current_path: list[str] = []
        start_offset = 0
        current_offset = 0

        for line in lines:
            is_code_fence = line.lstrip().startswith("```")
            if is_code_fence:
                in_code_block = not in_code_block

            if not in_code_block:
                match = self._HEADING_PATTERN.match(line)
                if match:
                    # Save previous section
                    content_str = "".join(current_content)
                    if content_str.strip() or current_content:
                        sections.append(
                            Section(
                                heading=current_heading,
                                level=current_level,
                                path=list(current_path),
                                content=content_str,
                                start_offset=start_offset,
                                end_offset=current_offset,
                            )
                        )

                    # Start new section
                    level = len(match.group(1))
                    heading_text = match.group(2).strip()

                    path_stack = [(lvl, txt) for lvl, txt in path_stack if lvl < level]
                    path_stack.append((level, heading_text))

                    current_heading = heading_text
                    current_level = level
                    current_path = [txt for _, txt in path_stack]

                    current_content = [line]
                    start_offset = current_offset
                    current_offset += len(line)
                    continue

            # Normal line (or inside code block)
            current_content.append(line)
            current_offset += len(line)

        # Add the last section
        if current_content:
            sections.append(
                Section(
                    heading=current_heading,
                    level=current_level,
                    path=list(current_path),
                    content="".join(current_content),
                    start_offset=start_offset,
                    end_offset=current_offset,
                )
            )

        return sections

    def _merge_sections(self, sections: list[Section]) -> list[Section]:
        if not sections:
            return []

        merged: list[Section] = []
        current = sections[0]

        for nxt in sections[1:]:
            # Merge if they are siblings under the same parent and fit within max_chars
            same_parent = current.path[:-1] == nxt.path[:-1] and len(current.path[:-1]) > 0
            combined_len = len(current.content) + len(nxt.content)

            if same_parent and combined_len <= self.max_chars:
                parent_path = current.path[:-1]
                parent_level = current.level - 1 if current.level > 1 else 1

                current = Section(
                    heading=parent_path[-1] if parent_path else "",
                    level=parent_level,
                    path=parent_path,
                    content=current.content + nxt.content,
                    start_offset=current.start_offset,
                    end_offset=nxt.end_offset,
                )
            else:
                merged.append(current)
                current = nxt

        merged.append(current)
        return merged

    def _get_blocks(self, text: str, base_offset: int) -> list[tuple[str, int, int]]:
        lines = text.splitlines(keepends=True)
        blocks = []
        current_block: list[str] = []
        in_code_block = False

        for line in lines:
            is_code_fence = line.lstrip().startswith("```")
            if is_code_fence:
                in_code_block = not in_code_block

            if not in_code_block and line.strip() == "":
                current_block.append(line)
                blocks.append("".join(current_block))
                current_block = []
            else:
                current_block.append(line)

        if current_block:
            blocks.append("".join(current_block))

        refined_blocks = []
        curr_off = base_offset
        for b in blocks:
            if len(b) > self.max_chars:
                # Split by lines as a last resort
                for line in b.splitlines(keepends=True):
                    refined_blocks.append((line, curr_off, curr_off + len(line)))
                    curr_off += len(line)
            else:
                refined_blocks.append((b, curr_off, curr_off + len(b)))
                curr_off += len(b)

        return refined_blocks

    def _split_content(self, text: str, base_offset: int) -> list[tuple[str, int, int]]:
        block_offsets = self._get_blocks(text, base_offset)

        splits = []
        i = 0
        while i < len(block_offsets):
            chunk_blocks = []
            chunk_len = 0
            chunk_start = block_offsets[i][1]

            while (
                i < len(block_offsets) and chunk_len + len(block_offsets[i][0]) <= self.max_chars
            ):
                chunk_blocks.append(block_offsets[i][0])
                chunk_len += len(block_offsets[i][0])
                i += 1

            if not chunk_blocks and i < len(block_offsets):
                chunk_blocks.append(block_offsets[i][0])
                chunk_len += len(block_offsets[i][0])
                i += 1

            chunk_text = "".join(chunk_blocks)
            chunk_end = chunk_start + len(chunk_text)
            splits.append((chunk_text, chunk_start, chunk_end))

            if i >= len(block_offsets):
                break

            overlap_len = 0
            next_start_idx = i
            for j in range(i - 1, -1, -1):
                if block_offsets[j][1] <= chunk_start:
                    break
                if overlap_len + len(block_offsets[j][0]) <= self.overlap_chars:
                    overlap_len += len(block_offsets[j][0])
                    next_start_idx = j
                else:
                    break

            i = next_start_idx

        return splits

    def _split_large_sections(self, sections: list[Section]) -> list[tuple[Section, bool]]:
        final_sections: list[tuple[Section, bool]] = []

        for sec in sections:
            if len(sec.content) <= self.max_chars:
                final_sections.append((sec, False))
                continue

            splits = self._split_content(sec.content, sec.start_offset)
            is_split = len(splits) > 1

            for split_content, start_off, end_off in splits:
                final_sections.append(
                    (
                        Section(
                            heading=sec.heading,
                            level=sec.level,
                            path=sec.path,
                            content=split_content,
                            start_offset=start_off,
                            end_offset=end_off,
                        ),
                        is_split,
                    )
                )

        return final_sections

    def _build_chunks(
        self, parsed: ParsedContent, sections: list[tuple[Section, bool]]
    ) -> list[DocumentChunk]:
        chunks = []

        for idx, (sec, is_split) in enumerate(sections):
            chunk_id = f"{parsed.document_id}:{idx}"

            metadata: dict[str, Any] = {
                "heading_path": sec.path,
                "heading_level": sec.level,
                "start_offset": sec.start_offset,
                "end_offset": sec.end_offset,
                "token_count": self._count_tokens(sec.content),
                "source_path": parsed.document_id,
                "section_index": idx,
                "is_split": is_split,
            }

            combined_meta = parsed.frontmatter.copy()
            combined_meta.update(metadata)

            chunks.append(
                DocumentChunk(
                    chunk_id=chunk_id,
                    document_id=parsed.document_id,
                    content=sec.content.strip(),
                    chunk_index=idx,
                    content_type=ContentType.PROSE,
                    metadata=combined_meta,
                )
            )

        return chunks
