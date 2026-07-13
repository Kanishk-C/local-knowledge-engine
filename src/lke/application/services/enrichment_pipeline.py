"""Enrichment pipeline."""

import hashlib
import json
import logging
import time
from collections.abc import Callable
from datetime import timedelta
from pathlib import Path

from pydantic import BaseModel, Field

from lke.application.services.indexing_pipeline import _MetadataStore
from lke.config.models import EnrichmentConfig
from lke.domain.events.base import DomainEvent
from lke.domain.events.enrichment import (
    EnrichmentCompleted,
    EnrichmentFailed,
    EnrichmentStarted,
    EnrichmentSkipped,
)
from lke.domain.events.filesystem import FileWriteStarting
from lke.domain.models.document import ParsedContent
from lke.domain.models.source import DataSource, SourceType
from lke.domain.protocols.ai_provider import AIProvider
from lke.domain.protocols.parser import Parser
from lke.domain.protocols.vocabulary import FolderVocabulary, TagVocabulary
from lke.domain.repositories.vector_repository import VectorRepository
from lke.infrastructure.parsing.markdown_writer import MarkdownFrontmatterWriter

logger = logging.getLogger(__name__)


class EnrichmentResult:
    """Result of an enrichment operation on a single file."""
    
    def __init__(
        self,
        file_path: Path,
        success: bool,
        skipped: bool = False,
        error: str | None = None,
        duration: timedelta | None = None,
        tags_added: int = 0,
        related_notes_found: int = 0,
    ) -> None:
        self.file_path = file_path
        self.success = success
        self.skipped = skipped
        self.error = error
        self.duration = duration
        self.tags_added = tags_added
        self.related_notes_found = related_notes_found


class BatchEnrichmentResult:
    """Result of an enrichment operation on a vault."""
    
    def __init__(self) -> None:
        self.results: list[EnrichmentResult] = []
        
    def add(self, result: EnrichmentResult) -> None:
        self.results.append(result)
        
    @property
    def total(self) -> int:
        return len(self.results)
        
    @property
    def successful(self) -> int:
        return sum(1 for r in self.results if r.success and not r.skipped)
        
    @property
    def skipped(self) -> int:
        return sum(1 for r in self.results if r.skipped)
        
    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if not r.success)


class EnrichmentOutput(BaseModel):
    """Structured output expected from the LLM."""
    
    tags: list[str] = Field(description="Relevant tags for the document")
    folder: str | None = Field(default=None, description="The suggested folder classification. None if no suitable folder.")
    summary: str | None = Field(default=None, description="A concise summary of the document. None if generation fails.")


class EnrichmentPipeline:
    """Orchestrates AI-driven document enrichment."""

    def __init__(
        self,
        parser: Parser,
        ai_provider: AIProvider,
        vector_repo: VectorRepository,
        tag_vocab: TagVocabulary,
        folder_vocab: FolderVocabulary,
        writer: MarkdownFrontmatterWriter,
        metadata_store: _MetadataStore,
        config: EnrichmentConfig,
    ) -> None:
        self._parser = parser
        self._ai = ai_provider
        self._vector_repo = vector_repo
        self._tag_vocab = tag_vocab
        self._folder_vocab = folder_vocab
        self._writer = writer
        self._metadata = metadata_store
        self._config = config
        
    def _build_prompt(self, parsed: ParsedContent) -> str:
        """Construct the prompt instructing the AI what to do."""
        known_tags = self._tag_vocab.get_all()
        known_folders = self._folder_vocab.get_all()
        
        prompt = (
            "Analyze the following markdown document and extract metadata.\n"
            "You MUST output valid JSON matching the requested schema.\n\n"
        )
        
        prompt += f"Known Tags: {', '.join(known_tags) if known_tags else 'None'}\n"
        prompt += f"Known Folders: {', '.join(known_folders) if known_folders else 'None'}\n\n"
        
        prompt += (
            f"RULES:\n"
            f"- You may propose at most {self._config.max_new_tags_per_note} novel tags not in the Known Tags list.\n"
            f"- You may propose at most {self._config.max_new_folders_per_note} novel folders not in the Known Folders list.\n"
            f"- ONLY apply a Known Tag if it is highly relevant to the document content. DO NOT reuse Known Tags just because they exist.\n"
            f"- Output MUST be a JSON object with 'tags', 'folder', and 'summary' keys.\n"
            f"\nDOCUMENT CONTENT:\n{parsed.raw_text}"
        )
        return prompt

    def _get_cross_encoder(self):
        if not hasattr(self, "_cross_encoder"):
            from sentence_transformers import CrossEncoder
            import logging
            logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
            self._cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        return self._cross_encoder

    def _find_related_notes(self, document_id: str) -> list[str]:
        """Find related notes using Cross-Encoder reranking."""
        chunks = self._vector_repo.get_document(document_id)
        if not chunks:
            return []
            
        # Get candidates using chunk-level search to avoid full table scan
        # We fetch top 50 per chunk to get a good candidate pool for reranking
        candidate_doc_ids = set()
        for chunk in chunks:
            hits = self._vector_repo.search(chunk.embedding, top_k=50)
            for hit in hits:
                hit_doc_id = hit.chunk.chunk.document_id if hasattr(hit, "chunk") else hit.document_id
                if hit_doc_id != document_id:
                    candidate_doc_ids.add(hit_doc_id)
                    
        if not candidate_doc_ids:
            return []
            
        # Re-rank candidates using the Cross-Encoder
        encoder = self._get_cross_encoder()
        query_text = " ".join([c.chunk.content for c in chunks])
        
        cand_pairs = []
        cand_ids_list = list(candidate_doc_ids)
        for cand_id in cand_ids_list:
            cand_chunks = self._vector_repo.get_document(cand_id)
            if cand_chunks:
                cand_text = " ".join([c.chunk.content for c in cand_chunks])
                cand_pairs.append((query_text, cand_text))
            else:
                cand_pairs.append((query_text, ""))
                
        scores = encoder.predict(cand_pairs)
        
        doc_scores: dict[str, float] = {}
        for cand_id, score in zip(cand_ids_list, scores):
            doc_scores[cand_id] = float(score)
            
        # Filter by threshold and sort by score
        threshold = self._config.related_notes_threshold
        related = [
            doc_id for doc_id, score in doc_scores.items() 
            if score >= threshold
        ]
        
        # Sort descending by score
        related.sort(key=lambda d: doc_scores[d], reverse=True)
        
        # Limit to max
        top_related = related[:self._config.related_notes_max]
        
        # Convert document paths to wikilinks. We extract the stem.
        links = []
        for doc in top_related:
            stem = Path(doc).stem
            links.append(f"[[{stem}]]")
            
        return links

    def enrich_document(
        self, 
        file_path: Path, 
        vault_path: Path | None = None,
        event_callback: Callable[[DomainEvent], None] | None = None
    ) -> EnrichmentResult:
        """Enrich a single document."""
        start_time = time.perf_counter()
        document_id = str(file_path.absolute())
        vault_root = vault_path or file_path.parent
        
        def emit(event: DomainEvent) -> None:
            if event_callback:
                event_callback(event)

        try:
            logger.info(f"Enriching document: {file_path}")

            # 1. Parse document
            source = DataSource(uri=document_id, source_type=SourceType.MARKDOWN)
            parsed = self._parser.parse(source)
            
            # Compute hash of the clean body
            content_hash = hashlib.sha256(parsed.raw_text.encode("utf-8")).hexdigest()
            
            # 2. Check skip logic
            # If frontmatter has ai_processed and it matches content_hash, we can skip
            if parsed.frontmatter.get("ai_processed") == content_hash:
                logger.info(f"Skipping enrichment for {file_path} (unchanged)")
                emit(EnrichmentSkipped.create(file_path=str(file_path), reason="unchanged"))
                return EnrichmentResult(
                    file_path=file_path,
                    success=True,
                    skipped=True,
                    duration=timedelta(seconds=time.perf_counter() - start_time),
                )
                
            # 3. Check if indexed
            if not self._metadata.get_hash(document_id):
                logger.warning(f"Document not indexed: {file_path}")
                emit(EnrichmentSkipped.create(file_path=str(file_path), reason="not indexed"))
                return EnrichmentResult(
                    file_path=file_path,
                    success=False,
                    skipped=True,
                    error="Skipped (must be indexed first to find related notes)",
                    duration=timedelta(seconds=time.perf_counter() - start_time),
                )
                
            # 4. Generate structured metadata
            prompt = self._build_prompt(parsed)
            output_dict = self._ai.generate(prompt, schema=EnrichmentOutput)
            output = EnrichmentOutput(**output_dict)
            
            # Retry if summary is empty
            if not output.summary or not output.summary.strip():
                logger.info(f"Received empty summary for {file_path}, retrying...")
                output_dict = self._ai.generate(prompt, schema=EnrichmentOutput)
                output = EnrichmentOutput(**output_dict)
                if not output.summary or not output.summary.strip():
                    logger.warning(f"Summary still empty after retry for {file_path}, omitting summary.")
                    output.summary = None
            
            # Normalize tags (lowercase and hyphenate)
            output.tags = [t.lower().replace(" ", "-") for t in output.tags]
            
            # Validate vocabulary constraints
            known_tags = set(self._tag_vocab.get_all())
            novel_tags = [t for t in output.tags if t not in known_tags]
            if len(novel_tags) > self._config.max_new_tags_per_note:
                # Keep only the allowed amount of novel tags
                allowed_novel = novel_tags[:self._config.max_new_tags_per_note]
                output.tags = [t for t in output.tags if t in known_tags or t in allowed_novel]
                
            for tag in output.tags:
                self._tag_vocab.add(tag)
                
            known_folders = set(self._folder_vocab.get_all())
            # Normalize folder literal None string from LLM
            if output.folder and output.folder.lower() in ("none", "null", "n/a"):
                output.folder = ""
            
            if output.folder not in known_folders and self._config.max_new_folders_per_note == 0:
                output.folder = "" # Disallow new folder if max is 0
            elif output.folder:
                self._folder_vocab.add(output.folder)
                
            # 5. Find related notes
            related_links = self._find_related_notes(document_id)
            
            # 6. Write back to disk
            new_folder = output.folder if self._config.auto_file_enabled else None
            
            # Emit FileWriteStarting before disk write
            emit(FileWriteStarting.create(original_path=str(file_path.absolute()), final_path=str(file_path.absolute())))
            
            final_path = self._writer.write_enrichment(
                file_path=file_path,
                content_hash=content_hash,
                tags=output.tags,
                summary=output.summary,
                related_links=related_links,
                new_folder=new_folder,
            )
            
            move_error = None
            if new_folder:
                # Handle moving by rewriting the file
                target_path = vault_root / new_folder / file_path.name
                if target_path != file_path:
                    # Emit FileWriteStarting before moving
                    emit(FileWriteStarting.create(original_path=str(file_path.absolute()), final_path=str(target_path.absolute())))
                    moved_path = self._writer.move_file(file_path, target_path)
                    if moved_path == file_path:
                        move_error = f"Move skipped: target {target_path} already exists"
                    else:
                        final_path = moved_path
                        
                        # Explicitly re-key the document in Vector and Metadata stores
                        old_doc_id = str(file_path.absolute())
                        new_doc_id = str(final_path.absolute())
                        
                        chunks = self._vector_repo.get_document(old_doc_id)
                        if chunks:
                            for c in chunks:
                                c.chunk.document_id = new_doc_id
                            self._vector_repo.delete_document(old_doc_id)
                            self._vector_repo.upsert(chunks)
                            
                        old_hash = self._metadata.get_hash(old_doc_id)
                        if old_hash:
                            self._metadata.remove(old_doc_id)
                            self._metadata.set_hash(new_doc_id, old_hash)
                            self._metadata.save()

            duration = timedelta(seconds=time.perf_counter() - start_time)
            emit(EnrichmentCompleted.create(file_path=str(file_path), tags=len(output.tags)))
            
            return EnrichmentResult(
                file_path=final_path,
                success=True if not move_error else False,
                error=move_error,
                tags_added=len(output.tags),
                related_notes_found=len(related_links),
                duration=duration,
            )
            
        except Exception as e:
            logger.error(f"Failed to enrich {file_path}: {e}")
            duration = timedelta(seconds=time.perf_counter() - start_time)
            emit(EnrichmentFailed.create(file_path=str(file_path), error=str(e)))
            return EnrichmentResult(
                file_path=file_path,
                success=False,
                error=str(e),
                duration=duration,
            )

    def enrich_vault(
        self, vault_path: Path, event_callback: Callable[[DomainEvent], None] | None = None
    ) -> BatchEnrichmentResult:
        """Enrich an entire directory of documents."""
        result = BatchEnrichmentResult()

        if not vault_path.is_dir():
            logger.error(f"Vault path is not a directory: {vault_path}")
            return result
            
        self._metadata.load()
        markdown_files = list(vault_path.rglob("*.md"))
        logger.info(f"Found {len(markdown_files)} files to enrich in {vault_path}")
        
        if event_callback:
            event_callback(EnrichmentStarted.create(target_path=str(vault_path), total_files=len(markdown_files)))
            
        for file_path in markdown_files:
            doc_result = self.enrich_document(file_path, vault_path, event_callback)
            result.add(doc_result)
            
        return result
