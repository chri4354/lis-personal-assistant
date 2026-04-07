"""Publisher: scan publishable markdown, generate MkDocs config, and build the site."""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import frontmatter as fm
import yaml

from assistant.repo import get_project_root, list_files_with_frontmatter, read_markdown

logger = logging.getLogger(__name__)

_IGNORE_FILENAMES = {"README.md", "index.md", "module.yaml"}


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


class ModuleConfig:
    """Per-module deployment config loaded from module.yaml."""

    def __init__(self, module_dir: Path):
        self.module_dir = module_dir
        self.slug = module_dir.name
        cfg_path = module_dir / "module.yaml"

        cfg: dict[str, Any] = {}
        if cfg_path.exists():
            with open(cfg_path, encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}

        self.site_name: str = cfg.get(
            "site_name",
            module_dir.name.replace("-", " ").title(),
        )
        self.remote: str = cfg.get("remote", "")
        self.site_url: str = cfg.get("site_url", "")
        self.branch: str = cfg.get("branch", "main")

    @property
    def has_remote(self) -> bool:
        return bool(self.remote)


def list_module_configs(
    base_dir: Path | None = None,
    config: PublishConfig | None = None,
) -> list[ModuleConfig]:
    """Return ModuleConfig for every module directory in publish/."""
    root = base_dir or get_project_root()
    config = config or PublishConfig(root)
    modules_dir = root / config.source_dir / "modules"
    if not modules_dir.is_dir():
        return []
    return [
        ModuleConfig(d)
        for d in sorted(modules_dir.iterdir())
        if d.is_dir()
    ]


# ---------------------------------------------------------------------------
# Scanning for publishable content
# ---------------------------------------------------------------------------


def _slugify(text: str) -> str:
    """Turn a human string into a URL-safe slug."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


class PublishableFile:
    """A markdown file eligible for publication."""

    def __init__(
        self,
        path: Path,
        meta: dict[str, Any],
        body: str,
        *,
        direct: bool = False,
    ):
        self.path = path
        self.meta = meta
        self.body = body
        self.direct = direct  # True = already lives in publish/

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

    @property
    def source_label(self) -> str:
        return "direct" if self.direct else "outputs"


def scan_publishable(
    base_dir: Path | None = None,
    config: PublishConfig | None = None,
) -> list[PublishableFile]:
    """Find all markdown files marked for publication.

    Scans two locations:
      1. outputs/ (lectures, meetings, communications, tasks) —
         these get copied into publish/ during build
      2. publish/ itself (modules/, pages/) —
         these are hand-curated and already in place
    """
    root = base_dir or get_project_root()
    config = config or PublishConfig(root)
    results: list[PublishableFile] = []
    seen_titles: set[str] = set()

    # 1. Scan outputs/
    output_dirs = [
        root / "outputs" / "lectures",
        root / "outputs" / "meetings",
        root / "outputs" / "communications",
        root / "outputs" / "tasks",
    ]

    for scan_dir in output_dirs:
        if not scan_dir.is_dir():
            continue
        for path, meta in list_files_with_frontmatter(scan_dir):
            if config.require_publish_flag and not meta.get("publish"):
                continue
            _, body = read_markdown(path)
            results.append(PublishableFile(path, meta, body))
            seen_titles.add(meta.get("title", path.stem))

    # 2. Scan publish/ for directly placed content
    publish_root = root / config.source_dir
    for sub in ("modules", "pages"):
        sub_dir = publish_root / sub
        if not sub_dir.is_dir():
            continue
        for path, meta in list_files_with_frontmatter(sub_dir):
            if path.name in _IGNORE_FILENAMES:
                continue
            if config.require_publish_flag and not meta.get("publish"):
                continue
            title = meta.get("title", path.stem)
            if title in seen_titles:
                continue
            _, body = read_markdown(path)
            results.append(
                PublishableFile(path, meta, body, direct=True)
            )

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

    Files already in publish/ (direct=True) are skipped during copy.
    Returns a list of all destination paths (both copied and direct).
    """
    root = base_dir or get_project_root()
    config = config or PublishConfig(root)
    publish_root = root / config.source_dir

    # Collect direct files before cleaning so we can restore them
    direct_files: list[PublishableFile] = [
        pf for pf in publishable if pf.direct
    ]

    if clean:
        for sub in ("modules", "pages"):
            target = publish_root / sub
            if target.is_dir():
                shutil.rmtree(target)
        logger.info("Cleaned publish directory")

        # Restore direct files after cleaning
        for pf in direct_files:
            pf.path.parent.mkdir(parents=True, exist_ok=True)
            content = pf.body
            if pf.meta:
                post = fm.Post(pf.body, **pf.meta)
                content = fm.dumps(post) + "\n"
            pf.path.write_text(content, encoding="utf-8")
            logger.info("Restored direct file: %s", pf.path.name)

    written: list[Path] = []
    for pf in publishable:
        if pf.direct:
            written.append(pf.path)
            continue
        dest = _dest_path_for(pf, publish_root)
        dest.parent.mkdir(parents=True, exist_ok=True)
        post = fm.Post(pf.body, **pf.meta)
        dest.write_text(fm.dumps(post) + "\n", encoding="utf-8")
        written.append(dest)
        logger.info(
            "Published: %s -> %s",
            pf.path.name, dest.relative_to(root),
        )

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
                mod_nav.append(
                    {"Overview": f"modules/{mod_dir.name}/index.md"}
                )

            # Week subdirectories
            for week_dir in sorted(mod_dir.iterdir()):
                if not week_dir.is_dir():
                    if (
                        week_dir.suffix == ".md"
                        and week_dir.name != "index.md"
                    ):
                        label = (
                            _title_from_file(week_dir)
                            or week_dir.stem.replace("-", " ").title()
                        )
                        rel = f"modules/{mod_dir.name}/{week_dir.name}"
                        mod_nav.append({label: rel})
                    continue

                week_label = week_dir.name.replace("-", " ").title()
                week_nav: list[Any] = []
                for sf in sorted(week_dir.glob("*.md")):
                    s_label = (
                        _title_from_file(sf)
                        or sf.stem.replace("-", " ").title()
                    )
                    rel = (
                        f"modules/{mod_dir.name}"
                        f"/{week_dir.name}/{sf.name}"
                    )
                    week_nav.append({s_label: rel})
                if week_nav:
                    mod_nav.append({week_label: week_nav})

            if mod_nav:
                nav.append({mod_label: mod_nav})

    # Pages (non-module content)
    pages_dir = publish_root / "pages"
    if pages_dir.is_dir():
        pages_nav: list[Any] = []
        for md in sorted(pages_dir.glob("*.md")):
            label = (
                _title_from_file(md)
                or md.stem.replace("-", " ").title()
            )
            pages_nav.append({label: f"pages/{md.name}"})
        if pages_nav:
            nav.append({"Pages": pages_nav})

    return nav


def _title_from_file(path: Path) -> str | None:
    """Try to extract a title from frontmatter or first H1."""
    try:
        meta, _ = read_markdown(path)
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
        yaml.dump(
            mkdocs_cfg, f,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )

    logger.info("Generated mkdocs.yml with %d nav entries", len(nav))
    return out_path


# ---------------------------------------------------------------------------
# Build & serve
# ---------------------------------------------------------------------------


def build_site(
    base_dir: Path | None = None,
) -> subprocess.CompletedProcess[str]:
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
            logger.info(
                "Site built successfully to %s/", config.output_dir
            )
        except FileNotFoundError:
            result["build_ok"] = False
            result["build_error"] = (
                "mkdocs not found. Install with: "
                "pip install mkdocs-material"
            )
        except subprocess.CalledProcessError as exc:
            result["build_ok"] = False
            result["build_error"] = exc.stderr or str(exc)
            logger.error("mkdocs build failed: %s", exc.stderr)

    return result


# ---------------------------------------------------------------------------
# Per-module remote deployment
# ---------------------------------------------------------------------------

_DEPLOY_WORKFLOW = """\
name: Deploy to GitHub Pages

on:
  push:
    branches: [main]
    paths:
      - "docs/**"
      - "mkdocs.yml"
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: "pages"
  cancel-in-progress: true

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
      - run: pip install mkdocs-material
      - run: mkdocs build
      - uses: actions/upload-pages-artifact@v3
        with:
          path: site

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
"""


def _build_module_nav(docs_dir: Path) -> list[Any]:
    """Build a nav tree for a single module's docs/ directory."""
    nav: list[Any] = []
    index = docs_dir / "index.md"
    if index.exists():
        nav.append({"Home": "index.md"})

    for entry in sorted(docs_dir.iterdir()):
        if not entry.is_dir():
            if entry.suffix == ".md" and entry.name != "index.md":
                label = (
                    _title_from_file(entry)
                    or entry.stem.replace("-", " ").title()
                )
                nav.append({label: entry.name})
            continue

        week_label = entry.name.replace("-", " ").title()
        week_nav: list[Any] = []
        for sf in sorted(entry.glob("*.md")):
            s_label = (
                _title_from_file(sf)
                or sf.stem.replace("-", " ").title()
            )
            week_nav.append({s_label: f"{entry.name}/{sf.name}"})
        if week_nav:
            nav.append({week_label: week_nav})

    return nav


def _generate_module_mkdocs(
    clone_dir: Path,
    mod_cfg: ModuleConfig,
    pub_cfg: PublishConfig,
) -> Path:
    """Write mkdocs.yml inside a cloned module repo."""
    docs_dir = clone_dir / "docs"
    nav = _build_module_nav(docs_dir)

    mkdocs_cfg: dict[str, Any] = {
        "site_name": mod_cfg.site_name,
        "docs_dir": "docs",
        "site_dir": "site",
        "theme": {
            "name": pub_cfg.theme,
            "palette": [
                {
                    "scheme": "default",
                    "primary": "indigo",
                    "toggle": {
                        "icon": "material/brightness-7",
                        "name": "Switch to dark mode",
                    },
                },
                {
                    "scheme": "slate",
                    "primary": "indigo",
                    "toggle": {
                        "icon": "material/brightness-4",
                        "name": "Switch to light mode",
                    },
                },
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

    if mod_cfg.site_url:
        mkdocs_cfg["site_url"] = mod_cfg.site_url
    if nav:
        mkdocs_cfg["nav"] = nav

    out_path = clone_dir / "mkdocs.yml"
    with open(out_path, "w", encoding="utf-8") as f:
        yaml.dump(
            mkdocs_cfg, f,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )
    return out_path


def deploy_module(
    mod_cfg: ModuleConfig,
    base_dir: Path | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Deploy a single module to its remote GitHub repo.

    Steps: clone -> copy docs -> generate mkdocs.yml -> add workflow -> commit -> push.
    """
    import tempfile

    root = base_dir or get_project_root()
    pub_cfg = PublishConfig(root)
    result: dict[str, Any] = {
        "module": mod_cfg.slug,
        "remote": mod_cfg.remote,
    }

    if not mod_cfg.has_remote:
        result["status"] = "skipped"
        result["reason"] = "no remote configured"
        return result

    source_dir = mod_cfg.module_dir
    md_files = [
        f for f in source_dir.rglob("*.md")
        if f.name not in _IGNORE_FILENAMES
    ]
    result["files"] = len(md_files)

    if not md_files:
        result["status"] = "skipped"
        result["reason"] = "no markdown files to deploy"
        return result

    if dry_run:
        result["status"] = "dry-run"
        result["would_deploy"] = [
            str(f.relative_to(source_dir)) for f in md_files
        ]
        return result

    with tempfile.TemporaryDirectory() as tmp:
        clone_dir = Path(tmp) / "repo"

        # Clone (try branch first, fall back to default)
        try:
            subprocess.run(
                [
                    "git", "clone", "--depth", "1",
                    "-b", mod_cfg.branch,
                    mod_cfg.remote, str(clone_dir),
                ],
                capture_output=True, text=True, check=True,
            )
        except subprocess.CalledProcessError:
            try:
                subprocess.run(
                    ["git", "clone", mod_cfg.remote, str(clone_dir)],
                    capture_output=True, text=True, check=True,
                )
            except subprocess.CalledProcessError as exc:
                result["status"] = "error"
                result["error"] = f"git clone failed: {exc.stderr}"
                return result

        # Clean existing docs/
        docs_dir = clone_dir / "docs"
        if docs_dir.is_dir():
            shutil.rmtree(docs_dir)
        docs_dir.mkdir(parents=True)

        # Copy markdown files preserving directory structure
        for md_file in md_files:
            rel = md_file.relative_to(source_dir)
            dest = docs_dir / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(md_file, dest)

        # Ensure index.md exists
        index_path = docs_dir / "index.md"
        if not index_path.exists():
            index_path.write_text(
                f"# {mod_cfg.site_name}\n\n"
                f"Welcome to the {mod_cfg.site_name} course book.\n",
                encoding="utf-8",
            )

        # Generate mkdocs.yml
        _generate_module_mkdocs(clone_dir, mod_cfg, pub_cfg)

        # Add GitHub Actions workflow
        wf_dir = clone_dir / ".github" / "workflows"
        wf_dir.mkdir(parents=True, exist_ok=True)
        (wf_dir / "deploy-pages.yml").write_text(
            _DEPLOY_WORKFLOW, encoding="utf-8",
        )

        # Git add, commit, push
        def _git(*args: str) -> subprocess.CompletedProcess[str]:
            return subprocess.run(
                ["git", *args],
                cwd=str(clone_dir),
                capture_output=True, text=True, check=True,
            )

        _git("add", "-A")

        status_proc = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(clone_dir),
            capture_output=True, text=True,
        )
        if not status_proc.stdout.strip():
            result["status"] = "up-to-date"
            return result

        _git("commit", "-m", f"Update {mod_cfg.site_name} content")

        try:
            _git("push", "origin", mod_cfg.branch)
            result["status"] = "deployed"
        except subprocess.CalledProcessError as exc:
            result["status"] = "error"
            result["error"] = f"git push failed: {exc.stderr}"

    return result


def deploy_all(
    base_dir: Path | None = None,
    module_filter: str | None = None,
    dry_run: bool = False,
) -> list[dict[str, Any]]:
    """Deploy all modules (or one) that have remotes configured."""
    root = base_dir or get_project_root()
    configs = list_module_configs(root)
    results: list[dict[str, Any]] = []

    for mod_cfg in configs:
        if module_filter and mod_cfg.slug != module_filter:
            continue
        if not mod_cfg.has_remote:
            logger.debug(
                "Skipping %s -- no remote configured", mod_cfg.slug,
            )
            continue
        logger.info(
            "Deploying module: %s -> %s",
            mod_cfg.slug, mod_cfg.remote,
        )
        r = deploy_module(mod_cfg, root, dry_run=dry_run)
        results.append(r)

    return results
