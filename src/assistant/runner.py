"""Skill runner: orchestrates retrieval → prompt → LLM → validation → output writing."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import yaml
from pydantic import ValidationError

from assistant.llm import LLMClient
from assistant.repo import (
    generate_output_filename,
    get_project_root,
    resolve_output_path,
    write_text,
)
from assistant.retrieval import retrieve_context
from assistant.schemas import (
    SKILL_OUTPUT_MODELS,
    InputMetadata,
    SkillDefinition,
    SkillResult,
)
from assistant.templates import render_output, render_prompt

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Skill loading
# ---------------------------------------------------------------------------


def load_skill(skill_name: str, base_dir: Path | None = None) -> SkillDefinition:
    """Load a skill definition from its YAML file."""
    root = base_dir or get_project_root()
    skill_path = root / "skills" / f"{skill_name}.yaml"

    if not skill_path.exists():
        raise FileNotFoundError(f"Skill not found: {skill_path}")

    with open(skill_path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    return SkillDefinition(**raw)


def list_skills(base_dir: Path | None = None) -> list[SkillDefinition]:
    """List all available skill definitions."""
    root = base_dir or get_project_root()
    skills_dir = root / "skills"
    if not skills_dir.is_dir():
        return []

    results = []
    for path in sorted(skills_dir.glob("*.yaml")):
        try:
            with open(path, encoding="utf-8") as f:
                raw = yaml.safe_load(f)
            results.append(SkillDefinition(**raw))
        except Exception as exc:
            logger.warning("Failed to load skill %s: %s", path.name, exc)
    return results


# ---------------------------------------------------------------------------
# Skill execution
# ---------------------------------------------------------------------------


def run_skill(
    skill_name: str,
    input_text: str,
    metadata: InputMetadata | None = None,
    llm_client: LLMClient | None = None,
    base_dir: Path | None = None,
) -> SkillResult:
    """Execute a skill end-to-end: retrieve → prompt → LLM → validate → write.

    Returns a SkillResult with the structured output, file path, and usage stats.
    """
    root = base_dir or get_project_root()
    skill = load_skill(skill_name, root)

    meta_dict = metadata.model_dump(exclude_none=True) if metadata else {}

    # 1. Retrieve context documents
    context_docs = retrieve_context(
        base_dir=root,
        source_scopes=skill.source_scopes,
        input_text=input_text,
        module=meta_dict.get("module"),
        module_code=meta_dict.get("module_code"),
    )

    logger.info(
        "Retrieved %d context documents for skill '%s'",
        len(context_docs),
        skill_name,
    )

    # 2. Render prompt
    prompt = render_prompt(
        skill=skill,
        input_text=input_text,
        context_documents=context_docs,
        metadata=meta_dict,
        base_dir=root,
    )

    # 3. Call LLM
    if llm_client is None:
        llm_client = LLMClient()

    output_model = SKILL_OUTPUT_MODELS.get(skill_name)

    llm_model = skill.llm.model  # None → client uses its default
    llm_temp = skill.llm.temperature if skill.llm.temperature is not None else 0.2

    raw_response, usage = llm_client.complete(
        system_prompt="You are a helpful assistant. Respond only with valid JSON.",
        user_message=prompt,
        model=llm_model,
        temperature=llm_temp,
        response_format=output_model,
    )

    # 4. Parse and validate output
    warnings: list[str] = []
    try:
        output_data = json.loads(raw_response)
    except json.JSONDecodeError as exc:
        logger.error("LLM returned invalid JSON: %s", exc)
        return SkillResult(
            skill_name=skill_name,
            output_data={"raw_response": raw_response},
            usage=usage,
            warnings=[f"LLM returned invalid JSON: {exc}"],
        )

    if output_model:
        try:
            validated = output_model(**output_data)
            output_data = validated.model_dump(mode="json")
        except ValidationError as exc:
            logger.warning("Output validation had issues: %s", exc)
            warnings.append(f"Output validation warnings: {exc}")

    # 5. Write markdown output
    output_file: str | None = None
    md_output_cfg = skill.outputs.get("markdown_note")
    if md_output_cfg and md_output_cfg.template:
        filename = generate_output_filename(skill_name, meta_dict)
        output_path = resolve_output_path(root, md_output_cfg.path, filename)

        rendered_md = render_output(
            template_path=md_output_cfg.template,
            data=output_data,
            metadata=meta_dict,
            source_file="(pasted input)",
            base_dir=root,
        )

        write_text(output_path, rendered_md)
        output_file = str(output_path.relative_to(root))
        logger.info("Wrote output to %s", output_file)

    return SkillResult(
        skill_name=skill_name,
        output_data=output_data,
        output_file=output_file,
        usage=usage,
        warnings=warnings,
    )
