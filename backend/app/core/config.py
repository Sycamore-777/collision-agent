"""Application settings loaded from environment variables."""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        enable_decoding=False,
    )

    app_env: str = "dev"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"
    allowed_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )

    database_url: str = "sqlite:///./data/app.db"

    data_dir: str = "./data"
    upload_dir: str = "./data/uploads"
    parsed_dir: str = "./data/parsed"
    report_dir: str = "./data/reports"
    trace_dir: str = "./data/traces"
    mock_dir: str = "./data/mock"
    prompt_dir: str = "./prompts"

    celestrak_base_url: str = "https://celestrak.org"
    space_track_enabled: bool = False
    space_track_base_url: str = ""
    space_track_username: str = ""
    space_track_password: str = ""

    parser_backend: Literal["mock", "mineru", "native"] = "mock"
    mineru_base_url: str = ""
    mineru_api_key: str = ""
    mineru_timeout: int = 120

    llm_enabled: bool = True
    llm_provider: str = "openai_compatible"
    model_name: str = ""
    base_url: str = ""
    api_key: str = ""
    llm_temperature: float = 0.2
    llm_max_tokens: int = 2048
    llm_timeout: int = 120
    llm_top_p: float = 1.0
    llm_model_for_action: str = ""
    llm_model_for_summary: str = ""
    llm_model_for_report: str = ""
    llm_model_for_review: str = ""

    prompt_lang: str = "zh-CN"
    prompt_strict_json: bool = True

    enable_external_context: bool = True
    enable_llm_suggestion: bool = True
    enable_report_generation: bool = True
    enable_manual_review_route: bool = True

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, value: Any) -> Any:
        """Accept JSON arrays, comma-separated strings, or a single origin."""

        if isinstance(value, list):
            return value
        if isinstance(value, str):
            trimmed = value.strip()
            if not trimmed:
                return []
            if trimmed.startswith("["):
                try:
                    parsed = json.loads(trimmed)
                except json.JSONDecodeError:
                    parsed = None
                if isinstance(parsed, list):
                    return parsed
            return [item.strip() for item in trimmed.split(",") if item.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings object."""

    return Settings()


def clear_settings_cache() -> None:
    """Reset cached settings for tests."""

    get_settings.cache_clear()
