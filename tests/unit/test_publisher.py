"""Tests for the publication pipeline."""

from pathlib import Path
from unittest.mock import patch

import yaml

from assistant.publisher import (
    PublishableFile,
    _build_nav,
    _dest_path_for,
    copy_to_publish,
    generate_mkdocs_config,
    scan_publishable,
)


def _write_md(path: Path, frontmatter: dict, body: str = "Content here.") -> Path:
    """Write a markdown file with frontmatter."""
    import frontmatter as fm

    path.parent.mkdir(parents=True, exist_ok=True)
    post = fm.Post(body, **frontmatter)
    path.write_text(fm.dumps(post) + "\n", encoding="utf-8")
    return path


def _make_project(tmp_path: Path) -> Path:
    """Set up a minimal project structure for publisher tests."""
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "publish.yaml").write_text(
        "publish:\n  site_name: Test Book\n  source_dir: publish\n  output_dir: site\n"
        "  filters:\n    require_frontmatter_publish: true\n"
    )
    (tmp_path / "publish").mkdir()
    (tmp_path / "publish" / "index.md").write_text("# Test Book\n")
    return tmp_path


def test_scan_publishable_finds_flagged_files(tmp_path):
    """Only files with publish: true are returned."""
    root = _make_project(tmp_path)
    lectures = root / "outputs" / "lectures"

    _write_md(lectures / "lecture1.md", {"title": "L1", "publish": True, "module": "AI"})
    _write_md(lectures / "lecture2.md", {"title": "L2", "publish": False})
    _write_md(lectures / "lecture3.md", {"title": "L3"})

    with patch("assistant.publisher.get_project_root", return_value=root):
        result = scan_publishable(root)

    assert len(result) == 1
    assert result[0].title == "L1"


def test_scan_publishable_returns_empty_when_none(tmp_path):
    """Empty result when no files have publish: true."""
    root = _make_project(tmp_path)
    lectures = root / "outputs" / "lectures"
    _write_md(lectures / "draft.md", {"title": "Draft"})

    with patch("assistant.publisher.get_project_root", return_value=root):
        result = scan_publishable(root)

    assert result == []


def test_dest_path_with_module_week_session(tmp_path):
    """File gets placed at modules/<mod>/week-XX/session-XX.md."""
    publish_root = tmp_path / "publish"
    pf = PublishableFile(
        path=Path("/fake/lecture.md"),
        meta={"title": "Intro", "module": "AI and CI", "week": 3, "session": 1},
        body="content",
    )

    dest = _dest_path_for(pf, publish_root)

    assert dest == publish_root / "modules" / "ai-and-ci" / "week-03" / "session-01.md"


def test_dest_path_without_module(tmp_path):
    """File without module goes into pages/."""
    publish_root = tmp_path / "publish"
    pf = PublishableFile(
        path=Path("/fake/notes.md"),
        meta={"title": "General Notes"},
        body="content",
    )

    dest = _dest_path_for(pf, publish_root)

    assert dest == publish_root / "pages" / "general-notes.md"


def test_dest_path_module_no_session(tmp_path):
    """Module file without session uses title slug as filename."""
    publish_root = tmp_path / "publish"
    pf = PublishableFile(
        path=Path("/fake/lecture.md"),
        meta={"title": "Overview Lecture", "module": "AI", "week": 1},
        body="content",
    )

    dest = _dest_path_for(pf, publish_root)

    assert dest == publish_root / "modules" / "ai" / "week-01" / "overview-lecture.md"


def test_copy_to_publish_writes_files(tmp_path):
    """copy_to_publish creates files in the publish tree."""
    root = _make_project(tmp_path)
    pf = PublishableFile(
        path=Path("/src/lecture.md"),
        meta={"title": "Session 1", "module": "AI", "week": 1, "session": 1},
        body="# Session 1\n\nContent here.",
    )

    written = copy_to_publish([pf], base_dir=root)

    assert len(written) == 1
    assert written[0].exists()
    assert "Content here" in written[0].read_text()


def test_copy_to_publish_clean_removes_old(tmp_path):
    """With clean=True, old module/pages dirs are removed first."""
    root = _make_project(tmp_path)
    old_file = root / "publish" / "modules" / "old" / "old.md"
    old_file.parent.mkdir(parents=True)
    old_file.write_text("stale content")

    copy_to_publish([], base_dir=root, clean=True)

    assert not old_file.exists()


def test_build_nav_structure(tmp_path):
    """Nav generation follows Home → Modules → Weeks → Sessions structure."""
    publish_root = tmp_path / "publish"
    (publish_root / "index.md").parent.mkdir(parents=True)
    (publish_root / "index.md").write_text("# Home\n")

    mod_dir = publish_root / "modules" / "ai-ci" / "week-01"
    mod_dir.mkdir(parents=True)
    (mod_dir / "session-01.md").write_text("# Intro to AI\n")
    (mod_dir / "session-02.md").write_text("# Deep Learning\n")

    nav = _build_nav(publish_root)

    assert nav[0] == {"Home": "index.md"}
    assert "Ai Ci" in str(nav[1])


def test_generate_mkdocs_config_creates_file(tmp_path):
    """generate_mkdocs_config writes a valid YAML file."""
    root = _make_project(tmp_path)

    with patch("assistant.publisher.get_project_root", return_value=root):
        mkdocs_path = generate_mkdocs_config(root)

    assert mkdocs_path.exists()
    cfg = yaml.safe_load(mkdocs_path.read_text())
    assert cfg["site_name"] == "Test Book"
    assert cfg["docs_dir"] == "publish"
    assert "nav" in cfg
