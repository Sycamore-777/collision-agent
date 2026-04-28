"""Shared pytest fixtures for backend tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import clear_settings_cache
from app.core.database import reset_database_caches


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    data_dir = tmp_path / "data"
    uploads_dir = data_dir / "uploads"
    parsed_dir = data_dir / "parsed"
    reports_dir = data_dir / "reports"
    traces_dir = data_dir / "traces"

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{(tmp_path / 'app.db').as_posix()}")
    monkeypatch.setenv("DATA_DIR", str(data_dir))
    monkeypatch.setenv("UPLOAD_DIR", str(uploads_dir))
    monkeypatch.setenv("PARSED_DIR", str(parsed_dir))
    monkeypatch.setenv("REPORT_DIR", str(reports_dir))
    monkeypatch.setenv("TRACE_DIR", str(traces_dir))
    monkeypatch.setenv("MOCK_DIR", str(PROJECT_ROOT / "data" / "mock"))
    monkeypatch.setenv("ENABLE_EXTERNAL_CONTEXT", "false")
    monkeypatch.setenv("ENABLE_LLM_SUGGESTION", "true")
    monkeypatch.setenv("LLM_ENABLED", "false")

    clear_settings_cache()
    reset_database_caches()

    from app.main import create_app

    with TestClient(create_app()) as test_client:
        yield test_client

    clear_settings_cache()
    reset_database_caches()


@pytest.fixture()
def sample_event_payload() -> dict:
    return json.loads((PROJECT_ROOT / "data" / "mock" / "cdm_clean.json").read_text(encoding="utf-8"))

