"""Application settings loaded from environment variables and config files."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-nano"
    notion_api_key: str = ""
    notion_task_db_id: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


def load_app_config(base_dir: Path | None = None) -> dict:
    """Load config/app.yaml as a dict."""
    from assistant.repo import get_project_root

    root = base_dir or get_project_root()
    config_path = root / "config" / "app.yaml"
    if not config_path.exists():
        return {}
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


_settings: Settings | None = None


def get_settings() -> Settings:
    """Get or create the singleton settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
