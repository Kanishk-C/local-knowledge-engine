import json
import pytest
from pathlib import Path

from lke.infrastructure.vocabulary.json_vocabulary import JsonVocabulary


def test_json_vocabulary_add_and_get(tmp_path: Path) -> None:
    """Test adding items and retrieving them."""
    vocab = JsonVocabulary(tmp_path, "test.json")
    
    assert vocab.get_all() == []
    
    vocab.add("python")
    vocab.add("rust")
    vocab.add("python")  # Duplicate should be ignored
    
    assert vocab.get_all() == ["python", "rust"]
    
    # Verify persistence
    vocab2 = JsonVocabulary(tmp_path, "test.json")
    assert vocab2.get_all() == ["python", "rust"]


def test_json_vocabulary_migration(tmp_path: Path) -> None:
    """Test migration from legacy .notemind directory."""
    legacy_dir = tmp_path / ".notemind"
    legacy_dir.mkdir()
    legacy_file = legacy_dir / "tags.json"
    legacy_file.write_text(json.dumps(["legacy_tag1", "legacy_tag2"]))
    
    vocab = JsonVocabulary(tmp_path, "tags.json")
    assert vocab.get_all() == ["legacy_tag1", "legacy_tag2"]
