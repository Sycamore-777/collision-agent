"""Common API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, Field


T = TypeVar("T")


class ApiErrorDetail(BaseModel):
    """Standard error payload."""

    code: str
    details: dict | list | str | None = None


class ApiEnvelope(BaseModel, Generic[T]):
    """Standard envelope for all API responses."""

    success: bool = True
    message: str = "ok"
    data: T | None = None
    error: ApiErrorDetail | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class Pagination(BaseModel):
    """Simple pagination metadata."""

    total: int
    page: int = 1
    page_size: int = 50

