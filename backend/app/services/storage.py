"""File storage helpers for uploads, parsed artifacts, and reports."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.core.config import get_settings


class StorageService:
    """Manage runtime files under the configured data directories."""

    def __init__(self) -> None:
        self.settings = get_settings()

    def _resolve(self, directory: str, filename: str) -> Path:
        target = Path(directory) / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    def compute_sha256(self, payload: bytes) -> str:
        digest = hashlib.sha256()
        digest.update(payload)
        return digest.hexdigest()

    def save_upload(self, source_name: str, payload: bytes) -> tuple[str, str]:
        suffix = Path(source_name).suffix or ".bin"
        file_name = f"{uuid4().hex}{suffix}"
        target = self._resolve(self.settings.upload_dir, file_name)
        target.write_bytes(payload)
        return str(target), self.compute_sha256(payload)

    def save_text(self, directory: str, prefix: str, content: str, suffix: str = ".txt") -> str:
        target = self._resolve(directory, f"{prefix}_{uuid4().hex}{suffix}")
        target.write_text(content, encoding="utf-8")
        return str(target)

    def save_named_text(self, directory: str, filename: str, content: str) -> str:
        target = self._resolve(directory, filename)
        target.write_text(content, encoding="utf-8")
        return str(target)

    def save_json(self, directory: str, prefix: str, payload: Any) -> str:
        target = self._resolve(directory, f"{prefix}_{uuid4().hex}.json")
        target.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        return str(target)

    def save_named_json(self, directory: str, filename: str, payload: Any) -> str:
        target = self._resolve(directory, filename)
        target.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        return str(target)

    def read_json(self, path: str) -> Any:
        return json.loads(Path(path).read_text(encoding="utf-8"))

    def read_text(self, path: str) -> str:
        return Path(path).read_text(encoding="utf-8")
