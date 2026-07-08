"""Domain service for text chunking."""

from collections.abc import Iterator

from lke.domain.models.document import ContentType, DocumentChunk, ParsedContent


class ChunkingService:
    """Service to split parsed content into smaller document chunks."""

    def __init__(self, max_tokens: int = 500, overlap_tokens: int = 50) -> None:
        """Initialize the chunking service.

        Args:
            max_tokens: Maximum estimated tokens per chunk.
            overlap_tokens: Number of tokens to overlap between chunks.
        """
        if max_tokens <= 0:
            raise ValueError("max_tokens must be greater than 0")
        if overlap_tokens < 0:
            raise ValueError("overlap_tokens cannot be negative")
        if overlap_tokens >= max_tokens:
            raise ValueError("overlap_tokens must be strictly less than max_tokens")

        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens

        # Simple estimation: 1 token ≈ 4 characters
        self.max_chars = self.max_tokens * 4
        self.overlap_chars = self.overlap_tokens * 4

    def chunk(self, parsed_content: ParsedContent) -> list[DocumentChunk]:
        """Split a ParsedContent object into multiple DocumentChunks."""
        text = parsed_content.raw_text.strip()
        if not text:
            return []

        chunks: list[DocumentChunk] = []

        for idx, chunk_text in enumerate(self._split_text(text)):
            chunks.append(
                DocumentChunk(
                    chunk_id=f"{parsed_content.document_id}_{idx}",
                    document_id=parsed_content.document_id,
                    content=chunk_text,
                    chunk_index=idx,
                    content_type=ContentType.PROSE,
                    metadata=parsed_content.frontmatter.copy(),
                )
            )

        return chunks

    def _split_text(self, text: str) -> Iterator[str]:
        """Split text into chunks based on character limits, without splitting words."""
        if len(text) <= self.max_chars:
            yield text
            return

        # Split into words (simplistic word boundary to avoid breaking words)
        words = text.split()

        current_chunk: list[str] = []
        current_len = 0

        # To handle overlap, we keep track of trailing words from the previous chunk
        overlap_buffer: list[str] = []
        overlap_len = 0

        for word in words:
            word_len = len(word) + (1 if current_len > 0 else 0)  # +1 for space

            if current_len + word_len > self.max_chars:
                if current_chunk:
                    yield " ".join(current_chunk)

                # Start new chunk with overlap
                current_chunk = list(overlap_buffer)
                current_len = overlap_len

                # If a single word is larger than the max_chars, it'll bypass the limit
                # We have to add it anyway so we don't lose data, but it will be a big chunk.
                if current_len == 0 and word_len > self.max_chars:
                    current_chunk.append(word)
                    current_len = len(word)
                    yield " ".join(current_chunk)
                    current_chunk = []
                    current_len = 0
                    overlap_buffer = []
                    overlap_len = 0
                    continue

            current_chunk.append(word)
            current_len += word_len

            # Update overlap buffer (keep the last `overlap_chars` worth of words)
            overlap_buffer.append(word)
            overlap_len += len(word) + (1 if len(overlap_buffer) > 1 else 0)

            while overlap_len > self.overlap_chars and len(overlap_buffer) > 0:
                removed_word = overlap_buffer.pop(0)
                overlap_len -= len(removed_word) + (1 if len(overlap_buffer) > 0 else 0)

        if current_chunk:
            yield " ".join(current_chunk)
