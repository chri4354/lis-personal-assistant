"""Tests for the Notion sync module."""

import datetime
from unittest.mock import MagicMock, patch

from assistant.notion_sync import (
    NotionConfig,
    NotionSyncResult,
    _build_page_properties,
    sync_tasks,
)
from assistant.schemas import TaskItem


def _make_task(**kwargs) -> TaskItem:
    defaults = {"title": "Test task", "description": "Do something", "status": "todo"}
    defaults.update(kwargs)
    return TaskItem(**defaults)


def test_build_page_properties_basic():
    """Build Notion properties from a simple task."""
    config = NotionConfig.__new__(NotionConfig)
    config.property_map = {
        "title": "Title",
        "description": "Description",
        "deadline": "Deadline",
        "module": "Module",
        "source": "Source",
        "status": "Status",
    }
    config.status_options = {"todo": "todo", "doing": "doing", "done": "done"}

    task = _make_task(title="Review rubric", module="AI-CI")
    props = _build_page_properties(task, config)

    assert props["Title"]["title"][0]["text"]["content"] == "Review rubric"
    assert props["Description"]["rich_text"][0]["text"]["content"] == "Do something"
    assert props["Module"]["select"]["name"] == "AI-CI"
    assert props["Status"]["select"]["name"] == "todo"


def test_build_page_properties_with_deadline():
    """Build Notion properties including a deadline."""
    config = NotionConfig.__new__(NotionConfig)
    config.property_map = {
        "title": "Title",
        "description": "Description",
        "deadline": "Deadline",
        "module": "Module",
        "source": "Source",
        "status": "Status",
    }
    config.status_options = {"todo": "todo"}

    task = _make_task(
        title="Submit brief",
        deadline=datetime.date(2026, 4, 10),
    )
    props = _build_page_properties(task, config)

    assert props["Deadline"]["date"]["start"] == "2026-04-10"


def test_build_page_properties_with_source():
    """Source file is included in properties."""
    config = NotionConfig.__new__(NotionConfig)
    config.property_map = {
        "title": "Title",
        "description": "Description",
        "deadline": "Deadline",
        "module": "Module",
        "source": "Source",
        "status": "Status",
    }
    config.status_options = {"todo": "todo"}

    task = _make_task(source_file="outputs/meetings/2026-04-01-meeting.md")
    props = _build_page_properties(task, config)

    assert "outputs/meetings" in props["Source"]["rich_text"][0]["text"]["content"]


def test_sync_tasks_not_configured(tmp_path):
    """sync_tasks returns an error when Notion is not configured."""
    # Create minimal config
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "notion.yaml").write_text("notion:\n  enabled: false\n")

    tasks = [_make_task()]

    with patch("assistant.notion_sync.get_settings") as mock_settings:
        mock_settings.return_value = MagicMock(
            notion_api_key="",
            notion_task_db_id="",
        )
        result = sync_tasks(tasks, base_dir=tmp_path)

    assert len(result.errors) > 0
    assert "not configured" in result.errors[0]


def test_notion_sync_result_summary():
    """NotionSyncResult generates a human-readable summary."""
    result = NotionSyncResult()
    result.created.append("Task A")
    result.created.append("Task B")
    result.skipped.append("Task C")

    assert "2 created" in result.summary
    assert "1 skipped" in result.summary
