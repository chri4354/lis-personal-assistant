"""Pydantic models for all data contracts: skill definitions, inputs, and structured outputs."""

import datetime
from typing import Any

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Skill definition (loaded from YAML)
# ---------------------------------------------------------------------------


class SkillOutputConfig(BaseModel):
    path: str | None = None
    template: str | None = None
    enabled: bool = True


class SkillLLMConfig(BaseModel):
    model: str | None = None
    temperature: float | None = None


class SkillDefinition(BaseModel):
    name: str
    description: str
    input_type: str
    input_location: str | None = None
    source_scopes: list[str] = Field(default_factory=list)
    outputs: dict[str, SkillOutputConfig] = Field(default_factory=dict)
    prompt_template: str | None = None
    llm: SkillLLMConfig = Field(default_factory=SkillLLMConfig)
    rules: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Metadata passed alongside user input
# ---------------------------------------------------------------------------


class InputMetadata(BaseModel):
    module: str | None = None
    module_code: str | None = None
    date: datetime.date | None = None
    week: int | None = None
    session: int | None = None


# ---------------------------------------------------------------------------
# Context document (retrieved for grounding)
# ---------------------------------------------------------------------------


class ContextDocument(BaseModel):
    title: str
    path: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Structured outputs
# ---------------------------------------------------------------------------


class TaskItem(BaseModel):
    title: str
    description: str = ""
    assignee: str | None = None
    deadline: datetime.date | None = None
    module: str | None = None
    source_file: str | None = None
    status: str = "todo"


class MeetingSummary(BaseModel):
    title: str
    date: datetime.date | None = None
    summary: list[str] = Field(default_factory=list)
    decisions: list[str] = Field(default_factory=list)
    actions: list[TaskItem] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)


class EmailDraft(BaseModel):
    subject_suggestion: str
    body: str
    grounding_sources: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class LecturePage(BaseModel):
    title: str
    overview: str = ""
    key_concepts: list[str] = Field(default_factory=list)
    examples: list[str] = Field(default_factory=list)
    questions_raised: list[str] = Field(default_factory=list)
    clarifications: list[str] = Field(default_factory=list)
    further_reading: list[str] = Field(default_factory=list)


class WeeklyComm(BaseModel):
    subject: str
    body: str
    deadlines_mentioned: list[str] = Field(default_factory=list)
    sources_used: list[str] = Field(default_factory=list)


class QuickCapture(BaseModel):
    summary: str
    actions: list[TaskItem] = Field(default_factory=list)


# Map skill names to their output model for validation
SKILL_OUTPUT_MODELS: dict[str, type[BaseModel]] = {
    "meeting_to_actions": MeetingSummary,
    "email_reply": EmailDraft,
    "lecture_to_page": LecturePage,
    "weekly_comm": WeeklyComm,
    "quick_capture": QuickCapture,
}

# ---------------------------------------------------------------------------
# Skill execution result
# ---------------------------------------------------------------------------


class UsageRecord(BaseModel):
    model: str
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float
    timestamp: datetime.datetime = Field(default_factory=datetime.datetime.now)


class SkillResult(BaseModel):
    skill_name: str
    output_data: dict[str, Any]
    output_file: str | None = None
    usage: UsageRecord | None = None
    warnings: list[str] = Field(default_factory=list)
