"""Reusable API dependencies."""

from __future__ import annotations

from typing import Generator

from sqlalchemy.orm import Session

from app.core.database import get_db_session


def db_session() -> Generator[Session, None, None]:
    """Proxy dependency for database sessions."""

    yield from get_db_session()

