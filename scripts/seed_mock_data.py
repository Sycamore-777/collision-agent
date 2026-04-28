"""Ensure mock data assets exist for demos and tests."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MOCK_DIR = ROOT / "data" / "mock"


def main() -> None:
    MOCK_DIR.mkdir(parents=True, exist_ok=True)
    assets = sorted(path.name for path in MOCK_DIR.glob("*") if path.is_file())
    print(json.dumps({"mock_dir": str(MOCK_DIR), "assets": assets}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

