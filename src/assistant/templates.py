"""Jinja2 template engine for rendering prompts and markdown outputs."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from assistant.repo import get_project_root
from assistant.schemas import ContextDocument, SkillDefinition


def _create_env(base_dir: Path | None = None) -> Environment:
    """Create a Jinja2 environment rooted at the project directory."""
    root = base_dir or get_project_root()
    return Environment(
        loader=FileSystemLoader(str(root)),
        autoescape=select_autoescape([]),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def render_prompt(
    skill: SkillDefinition,
    input_text: str,
    context_documents: list[ContextDocument],
    metadata: dict[str, Any] | None = None,
    base_dir: Path | None = None,
) -> str:
    """Render a skill's prompt template with the provided context."""
    if not skill.prompt_template:
        raise ValueError(f"Skill '{skill.name}' has no prompt_template configured")

    env = _create_env(base_dir)
    template = env.get_template(skill.prompt_template)

    return template.render(
        skill=skill,
        input_text=input_text,
        context_documents=context_documents,
        metadata=metadata or {},
    )


def render_output(
    template_path: str,
    data: dict[str, Any],
    metadata: dict[str, Any] | None = None,
    source_file: str = "",
    base_dir: Path | None = None,
) -> str:
    """Render a markdown output template with structured data."""
    env = _create_env(base_dir)
    template = env.get_template(template_path)

    return template.render(
        data=data,
        metadata=metadata or {},
        source_file=source_file,
        today=date.today().isoformat(),
    )
