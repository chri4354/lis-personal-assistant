"""Tests for Pydantic schemas."""

import datetime

from assistant.schemas import (
    EmailDraft,
    MeetingSummary,
    SkillDefinition,
    TaskItem,
)


def test_meeting_summary_parses():
    """MeetingSummary validates a well-formed dict."""
    data = {
        "title": "Planning Meeting",
        "date": "2026-04-01",
        "summary": ["Discussed timeline"],
        "decisions": ["Publish brief by Friday"],
        "actions": [
            {
                "title": "Review rubric",
                "description": "Align with learning outcomes",
                "assignee": "James",
                "deadline": "2026-04-08",
                "module": "AI-CI",
                "status": "todo",
            }
        ],
        "open_questions": ["Extend Week 6?"],
    }
    ms = MeetingSummary(**data)
    assert ms.title == "Planning Meeting"
    assert len(ms.actions) == 1
    assert ms.actions[0].assignee == "James"
    assert ms.actions[0].deadline == datetime.date(2026, 4, 8)


def test_email_draft_parses():
    """EmailDraft validates a well-formed dict."""
    data = {
        "subject_suggestion": "Re: Extension request",
        "body": "Thank you for your email...",
        "grounding_sources": ["knowledge/policies/extensions.md"],
        "warnings": ["Student should apply via mitigating circumstances"],
    }
    ed = EmailDraft(**data)
    assert "Extension" in ed.subject_suggestion
    assert len(ed.warnings) == 1


def test_skill_definition_from_dict():
    """SkillDefinition loads from a dict (simulating YAML parse)."""
    raw = {
        "name": "meeting_to_actions",
        "description": "Process meeting transcripts",
        "input_type": "transcript",
        "source_scopes": ["knowledge/modules"],
        "rules": ["Do not invent deadlines"],
    }
    sd = SkillDefinition(**raw)
    assert sd.name == "meeting_to_actions"
    assert len(sd.rules) == 1


def test_task_item_defaults():
    """TaskItem has sensible defaults."""
    task = TaskItem(title="Do something")
    assert task.status == "todo"
    assert task.deadline is None
    assert task.assignee is None
