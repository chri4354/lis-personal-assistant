"""Repository manager: read/write markdown files, parse frontmatter, resolve paths."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Any

import frontmatter


def get_project_root() -> Path:
    """Walk up from this file to find the project root (directory containing 'config/')."""
    current = Path(__file__).resolve().parent
    for _ in range(10):
        if (current / "config").is_dir():
            return current
        current = current.parent
    raise FileNotFoundError("Could not locate project root (directory containing 'config/')")


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------


def read_markdown(path: Path) -> tuple[dict[str, Any], str]:
    """Read a markdown file and return (frontmatter_dict, body_text)."""
    post = frontmatter.load(str(path))
    return dict(post.metadata), post.content


def read_markdown_text(path: Path) -> str:
    """Read just the body text of a markdown file (ignoring frontmatter)."""
    _, body = read_markdown(path)
    return body


def read_raw(path: Path) -> str:
    """Read a file as plain text."""
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------


def write_markdown(path: Path, metadata: dict[str, Any], body: str) -> Path:
    """Write a markdown file with YAML frontmatter. Creates parent dirs if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    post = frontmatter.Post(body, **metadata)
    path.write_text(frontmatter.dumps(post) + "\n", encoding="utf-8")
    return path


def write_text(path: Path, content: str) -> Path:
    """Write plain text to a file. Creates parent dirs if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Listing & searching
# ---------------------------------------------------------------------------


def list_files(
    directory: Path,
    suffix: str = ".md",
    recursive: bool = True,
) -> list[Path]:
    """List files in a directory, optionally recursing into subdirectories."""
    if not directory.is_dir():
        return []
    pattern = f"**/*{suffix}" if recursive else f"*{suffix}"
    return sorted(directory.glob(pattern))


def list_files_with_frontmatter(
    directory: Path,
    suffix: str = ".md",
    recursive: bool = True,
) -> list[tuple[Path, dict[str, Any]]]:
    """List markdown files along with their parsed frontmatter."""
    results = []
    for path in list_files(directory, suffix, recursive):
        try:
            meta, _ = read_markdown(path)
            results.append((path, meta))
        except Exception:
            results.append((path, {}))
    return results


# ---------------------------------------------------------------------------
# Path conventions
# ---------------------------------------------------------------------------


def generate_output_filename(
    skill_name: str,
    metadata: dict[str, Any] | None = None,
    suffix: str = ".md",
) -> str:
    """Generate a predictable, sortable filename for a skill output.

    Format: YYYY-MM-DD-<skill-or-topic-slug>.md
    """
    d = date.today()
    if metadata:
        if "date" in metadata and metadata["date"]:
            d = metadata["date"] if isinstance(metadata["date"], date) else d

    slug = skill_name.replace("_", "-")
    if metadata:
        module = metadata.get("module") or metadata.get("module_code")
        if module:
            module_slug = re.sub(r"[^a-z0-9]+", "-", str(module).lower()).strip("-")
            slug = f"{module_slug}-{slug}"
        chapter = metadata.get("chapter")
        if chapter:
            chapter_slug = re.sub(r"[^a-z0-9]+", "-", str(chapter).lower()).strip("-")
            slug = f"{chapter_slug}-{slug}"
        elif metadata.get("week") is not None:
            slug = f"week-{int(metadata['week']):02d}-{slug}"

    return f"{d.isoformat()}-{slug}{suffix}"


def resolve_output_path(
    base_dir: Path,
    output_config_path: str,
    filename: str,
) -> Path:
    """Resolve the full output path from a skill's output config and generated filename."""
    return base_dir / output_config_path / filename
