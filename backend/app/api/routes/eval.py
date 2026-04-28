"""Evaluation endpoint backed by local mock data."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import db_session
from app.core.config import get_settings
from app.core.response import success_response
from app.orchestrator.runner import TaskRunner
from app.schemas.task import TaskOptions
from app.services.task_service import TaskService

router = APIRouter(prefix="/v1/eval", tags=["evaluation"])
task_service = TaskService()


@router.post("/run")
def run_eval(session: Session = Depends(db_session)):
    settings = get_settings()
    clean_path = Path(settings.mock_dir) / "cdm_clean.json"
    constraint_path = Path(settings.mock_dir) / "mission_constraints.json"
    uploads = [
        UploadFile(filename=clean_path.name, file=BytesIO(clean_path.read_bytes())),
    ]
    if constraint_path.exists():
        uploads.append(
            UploadFile(filename=constraint_path.name, file=BytesIO(constraint_path.read_bytes()))
        )
    background_tasks = BackgroundTasks()
    response = task_service.create_task(
        session,
        background_tasks,
        task_type="collision_warning_eval",
        options=TaskOptions(),
        uploaded_files=uploads,
        inline_payload=None,
        enqueue_runner=False,
    )
    TaskRunner().run_task(response.task_id)

    result = task_service.get_result(session, response.task_id)
    return success_response(
        {
            "task_id": response.task_id,
            "status": result.status,
            "artifact_paths": result.artifacts,
        },
        message="eval_completed",
    )
