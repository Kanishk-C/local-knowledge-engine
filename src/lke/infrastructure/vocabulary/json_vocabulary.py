"""JSON-based vocabulary storage."""

import json
import os
from pathlib import Path

from lke.domain.protocols.vocabulary import FolderVocabulary, TagVocabulary


class JsonVocabulary(TagVocabulary, FolderVocabulary):
    """Vocabulary manager backed by a JSON file.
    
    Implements both TagVocabulary and FolderVocabulary.
    Handles migration from legacy .notemind structure if necessary.
    """

    def __init__(self, workspace_path: str | Path, filename: str) -> None:
        """Initialize the JSON vocabulary.
        
        Args:
            workspace_path: The root workspace directory (where .lke/ lives)
            filename: The name of the json file (e.g., 'tags.json')
        """
        self._workspace_path = Path(workspace_path)
        self._lke_dir = self._workspace_path / ".lke"
        self._lke_dir.mkdir(parents=True, exist_ok=True)
        self._file_path = self._lke_dir / filename
        
        # Migration from legacy .notemind
        legacy_path = self._workspace_path / ".notemind" / filename
        if legacy_path.exists() and not self._file_path.exists():
            try:
                import shutil
                shutil.copy2(legacy_path, self._file_path)
            except Exception:
                pass
                
        self._items: set[str] = set()
        self._load()

    def _load(self) -> None:
        """Load vocabulary from disk."""
        if not self._file_path.exists():
            return
            
        try:
            with open(self._file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    self._items = set(str(item) for item in data)
        except Exception:
            pass

    def _save(self) -> None:
        """Save vocabulary to disk atomically."""
        temp_path = self._file_path.with_suffix(".json.tmp")
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(sorted(list(self._items)), f, indent=2)
            os.replace(temp_path, self._file_path)
        except Exception:
            if temp_path.exists():
                temp_path.unlink()
            raise

    def get_all(self) -> list[str]:
        """Retrieve all known items."""
        return sorted(list(self._items))

    def add(self, item: str) -> None:
        """Add a new item to the vocabulary."""
        if item not in self._items:
            self._items.add(item)
            self._save()
