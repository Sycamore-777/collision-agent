"""Task-facing API routes."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import db_session
from app.core.errors import CollisionAgentError
from app.core.response import error_response, success_response
from app.schemas.task import ChatMessageCreate, TaskOptions
from app.services.task_service import TaskService

router = APIRouter(prefix="/v1/tasks", tags=["tasks"])
task_service = TaskService()


@router.post("")
def create_task(
    background_tasks: BackgroundTasks,
    task_type: str = Form("collision_warning"),
    url: str | None = Form(None),
    inline_payload: str | None = Form(None),
    user_requirement: str | None = Form(None),
    options_json: str | None = Form(None),
    files: list[UploadFile] | None = File(None),
    session: Session = Depends(db_session),
):
    try:
        options = TaskOptions.model_validate(json.loads(options_json)) if options_json else TaskOptions()
        data = task_service.create_task(
            session,
            background_tasks,
            task_type=task_type,
            options=options,
            uploaded_files=files,
            url=url,
            inline_payload=inline_payload,
            user_requirement=user_requirement,
        )
        return success_response(data.model_dump(mode="json"), message="task_created")
    except CollisionAgentError as exc:
        raise HTTPException(status_code=400, detail=error_response(str(exc), code=exc.code))


@router.get("")
def list_tasks(session: Session = Depends(db_session)):
    return success_response(
        [item.model_dump(mode="json") for item in task_service.list_tasks(session)],
        message="task_list",
    )


@router.get("/{task_id}")
def get_task(task_id: str, session: Session = Depends(db_session)):
    try:
        detail = task_service.get_task_detail(session, task_id)
        return success_response(detail.model_dump(mode="json"), message="task_detail")
    except CollisionAgentError as exc:
        raise HTTPException(status_code=404, detail=error_response(str(exc), code=exc.code))


@router.get("/{task_id}/result")
def get_result(task_id: str, session: Session = Depends(db_session)):
    try:
        result = task_service.get_result(session, task_id)
        return success_response(result.model_dump(mode="json"), message="task_result")
    except CollisionAgentError as exc:
        raise HTTPException(status_code=404, detail=error_response(str(exc), code=exc.code))


@router.get("/{task_id}/report")
def get_report(task_id: str, session: Session = Depends(db_session)):
    try:
        report = task_service.get_report(session, task_id)
        return success_response(report.model_dump(mode="json"), message="task_report")
    except CollisionAgentError as exc:
        raise HTTPException(status_code=404, detail=error_response(str(exc), code=exc.code))


@router.get("/{task_id}/trace")
def get_trace(task_id: str, session: Session = Depends(db_session)):
    try:
        trace = task_service.get_trace(session, task_id)
        return success_response(trace.model_dump(mode="json"), message="task_trace")
    except CollisionAgentError as exc:
        raise HTTPException(status_code=404, detail=error_response(str(exc), code=exc.code))


@router.get("/{task_id}/llm-calls")
def get_llm_calls(task_id: str, session: Session = Depends(db_session)):
    return success_response(task_service.get_llm_calls(session, task_id), message="llm_calls")


@router.get("/{task_id}/chat")
def get_chat_messages(task_id: str, session: Session = Depends(db_session)):
    try:
        messages = task_service.get_chat_messages(session, task_id)
        return success_response([item.model_dump(mode="json") for item in messages], message="task_chat")
    except CollisionAgentError as exc:
        raise HTTPException(status_code=404, detail=error_response(str(exc), code=exc.code))


@router.post("/{task_id}/chat")
def create_chat_reply(
    task_id: str,
    payload: ChatMessageCreate,
    session: Session = Depends(db_session),
):
    try:
        message = task_service.create_chat_reply(
            session,
            task_id,
            content=payload.content,
            attachments=payload.attachments,
        )
        return success_response(message.model_dump(mode="json"), message="chat_reply")
    except CollisionAgentError as exc:
        status_code = 400 if exc.code == "validation_failure" else 404
        raise HTTPException(status_code=status_code, detail=error_response(str(exc), code=exc.code))


@router.post("/{task_id}/chat/stream")
def stream_chat_reply(
    task_id: str,
    payload: ChatMessageCreate,
):
    try:
        return StreamingResponse(
            task_service.stream_chat_reply(
                task_id,
                content=payload.content,
                attachments=payload.attachments,
                persist_user=payload.persist_user,
            ),
            media_type="text/plain; charset=utf-8",
        )
    except CollisionAgentError as exc:
        status_code = 400 if exc.code == "validation_failure" else 404
        raise HTTPException(status_code=status_code, detail=error_response(str(exc), code=exc.code))


@router.post("/{task_id}/chat/stream-form")
def stream_chat_reply_form(
    task_id: str,
    content: str = Form(...),
    files: list[UploadFile] | None = File(None),
):
    try:
        uploaded_files = [
            {
                "filename": upload.filename or "upload.bin",
                "content_type": upload.content_type,
                "payload": upload.file.read(),
            }
            for upload in files or []
        ]
        return StreamingResponse(
            task_service.stream_chat_reply_with_files(
                task_id,
                content=content,
                uploaded_files=uploaded_files,
            ),
            media_type="text/plain; charset=utf-8",
        )
    except CollisionAgentError as exc:
        status_code = 400 if exc.code == "validation_failure" else 404
        raise HTTPException(status_code=status_code, detail=error_response(str(exc), code=exc.code))
