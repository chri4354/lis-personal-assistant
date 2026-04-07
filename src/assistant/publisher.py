"""Publisher: scan publishable markdown, generate MkDocs config, and build the site."""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import yaml

from assistant.repo import get_project_root, list_files_with_frontmatter, read_markdown

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


class PublishConfig:
    """Settings loaded from config/publish.yaml."""

    def __init__(self, base_dir: Path | None = None):
        root = base_dir or get_project_root()
        cfg_path = root / "config" / "publish.yaml"

        cfg: dict[str, Any] = {}
        if cfg_path.exists():
            with open(cfg_path, encoding="utf-8") as f:
                raw = yaml.safe_load(f) or {}
            cfg = raw.get("publish", {})

        self.site_name: str = cfg.get("site_name", "Course Book")
        self.site_url: str = cfg.get("site_url", "")
        self.theme: str = cfg.get("theme", "material")
        self.source_dir: str = cfg.get("source_dir", "publish")
        self.output_dir: str = cfg.get("output_dir", "site")
        self.require_publish_flag: bool = cfg.get("filters", {}).get(
            "require_frontmatter_publish", True
        )


# ---------------------------------------------------------------------------
# Scanning for publishable content
# ---------------------------------------------------------------------------


def _slugify(text: str) -> str:
    """Turn a human string into a URL-safe slug."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


class PublishableFile:
    """A markdown file eligible for publication."""

    def __init__(self, path: Path, meta: dict[str, Any], body: str):
        self.path = path
        self.meta = meta
        self.body = body

    @property
    def title(self) -> str:
        return str(self.meta.get("title", self.path.stem))

    @property
    def module(self) -> str | None:
        return self.meta.get("module") or self.meta.get("module_code")

    @property
    def week(self) -> int | None:
        w = self.meta.get("week")
        return int(w) if w is not None else None

    @property
    def session(self) -> int | None:
        s = self.meta.get("session")
        return int(s) if s is not None else None


def scan_publishable(
    base_dir: Path | None = None,
    config: PublishConfig | None = None,
) -> list[PublishableFile]:
    """Find all markdown files marked for publication.

    Scans outputs/ (lectures, meetings, communications, tasks) and the
    publish/ directory itself for files with `publish: true` in frontmatter.
    """
    root = base_dir or get_project_root()
    config = config or PublishConfig(root)
    results: list[PublishableFile] = []

    scan_dirs = [
        root / "outputs" / "lectures",
        root / "outputs" / "meetings",
        root / "outputs" / "communications",
        root / "outputs" / "tasks",
    ]

    for scan_dir in scan_dirs:
        if not scan_dir.is_dir():
            continue
        for path, meta in list_files_with_frontmatter(scan_dir):
            if config.require_publish_flag and not meta.get("publish"):
                continue
            _, body = read_markdown(path)
            results.append(PublishableFile(path, meta, body))

    return results


# ---------------------------------------------------------------------------
# Copying files to the publish tree
# ---------------------------------------------------------------------------


def _dest_path_for(pf: PublishableFile, publish_root: Path) -> Path:
    """Compute the destination path inside the publish tree.

    Structure: publish/modules/<module-slug>/week-XX/session-XX.md
    Falls back to publish/pages/<filename>.md for files without module info.
    """
    if pf.module:
        mod_slug = _slugify(pf.module)
        parts = [publish_root / "modules" / mod_slug]

        if pf.week is not None:
            parts.append(Path(f"week-{pf.week:02d}"))

        if pf.session is not None:
            filename = f"session-{pf.session:02d}.md"
        else:
            filename = f"{_slugify(pf.title)}.md"

        dest = parts[0]
        for p in parts[1:]:
            dest = dest / p
        return dest / filename
    else:
        return publish_root / "pages" / f"{_slugify(pf.title)}.md"


def copy_to_publish(
    publishable: list[PublishableFile],
    base_dir: Path | None = None,
    config: PublishConfig | None = None,
    clean: bool = False,
) -> list[Path]:
    """Copy publishable files into the publish/ source tree.

    Returns a list of destination paths that were written.
    """
    root = base_dir or get_project_root()
    config = config or PublishConfig(root)
    publish_root = root / config.source_dir

    if clean:
        for sub in ("modules", "pages"):
            target = publish_root / sub
            if target.is_dir():
                shutil.rmtree(target)
        logger.info("Cleaned publish directory")

    written: list[Path] = []
    for pf in publishable:
        dest = _dest_path_for(pf, publish_root)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(pf.body, encoding="utf-8")
        written.append(dest)
        logger.info("Published: %s -> %s", pf.path.name, dest.relative_to(root))

    return written


# ---------------------------------------------------------------------------
# MkDocs config generation
# ---------------------------------------------------------------------------


def _build_nav(publish_root: Path) -> list[Any]:
    """Generate a MkDocs nav structure from the publish directory tree.

    Produces:
      - Home: index.md
      - Module Name:
        - Week 01:
          - Session 01: modules/mod/week-01/session-01.md
        - standalone-page: modules/mod/standalone.md
      - Pages:
        - title: pages/title.md
    """
    nav: list[Any] = []
    index = publish_root / "index.md"
    if index.exists():
        nav.append({"Home": "index.md"})

    # Modules
    modules_dir = publish_root / "modules"
    if modules_dir.is_dir():
        for mod_dir in sorted(modules_dir.iterdir()):
            if not mod_dir.is_dir():
                continue
            mod_label = mod_dir.name.replace("-", " ").title()
            mod_nav: list[Any] = []

            # Check for module index
            mod_index = mod_dir / "index.md"
            if mod_index.exists():
                mod_nav.append({"Overview": f"modules/{mod_dir.name}/index.md"})

            # Week subdirectories
            for week_dir in sorted(mod_dir.iterdir()):
                if not week_dir.is_dir():
                    if week_dir.suffix == ".md" and week_dir.name != "index.md":
                        label = (
                            _title_from_file(week_dir)
                            or week_dir.stem.replace("-", " ").title()
                        )
                        mod_nav.append({label: f"modules/{mod_dir.name}/{week_dir.name}"})
                    continue

                week_label = week_dir.name.replace("-", " ").title()
                week_nav: list[Any] = []
                for session_file in sorted(week_dir.glob("*.md")):
                    s_label = (
                        _title_from_file(session_file)
                        or session_file.stem.replace("-", " ").title()
                    )
                    week_nav.append({
                        s_label: f"modules/{mod_dir.name}/{week_dir.name}/{session_file.name}"
                    })
                if week_nav:
                    mod_nav.append({week_label: week_nav})

            if mod_nav:
                nav.append({mod_label: mod_nav})

    # Pages (non-module content)
    pages_dir = publish_root / "pages"
    if pages_dir.is_dir():
        pages_nav: list[Any] = []
        for md in sorted(pages_dir.glob("*.md")):
            label = _title_from_file(md) or md.stem.replace("-", " ").title()
            pages_nav.append({label: f"pages/{md.name}"})
        if pages_nav:
            nav.append({"Pages": pages_nav})

    return nav


def _title_from_file(path: Path) -> str | None:
    """Try to extract a title from a markdown file's first H1 or frontmatter."""
    try:
        meta, body = read_markdown(path)
        if meta.get("title"):
            return str(meta["title"])
    except Exception:
        pass
    try:
        text = path.read_text(encoding="utf-8")
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("# "):
                return line[2:].strip()
    except Exception:
        pass
    return None


def generate_mkdocs_config(
    base_dir: Path | None = None,
    config: PublishConfig | None = None,
) -> Path:
    """Generate mkdocs.yml from the publish directory structure."""
    root = base_dir or get_project_root()
    config = config or PublishConfig(root)
    publish_root = root / config.source_dir

    nav = _build_nav(publish_root)

    mkdocs_cfg: dict[str, Any] = {
        "site_name": config.site_name,
        "docs_dir": config.source_dir,
        "site_dir": config.output_dir,
        "theme": {
            "name": config.theme,
            "palette": [
                {"scheme": "default", "primary": "indigo", "toggle": {
                    "icon": "material/brightness-7",
                    "name": "Switch to dark mode",
                }},
                {"scheme": "slate", "primary": "indigo", "toggle": {
                    "icon": "material/brightness-4",
                    "name": "Switch to light mode",
                }},
            ],
            "features": [
                "navigation.sections",
                "navigation.expand",
                "toc.integrate",
            ],
        },
        "markdown_extensions": [
            "tables",
            "toc",
            "admonition",
            "pymdownx.details",
            "pymdownx.superfences",
        ],
    }

    if config.site_url:
        mkdocs_cfg["site_url"] = config.site_url

    if nav:
        mkdocs_cfg["nav"] = nav

    out_path = root / "mkdocs.yml"
    with open(out_path, "w", encoding="utf-8") as f:
        yaml.dump(mkdocs_cfg, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    logger.info("Generated mkdocs.yml with %d nav entries", len(nav))
    return out_path


# ---------------------------------------------------------------------------
# Build & serve
# ---------------------------------------------------------------------------


def build_site(base_dir: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Run `mkdocs build` to generate the static site."""
    root = base_dir or get_project_root()
    return subprocess.run(
        ["mkdocs", "build"],
        cwd=str(root),
        capture_output=True,
        text=True,
        check=True,
    )


def serve_site(
    base_dir: Path | None = None,
    port: int = 8001,
) -> subprocess.Popen[str]:
    """Start `mkdocs serve` for local preview (non-blocking)."""
    root = base_dir or get_project_root()
    return subprocess.Popen(
        ["mkdocs", "serve", "--dev-addr", f"127.0.0.1:{port}"],
        cwd=str(root),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


# ---------------------------------------------------------------------------
# High-level orchestration
# ---------------------------------------------------------------------------


def publish_all(
    base_dir: Path | None = None,
    clean: bool = True,
    build: bool = True,
) -> dict[str, Any]:
    """Full pipeline: scan → copy → generate config → build.

    Returns a summary dict with counts and paths.
    """
    root = base_dir or get_project_root()
    config = PublishConfig(root)

    # Ensure index.md exists
    publish_root = root / config.source_dir
    index_path = publish_root / "index.md"
    if not index_path.exists():
        index_path.parent.mkdir(parents=True, exist_ok=True)
        index_path.write_text(
            f"# {config.site_name}\n\nWelcome to the course book.\n",
            encoding="utf-8",
        )

    publishable = scan_publishable(root, config)
    written = copy_to_publish(publishable, root, config, clean=clean)
    mkdocs_path = generate_mkdocs_config(root, config)

    result: dict[str, Any] = {
        "scanned": len(publishable),
        "published": len(written),
        "files": [str(w.relative_to(root)) for w in written],
        "mkdocs_config": str(mkdocs_path.relative_to(root)),
    }

    if build:
        try:
            proc = build_site(root)
            result["build_ok"] = True
            result["build_output"] = proc.stdout
            logger.info("Site built successfully to %s/", config.output_dir)
        except FileNotFoundError:
            result["build_ok"] = False
            result["build_error"] = (
                "mkdocs not found. Install with: pip install mkdocs-material"
            )
            logger.error("mkdocs not found — install with: pip install mkdocs-material")
        except subprocess.CalledProcessError as exc:
            result["build_ok"] = False
            result["build_error"] = exc.stderr or str(exc)
            logger.error("mkdocs build failed: %s", exc.stderr)

    return result
