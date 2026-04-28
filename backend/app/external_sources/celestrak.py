"""CelesTrak client with local mock fallback."""

from __future__ import annotations

import json
from pathlib import Path

import httpx

from app.core.config import get_settings


class CelesTrakClient:
    """Retrieve orbital context, preferring remote data but falling back locally."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.mock_path = Path(self.settings.mock_dir) / "celestrak_context.json"

    def fetch_context(self, norad_id: str | None) -> dict:
        if not norad_id:
            return {"source": "none", "context": None}

        if self.settings.enable_external_context:
            try:
                response = httpx.get(
                    f"{self.settings.celestrak_base_url}/NORAD/elements/gp.php",
                    params={"CATNR": norad_id, "FORMAT": "JSON"},
                    timeout=10.0,
                )
                response.raise_for_status()
                payload = response.json()
                if payload:
                    return {"source": "celestrak", "context": payload[0] if isinstance(payload, list) else payload}
            except Exception:
                pass

        if self.mock_path.exists():
            payload = json.loads(self.mock_path.read_text(encoding="utf-8"))
            return {"source": "mock", "context": payload.get(str(norad_id))}

        return {"source": "degraded", "context": None}

