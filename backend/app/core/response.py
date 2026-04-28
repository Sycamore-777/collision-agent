"""API response helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def utcnow() -> datetime:
    """Return a timezone-aware UTC timestamp."""

    return datetime.now(timezone.utc)


def success_response(data: Any, *, message: str = "ok") -> dict[str, Any]:
    """Return the standard API success envelope."""

    return {
        "success": True,
        "message": message,
        "data": data,
        "error": None,
        "timestamp": utcnow().isoformat(),
    }


def error_response(
    message: str,
    *,
    code: str,
    details: Any | None = None,
) -> dict[str, Any]:
    """Return the standard API error envelope."""

    return {
        "success": False,
        "message": message,
        "data": None,
        "error": {
            "code": code,
            "details": details,
        },
        "timestamp": utcnow().isoformat(),
    }

