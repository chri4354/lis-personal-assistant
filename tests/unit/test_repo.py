"""Tests for the repository manager."""

from pathlib import Path

from assistant.repo import (
    generate_output_filename,
    list_files,
    read_markdown,
    write_markdown,
)


def test_write_and_read_markdown(tmp_path: Path):
    """Round-trip: write a markdown file with frontmatter, then read it back."""
    file_path = tmp_path / "test.md"
    metadata = {"title": "Test Note", "type": "meeting-summary", "module": "AI-CI"}
    body = "# Hello\n\nThis is a test note."

    write_markdown(file_path, metadata, body)

    assert file_path.exists()

    read_meta, read_body = read_markdown(file_path)
    assert read_meta["title"] == "Test Note"
    assert read_meta["type"] == "meeting-summary"
    assert "Hello" in read_body


def test_list_files(tmp_path: Path):
    """List markdown files in a directory."""
    (tmp_path / "a.md").write_text("# A")
    (tmp_path / "b.md").write_text("# B")
    (tmp_path / "c.txt").write_text("not markdown")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "d.md").write_text("# D")

    files = list_files(tmp_path, suffix=".md", recursive=True)
    names = [f.name for f in files]
    assert "a.md" in names
    assert "b.md" in names
    assert "d.md" in names
    assert "c.txt" not in names


def test_generate_output_filename_basic():
    """Generate a filename with no metadata."""
    name = generate_output_filename("meeting_to_actions")
    assert name.endswith(".md")
    assert "meeting-to-actions" in name


def test_generate_output_filename_with_module():
    """Generate a filename with module metadata."""
    name = generate_output_filename(
        "lecture_to_page",
        metadata={"module": "AI and Collective Intelligence", "week": 3},
    )
    assert "week-03" in name
    assert "ai-and-collective-intelligence" in name
    assert name.endswith(".md")
