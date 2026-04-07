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
    read_markdown,
    resolve_output_path,
    write_text,
)
from assistant.retrieval import retrieve_context
from assistant.schemas import (
    SKILL_OUTPUT_MODELS,
    InputMetadata,
    SkillDefinition,
    SkillResult,
    TaskItem,
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
# Input loading
# ---------------------------------------------------------------------------


def load_input(
    input_path: Path,
    base_dir: Path | None = None,
) -> tuple[str, InputMetadata]:
    """Load input text and metadata from a markdown file.

    Returns (body_text, metadata) where metadata is extracted from frontmatter.
    """
    meta_raw, body = read_markdown(input_path)

    metadata = InputMetadata(
        module=meta_raw.get("module"),
        module_code=meta_raw.get("module_code"),
        date=meta_raw.get("date"),
        week=meta_raw.get("week"),
        session=meta_raw.get("session"),
    )

    return body, metadata


# ---------------------------------------------------------------------------
# Skill execution
# ---------------------------------------------------------------------------


def run_skill(
    skill_name: str,
    input_text: str,
    metadata: InputMetadata | None = None,
    source_file: str | None = None,
    llm_client: LLMClient | None = None,
    base_dir: Path | None = None,
) -> SkillResult:
    """Execute a skill end-to-end: retrieve → prompt → LLM → validate → write.

    Returns a SkillResult with the structured output, file path, and usage stats.
    """
    root = base_dir or get_project_root()
    skill = load_skill(skill_name, root)

    if not skill.prompt_template:
        raise ValueError(
            f"Skill '{skill_name}' has no prompt_template and cannot be run directly. "
            f"It may be an integration skill (e.g. notion_sync) triggered by other skills."
        )

    meta_dict = metadata.model_dump(exclude_none=True) if metadata else {}
    source_label = source_file or "(pasted input)"

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
    if md_output_cfg and md_output_cfg.path and md_output_cfg.template:
        filename = generate_output_filename(skill_name, meta_dict)
        output_path = resolve_output_path(root, md_output_cfg.path, filename)

        rendered_md = render_output(
            template_path=md_output_cfg.template,
            data=output_data,
            metadata=meta_dict,
            source_file=source_label,
            base_dir=root,
        )

        write_text(output_path, rendered_md)
        output_file = str(output_path.relative_to(root))
        logger.info("Wrote output to %s", output_file)

        # Save structured data as companion JSON for downstream use (e.g. notion sync)
        json_path = output_path.with_suffix(".json")
        write_text(json_path, json.dumps(output_data, indent=2, default=str) + "\n")
        logger.debug("Wrote companion JSON to %s", json_path.name)

    # 6. Auto-sync tasks to Notion if skill produces actions and notion_tasks is enabled
    notion_output_cfg = skill.outputs.get("notion_tasks")
    if notion_output_cfg and notion_output_cfg.enabled and "actions" in output_data:
        try:
            from assistant.notion_sync import is_notion_configured, sync_tasks

            if is_notion_configured(root):
                tasks = [TaskItem(**a) for a in output_data["actions"]]
                if tasks:
                    sync_result = sync_tasks(
                        tasks=tasks,
                        source_file=output_file or source_label,
                        base_dir=root,
                    )
                    logger.info("Notion sync: %s", sync_result.summary)
                    if sync_result.errors:
                        warnings.extend(
                            f"Notion: {e}" for e in sync_result.errors
                        )
            else:
                logger.debug("Notion not configured, skipping task sync")
        except Exception as exc:
            logger.warning("Notion sync failed: %s", exc)
            warnings.append(f"Notion sync failed: {exc}")

    return SkillResult(
        skill_name=skill_name,
        output_data=output_data,
        output_file=output_file,
        usage=usage,
        warnings=warnings,
    )
