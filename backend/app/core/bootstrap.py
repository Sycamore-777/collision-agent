"""Startup helpers for directory and schema initialization."""

from __future__ import annotations

from pathlib import Path

from app.core.config import get_settings
from app.core.database import get_engine
from app.models import Base


def ensure_runtime_directories() -> None:
    """Create all configured runtime directories if they do not exist."""

    settings = get_settings()
    for raw_path in [
        settings.data_dir,
        settings.upload_dir,
        settings.parsed_dir,
        settings.report_dir,
        settings.trace_dir,
        settings.mock_dir,
        settings.prompt_dir,
    ]:
        Path(raw_path).mkdir(parents=True, exist_ok=True)


def ensure_database_schema() -> None:
    """Create database tables for local development and tests."""

    Base.metadata.create_all(bind=get_engine())
