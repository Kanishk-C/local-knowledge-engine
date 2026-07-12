import pytest
from unittest.mock import Mock, call
from pathlib import Path
from watchdog.events import FileModifiedEvent, FileDeletedEvent, FileMovedEvent
import time

from lke.application.services.watcher_service import WatcherService, _IgnoreCache
from lke.domain.events.filesystem import FileWriteStarting

def test_watcher_service_handle_change_success():
    mock_indexing = Mock()
    mock_enrichment = Mock()
    
    mock_indexing.index_document.return_value.success = True
    mock_enrichment.enrich_document.return_value.success = True
    
    watcher = WatcherService(Path("/tmp"), mock_indexing, mock_enrichment)
    
    test_path = Path("/tmp/test.md")
    watcher._handle_change(test_path)
    
    # Verify indexing called
    mock_indexing.index_document.assert_called_once_with(str(test_path.absolute()))
    
    # Verify enrichment called and callback passed
    mock_enrichment.enrich_document.assert_called_once()
    kwargs = mock_enrichment.enrich_document.call_args[1]
    assert "event_callback" in kwargs
    assert kwargs["event_callback"] == watcher._on_event

def test_watcher_service_handle_change_indexing_fails():
    mock_indexing = Mock()
    mock_enrichment = Mock()
    
    mock_indexing.index_document.return_value.success = False
    
    watcher = WatcherService(Path("/tmp"), mock_indexing, mock_enrichment)
    
    test_path = Path("/tmp/test.md")
    watcher._handle_change(test_path)
    
    # Verify indexing called
    mock_indexing.index_document.assert_called_once_with(str(test_path.absolute()))
    
    # Verify enrichment NOT called
    mock_enrichment.enrich_document.assert_not_called()

def test_watcher_service_ignore_cache_logic():
    cache = _IgnoreCache(ttl_seconds=0.1)
    
    cache.add("/tmp/test1.md")
    assert cache.should_ignore("/tmp/test1.md") is True
    assert cache.should_ignore("/tmp/test2.md") is False
    
    # Let it expire
    time.sleep(0.2)
    assert cache.should_ignore("/tmp/test1.md") is False

def test_watcher_service_on_event():
    mock_indexing = Mock()
    mock_enrichment = Mock()
    
    watcher = WatcherService(Path("/tmp"), mock_indexing, mock_enrichment)
    
    event = FileWriteStarting.create(original_path="/tmp/test1.md", final_path="/tmp/test2.md")
    watcher._on_event(event)
    
    assert watcher._ignore_cache.should_ignore("/tmp/test1.md") is True
    assert watcher._ignore_cache.should_ignore("/tmp/test2.md") is True
    assert watcher._ignore_cache.should_ignore("/tmp/other.md") is False
