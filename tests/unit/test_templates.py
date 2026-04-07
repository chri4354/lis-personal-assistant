"""Tests for the template engine."""

from pathlib import Path

from assistant.schemas import ContextDocument, SkillDefinition
from assistant.templates import render_output, render_prompt


def _create_minimal_skill(template_dir: Path) -> tuple[SkillDefinition, Path]:
    """Create a minimal skill and prompt template for testing."""
    prompt_path = "templates/prompts/test_skill.j2"
    (template_dir / "templates" / "prompts").mkdir(parents=True, exist_ok=True)
    (template_dir / prompt_path).write_text(
        "Rules:\n{% for rule in skill.rules %}- {{ rule }}\n{% endfor %}\n"
        "Input: {{ input_text }}\n"
        "{% if context_documents %}Context: {{ context_documents | length }} docs{% endif %}"
    )

    skill = SkillDefinition(
        name="test_skill",
        description="A test skill",
        input_type="text",
        prompt_template=prompt_path,
        rules=["Rule one", "Rule two"],
    )
    return skill, template_dir


def test_render_prompt(tmp_path: Path):
    """Render a prompt template with skill rules and input."""
    skill, base = _create_minimal_skill(tmp_path)

    result = render_prompt(
        skill=skill,
        input_text="Hello world",
        context_documents=[],
        base_dir=base,
    )

    assert "Rule one" in result
    assert "Rule two" in result
    assert "Hello world" in result


def test_render_prompt_with_context(tmp_path: Path):
    """Render a prompt with context documents injected."""
    skill, base = _create_minimal_skill(tmp_path)

    docs = [
        ContextDocument(
            title="Test Doc",
            path="knowledge/test.md",
            content="Some content",
        )
    ]

    result = render_prompt(
        skill=skill,
        input_text="test input",
        context_documents=docs,
        base_dir=base,
    )

    assert "Context: 1 docs" in result


def test_render_output(tmp_path: Path):
    """Render a markdown output template."""
    output_template = "templates/outputs/test_output.md"
    (tmp_path / "templates" / "outputs").mkdir(parents=True, exist_ok=True)
    (tmp_path / output_template).write_text(
        "# {{ data.title }}\n\n{{ data.body }}\n\nSource: {{ source_file }}"
    )

    result = render_output(
        template_path=output_template,
        data={"title": "Test Title", "body": "Test body content"},
        source_file="inbox/test.md",
        base_dir=tmp_path,
    )

    assert "# Test Title" in result
    assert "Test body content" in result
    assert "inbox/test.md" in result
