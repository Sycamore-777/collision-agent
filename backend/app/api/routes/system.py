"""System routes for health and metrics."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import db_session
from app.core.response import success_response
from app.models.records import TaskRecord

router = APIRouter(tags=["system"])


@router.get("/healthz")
def healthz():
    return success_response({"status": "ok"}, message="healthy")


@router.get("/metrics", response_class=PlainTextResponse)
def metrics(session: Session = Depends(db_session)) -> str:
    total_tasks = session.scalar(select(func.count()).select_from(TaskRecord)) or 0
    by_status = {
        status: session.scalar(select(func.count()).select_from(TaskRecord).where(TaskRecord.status == status)) or 0
        for status in ["pending", "running", "succeeded", "failed", "manual_review"]
    }
    lines = [f"collision_agent_tasks_total {total_tasks}"]
    lines.extend(f'collision_agent_tasks_status{{status="{status}"}} {count}' for status, count in by_status.items())
    return "\n".join(lines)

