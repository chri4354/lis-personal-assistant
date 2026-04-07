"""Notion integration: push structured tasks to a Notion database."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from assistant.repo import get_project_root
from assistant.schemas import TaskItem
from assistant.settings import get_settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


class NotionConfig:
    """Notion integration settings loaded from config + environment."""

    def __init__(self, base_dir: Path | None = None):
        root = base_dir or get_project_root()
        config_path = root / "config" / "notion.yaml"

        cfg: dict[str, Any] = {}
        if config_path.exists():
            with open(config_path, encoding="utf-8") as f:
                raw = yaml.safe_load(f) or {}
            cfg = raw.get("notion", {})

        settings = get_settings()

        self.api_key: str = settings.notion_api_key or ""
        self.database_id: str = settings.notion_task_db_id or cfg.get("task_database_id", "")
        self.enabled: bool = bool(self.api_key and self.database_id)

        self.property_map: dict[str, str] = cfg.get("property_map", {
            "title": "Title",
            "description": "Description",
            "deadline": "Deadline",
            "module": "Module",
            "source": "Source",
            "status": "Status",
        })

        self.status_options: dict[str, str] = cfg.get("status_options", {
            "todo": "Not started",
            "doing": "In progress",
            "done": "Done",
        })


# ---------------------------------------------------------------------------
# Task → Notion property mapping
# ---------------------------------------------------------------------------


def _build_page_properties(
    task: TaskItem,
    config: NotionConfig,
) -> dict[str, Any]:
    """Map a TaskItem to Notion page properties."""
    pm = config.property_map
    props: dict[str, Any] = {}

    # Title (required)
    props[pm.get("title", "Title")] = {
        "title": [{"text": {"content": task.title}}]
    }

    # Description
    if task.description:
        props[pm.get("description", "Description")] = {
            "rich_text": [{"text": {"content": task.description}}]
        }

    # Deadline
    if task.deadline:
        props[pm.get("deadline", "Deadline")] = {
            "date": {"start": task.deadline.isoformat()}
        }

    # Module
    if task.module:
        props[pm.get("module", "Module")] = {
            "select": {"name": task.module}
        }

    # Source file
    if task.source_file:
        props[pm.get("source", "Source")] = {
            "rich_text": [{"text": {"content": task.source_file}}]
        }

    # Status — uses Notion's "status" property type (not "select")
    status_name = config.status_options.get(task.status, task.status)
    props[pm.get("status", "Status")] = {
        "status": {"name": status_name}
    }

    return props


# ---------------------------------------------------------------------------
# Sync operations
# ---------------------------------------------------------------------------


class NotionSyncResult:
    """Result of a sync operation."""

    def __init__(self):
        self.created: list[str] = []
        self.skipped: list[str] = []
        self.errors: list[str] = []

    @property
    def summary(self) -> str:
        parts = []
        if self.created:
            parts.append(f"{len(self.created)} created")
        if self.skipped:
            parts.append(f"{len(self.skipped)} skipped (duplicates)")
        if self.errors:
            parts.append(f"{len(self.errors)} errors")
        return ", ".join(parts) or "nothing to sync"


def sync_tasks(
    tasks: list[TaskItem],
    source_file: str | None = None,
    dry_run: bool = False,
    base_dir: Path | None = None,
) -> NotionSyncResult:
    """Push a list of tasks to the configured Notion database.

    Args:
        tasks: List of TaskItem objects to sync.
        source_file: The source file path to attach to each task for traceability.
        dry_run: If True, log what would be created but don't actually call the API.
        base_dir: Project root override.

    Returns:
        NotionSyncResult with counts of created, skipped, and errored tasks.
    """
    result = NotionSyncResult()
    config = NotionConfig(base_dir)

    if not config.enabled:
        logger.warning(
            "Notion sync is disabled (missing NOTION_API_KEY or NOTION_TASK_DB_ID). "
            "Skipping sync."
        )
        result.errors.append("Notion sync not configured")
        return result

    from notion_client import Client

    client = Client(auth=config.api_key)

    # Fetch existing task titles for deduplication
    existing_titles = _fetch_existing_titles(client, config.database_id)

    for task in tasks:
        if source_file and not task.source_file:
            task.source_file = source_file

        # Deduplicate by title
        if task.title in existing_titles:
            logger.info("Skipping duplicate task: %s", task.title)
            result.skipped.append(task.title)
            continue

        if dry_run:
            logger.info("[DRY RUN] Would create task: %s", task.title)
            result.created.append(f"[dry-run] {task.title}")
            continue

        try:
            properties = _build_page_properties(task, config)
            client.pages.create(
                parent={"database_id": config.database_id},
                properties=properties,
            )
            logger.info("Created Notion task: %s", task.title)
            result.created.append(task.title)
            existing_titles.add(task.title)
        except Exception as exc:
            logger.error("Failed to create task '%s': %s", task.title, exc)
            result.errors.append(f"{task.title}: {exc}")

    return result


def _fetch_existing_titles(client: Any, database_id: str) -> set[str]:
    """Fetch existing task titles from the database for deduplication.

    Uses the raw request method since notion-client v3 removed databases.query().
    """
    titles: set[str] = set()
    try:
        response = client.request(
            path=f"databases/{database_id}/query",
            method="POST",
            body={"page_size": 100},
        )
        for page in response.get("results", []):
            props = page.get("properties", {})
            for prop_val in props.values():
                if prop_val.get("type") == "title":
                    title_parts = prop_val.get("title", [])
                    if title_parts:
                        titles.add(title_parts[0].get("plain_text", ""))
                    break
    except Exception as exc:
        logger.warning("Could not fetch existing tasks for deduplication: %s", exc)
    return titles


# ---------------------------------------------------------------------------
# Convenience: check if Notion is configured
# ---------------------------------------------------------------------------


def is_notion_configured(base_dir: Path | None = None) -> bool:
    """Check whether Notion credentials are set up."""
    config = NotionConfig(base_dir)
    return config.enabled
