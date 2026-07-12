from pathlib import Path
from lke.infrastructure.parsing.markdown_writer import MarkdownFrontmatterWriter

def test_move_file_collision_aborts(tmp_path: Path):
    writer = MarkdownFrontmatterWriter()
    source_path = tmp_path / "source.md"
    source_path.write_text("source content")
    
    target_path = tmp_path / "target.md"
    target_path.write_text("target content")
    
    result = writer.move_file(source_path, target_path)
    
    assert result == source_path
    assert source_path.exists()
    assert target_path.exists()
    assert target_path.read_text() == "target content"
