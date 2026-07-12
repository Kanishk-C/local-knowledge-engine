"""File system watcher service."""

import logging
import queue
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from watchdog.events import (
    FileSystemEvent,
    FileSystemEventHandler,
    FileModifiedEvent,
    FileCreatedEvent,
    FileDeletedEvent,
    FileMovedEvent,
)
from watchdog.observers import Observer

from lke.application.services.enrichment_pipeline import EnrichmentPipeline
from lke.application.services.indexing_pipeline import IndexingPipeline
from lke.domain.events.base import DomainEvent
from lke.domain.events.enrichment import EnrichmentCompleted

logger = logging.getLogger(__name__)


class _IgnoreCache:
    """A TTL-based cache to ignore paths that were just written to."""

    def __init__(self, ttl_seconds: float = 5.0):
        self._cache: dict[str, float] = {}
        self._ttl = ttl_seconds
        self._lock = threading.Lock()

    def add(self, path: str) -> None:
        """Add a path to the ignore cache."""
        with self._lock:
            self._cache[path] = time.time() + self._ttl

    def should_ignore(self, path: str) -> bool:
        """Check if a path should be ignored and clean up expired entries."""
        now = time.time()
        with self._lock:
            # Clean up expired entries to prevent memory leak
            expired = [k for k, v in self._cache.items() if v < now]
            for k in expired:
                del self._cache[k]
                
            return path in self._cache


class WatcherHandler(FileSystemEventHandler):
    """Handles watchdog events and queues them for processing."""

    def __init__(self, event_queue: queue.Queue, ignore_cache: _IgnoreCache):
        super().__init__()
        self._queue = event_queue
        self._ignore_cache = ignore_cache

    def _process_path(self, path: str, event: FileSystemEvent) -> None:
        """Process a path, checking the ignore cache before queueing."""
        if self._ignore_cache.should_ignore(path):
            logger.debug(f"Watcher ignoring self-write event for {path}")
            return
            
        if not path.endswith(".md"):
            return
            
        self._queue.put(event)

    def on_created(self, event: FileSystemEvent) -> None:
        if isinstance(event, FileCreatedEvent):
            self._process_path(event.src_path, event)

    def on_modified(self, event: FileSystemEvent) -> None:
        if isinstance(event, FileModifiedEvent):
            self._process_path(event.src_path, event)

    def on_deleted(self, event: FileSystemEvent) -> None:
        if isinstance(event, FileDeletedEvent):
            self._process_path(event.src_path, event)

    def on_moved(self, event: FileSystemEvent) -> None:
        if isinstance(event, FileMovedEvent):
            # Check old path for ignore (self-move). 
            # If the old_path is in ignore-cache, the whole move is a self-move.
            if self._ignore_cache.should_ignore(event.src_path):
                logger.debug(f"Watcher ignoring self-move from {event.src_path} to {event.dest_path}")
                return
                
            # Otherwise, translate into Deleted + Created
            # Only put if they are .md files
            if event.src_path.endswith(".md"):
                self._queue.put(FileDeletedEvent(event.src_path))
            if event.dest_path.endswith(".md"):
                self._queue.put(FileCreatedEvent(event.dest_path))


class WatcherService:
    """Service to watch a directory and trigger pipelines sequentially."""

    def __init__(
        self,
        vault_path: Path,
        indexing_pipeline: IndexingPipeline,
        enrichment_pipeline: EnrichmentPipeline,
        debounce_seconds: float = 2.0,
    ):
        self.vault_path = vault_path
        self._indexing = indexing_pipeline
        self._enrichment = enrichment_pipeline
        self._debounce_seconds = debounce_seconds
        
        self._queue: queue.Queue[FileSystemEvent] = queue.Queue()
        self._ignore_cache = _IgnoreCache(ttl_seconds=5.0)
        self._handler = WatcherHandler(self._queue, self._ignore_cache)
        self._observer: Optional[Observer] = None
        self._worker_thread: Optional[threading.Thread] = None
        self._running = False
        self._timers: dict[str, threading.Timer] = {}
        self._timer_lock = threading.Lock()

    def start(self) -> None:
        """Start the watcher and worker thread."""
        if self._running:
            return
            
        self._running = True
        
        # Start worker thread
        self._worker_thread = threading.Thread(target=self._process_queue, daemon=True)
        self._worker_thread.start()
        
        # Start watchdog observer
        self._observer = Observer()
        self._observer.schedule(self._handler, str(self.vault_path), recursive=True)
        self._observer.start()
        logger.info(f"Started watch mode on {self.vault_path}")

    def stop(self) -> None:
        """Stop the watcher."""
        self._running = False
        if self._observer:
            self._observer.stop()
            self._observer.join()
        if self._worker_thread:
            self._worker_thread.join()
        logger.info("Watch mode stopped")

    def _process_queue(self) -> None:
        """Worker thread loop to process events sequentially."""
        while self._running:
            try:
                # Use a timeout to allow checking self._running periodically
                event = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue
                
            path_str = event.src_path
            path = Path(path_str)
            
            # Skip hidden folders like .lke
            if ".lke" in path.parts:
                self._queue.task_done()
                continue
                
            # Check ignore cache for self-writes
            if isinstance(event, (FileCreatedEvent, FileModifiedEvent, FileDeletedEvent)):
                # For move events, they are translated to Deleted(src) + Created(dest).
                # We need to ignore both if they are in the cache.
                if self._ignore_cache.should_ignore(path_str):
                    logger.debug(f"Ignoring self-write for {path_str}")
                    self._queue.task_done()
                    continue
                
            # Handle Debounce for Created/Modified
            if isinstance(event, (FileCreatedEvent, FileModifiedEvent)):
                with self._timer_lock:
                    if path_str in self._timers:
                        self._timers[path_str].cancel()
                    
                    timer = threading.Timer(
                        self._debounce_seconds,
                        self._trigger_change,
                        args=[path, path_str]
                    )
                    self._timers[path_str] = timer
                    timer.start()
                    
            elif isinstance(event, FileDeletedEvent):
                with self._timer_lock:
                    if path_str in self._timers:
                        self._timers[path_str].cancel()
                        del self._timers[path_str]
                logger.info(f"Processing deletion for {path_str}")
                self._handle_delete(path)
                
            self._queue.task_done()

    def _trigger_change(self, path: Path, path_str: str) -> None:
        """Trigger the change after debounce period."""
        with self._timer_lock:
            if path_str in self._timers:
                del self._timers[path_str]
        logger.info(f"Processing change for {path_str}")
        self._handle_change(path)

    def _on_event(self, event: DomainEvent) -> None:
        """Callback for pipeline events."""
        from lke.domain.events.filesystem import FileWriteStarting
        
        if isinstance(event, FileWriteStarting):
            self._ignore_cache.add(event.original_path)
            if event.final_path != event.original_path:
                self._ignore_cache.add(event.final_path)

    def _handle_change(self, path: Path) -> None:
        """Handle a file creation or modification."""
        try:
            doc_id = str(path.absolute())
            
            # 1. Indexing
            index_result = self._indexing.index_document(path)
            
            if not index_result.success:
                logger.error(f"Indexing failed for {doc_id}")
                return
                
            # 2. Enrichment (only if indexing succeeded)
            # Pass our event callback so we can catch FileWriteStarting
            enrich_result = self._enrichment.enrich_document(path, event_callback=self._on_event)
            
            if not enrich_result.success:
                logger.error(f"Enrichment failed for {doc_id}")
                
        except Exception as e:
            logger.error(f"Error handling change for {path}: {e}")

    def _handle_delete(self, path: Path) -> None:
        """Handle a file deletion."""
        try:
            doc_id = str(path.absolute())
            self._indexing.remove_document(doc_id)
        except Exception as e:
            logger.error(f"Error handling deletion for {path}: {e}")

