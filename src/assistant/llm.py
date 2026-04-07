"""LLM abstraction layer: thin wrapper around OpenAI SDK with usage tracking."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from openai import OpenAI
from pydantic import BaseModel

from assistant.repo import get_project_root
from assistant.schemas import UsageRecord

logger = logging.getLogger(__name__)

# Approximate pricing per 1M tokens (USD) — update as OpenAI changes prices
_PRICING: dict[str, tuple[float, float]] = {
    "gpt-4.1-nano": (0.10, 0.40),
    "gpt-4.1-mini": (0.40, 1.60),
    "gpt-4.1": (2.00, 8.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
}


def _estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate USD cost based on known pricing."""
    in_price, out_price = _PRICING.get(model, (0.15, 0.60))
    return (input_tokens * in_price + output_tokens * out_price) / 1_000_000


class LLMClient:
    """Stateless OpenAI wrapper that logs token usage."""

    def __init__(
        self,
        api_key: str | None = None,
        default_model: str = "gpt-4.1-nano",
        usage_log_path: Path | None = None,
    ):
        self._client = OpenAI(api_key=api_key)
        self._default_model = default_model
        self._usage_log_path = usage_log_path or (
            get_project_root() / "outputs" / ".usage_log.jsonl"
        )

    def complete(
        self,
        system_prompt: str,
        user_message: str,
        model: str | None = None,
        temperature: float = 0.2,
        response_format: type[BaseModel] | None = None,
    ) -> tuple[str, UsageRecord]:
        """Send a completion request and return (response_text, usage_record).

        If response_format is provided, uses OpenAI's structured output (JSON mode)
        to ensure the response validates against the given Pydantic model.
        """
        model = model or self._default_model
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }

        if response_format is not None:
            kwargs["response_format"] = {"type": "json_object"}

        response = self._client.chat.completions.create(**kwargs)

        choice = response.choices[0]
        content = choice.message.content or ""

        input_tokens = response.usage.prompt_tokens if response.usage else 0
        output_tokens = response.usage.completion_tokens if response.usage else 0

        usage = UsageRecord(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost_usd=_estimate_cost(model, input_tokens, output_tokens),
        )

        self._log_usage(usage)

        logger.info(
            "LLM call: model=%s, in=%d, out=%d, cost=$%.4f",
            model,
            input_tokens,
            output_tokens,
            usage.estimated_cost_usd,
        )

        return content, usage

    def _log_usage(self, usage: UsageRecord) -> None:
        """Append usage record to the JSONL log file."""
        try:
            self._usage_log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._usage_log_path, "a", encoding="utf-8") as f:
                f.write(usage.model_dump_json() + "\n")
        except Exception as exc:
            logger.warning("Failed to write usage log: %s", exc)
