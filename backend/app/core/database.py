"""Database helpers with lazy engine creation for tests and local runs."""

from __future__ import annotations

from contextlib import contextmanager
from functools import lru_cache
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


def _connect_args(database_url: str) -> dict[str, object]:
    if database_url.startswith("sqlite"):
        return {"check_same_thread": False}

    return {}


@lru_cache
def get_engine(database_url: str | None = None) -> Engine:
    """Create or reuse the SQLAlchemy engine."""

    resolved_url = database_url or get_settings().database_url
    return create_engine(
        resolved_url,
        future=True,
        pool_pre_ping=True,
        connect_args=_connect_args(resolved_url),
    )


@lru_cache
def get_session_factory(database_url: str | None = None) -> sessionmaker[Session]:
    """Create a reusable session factory."""

    return sessionmaker(
        bind=get_engine(database_url),
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        class_=Session,
    )


def reset_database_caches() -> None:
    """Reset lazy database caches used in tests."""

    get_session_factory.cache_clear()
    get_engine.cache_clear()


def get_db_session() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a scoped database session."""

    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Provide a transactional scope for background workflows."""

    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

