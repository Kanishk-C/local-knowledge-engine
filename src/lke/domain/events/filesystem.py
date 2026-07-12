from dataclasses import dataclass

from lke.domain.events.base import DomainEvent


@dataclass(frozen=True)
class FileWriteStarting(DomainEvent):
    """Emitted immediately before a file write or move operation touches the disk.
    
    This allows services like the File System Watcher to ignore the subsequent
    OS-level watchdog events (like Modified, Deleted, Created) caused by our own
    writes, preventing infinite loops.
    """
    
    original_path: str
    final_path: str
