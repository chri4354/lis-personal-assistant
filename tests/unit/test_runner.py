"""Tests for the skill runner with a mock LLM client."""

import json
from unittest.mock import MagicMock

from assistant.llm import LLMClient
from assistant.runner import list_skills, load_skill, run_skill
from assistant.schemas import InputMetadata, UsageRecord


def _make_mock_llm(response_data: dict) -> LLMClient:
    """Create a mock LLM client that returns a fixed JSON response."""
    mock = MagicMock(spec=LLMClient)
    usage = UsageRecord(
        model="gpt-4.1-nano",
        input_tokens=100,
        output_tokens=50,
        estimated_cost_usd=0.0001,
    )
    mock.complete.return_value = (json.dumps(response_data), usage)
    return mock


def test_load_skill():
    """Load a skill definition from the project's skills/ directory."""
    skill = load_skill("meeting_to_actions")
    assert skill.name == "meeting_to_actions"
    assert skill.input_type == "transcript"
    assert len(skill.rules) > 0


def test_list_skills_returns_all():
    """list_skills returns all 5 skill definitions."""
    skills = list_skills()
    names = [s.name for s in skills]
    assert "meeting_to_actions" in names
    assert "email_reply" in names
    assert "lecture_to_page" in names
    assert "weekly_comm" in names
    assert "notion_sync" in names


def test_run_meeting_skill_with_mock_llm():
    """Run meeting_to_actions with a mock LLM and verify output is written."""
    mock_response = {
        "title": "Test Meeting",
        "date": "2026-04-01",
        "summary": ["Discussed the plan"],
        "decisions": ["Go ahead"],
        "actions": [
            {
                "title": "Write tests",
                "description": "Add unit tests",
                "assignee": "Dev",
                "deadline": None,
                "module": None,
                "status": "todo",
            }
        ],
        "open_questions": [],
    }
    mock_llm = _make_mock_llm(mock_response)

    result = run_skill(
        skill_name="meeting_to_actions",
        input_text="Sample meeting transcript text.",
        metadata=InputMetadata(module="AI and Collective Intelligence"),
        llm_client=mock_llm,
    )

    assert result.skill_name == "meeting_to_actions"
    assert result.output_data["title"] == "Test Meeting"
    assert result.output_file is not None
    assert result.output_file.endswith(".md")
    assert result.usage is not None
    assert result.usage.model == "gpt-4.1-nano"

    # Verify the file was actually written
    from assistant.repo import get_project_root

    output_path = get_project_root() / result.output_file
    assert output_path.exists()
    content = output_path.read_text()
    assert "Test Meeting" in content

    # Cleanup
    output_path.unlink()


def test_run_email_skill_with_mock_llm():
    """Run email_reply with a mock LLM."""
    mock_response = {
        "subject_suggestion": "Re: Extension request",
        "body": "Thank you for reaching out. Extensions are handled via mitigating circumstances.",
        "grounding_sources": ["knowledge/policies/extensions.md"],
        "warnings": [],
    }
    mock_llm = _make_mock_llm(mock_response)

    result = run_skill(
        skill_name="email_reply",
        input_text="Dear team, can I get an extension?",
        llm_client=mock_llm,
    )

    assert result.skill_name == "email_reply"
    assert "Extension" in result.output_data["subject_suggestion"]
    assert result.output_file is not None

    # Cleanup
    from assistant.repo import get_project_root

    output_path = get_project_root() / result.output_file
    if output_path.exists():
        output_path.unlink()
