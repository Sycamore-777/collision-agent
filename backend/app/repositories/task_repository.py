"""Persistence helpers for task-centric workflows."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone

from sqlalchemy import delete, desc, select, update
from sqlalchemy.orm import Session

from app.models.records import (
    ChatMessageRecord,
    EventRecord,
    LlmCallLogRecord,
    ParsedDocumentRecord,
    ReportRecord,
    TaskInputRecord,
    TaskRecord,
    TaskStepLogRecord,
)


def now_utc() -> datetime:
    """Return a UTC timestamp for persistence."""

    return datetime.now(timezone.utc)


class TaskRepository:
    """Repository wrapper around the SQLAlchemy session."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create_task(self, *, task_type: str, status: str, config_json: dict) -> TaskRecord:
        task = TaskRecord(
            task_type=task_type,
            status=status,
            created_at=now_utc(),
            updated_at=now_utc(),
            config_json=config_json,
        )
        self.session.add(task)
        self.session.flush()
        return task

    def add_task_input(self, **values: object) -> TaskInputRecord:
        record = TaskInputRecord(created_at=now_utc(), **values)
        self.session.add(record)
        self.session.flush()
        return record

    def add_parsed_document(self, **values: object) -> ParsedDocumentRecord:
        record = ParsedDocumentRecord(created_at=now_utc(), **values)
        self.session.add(record)
        self.session.flush()
        return record

    def add_event(self, **values: object) -> EventRecord:
        record = EventRecord(created_at=now_utc(), **values)
        self.session.add(record)
        self.session.flush()
        return record

    def add_llm_call(self, **values: object) -> LlmCallLogRecord:
        record = LlmCallLogRecord(created_at=now_utc(), **values)
        self.session.add(record)
        self.session.flush()
        return record

    def add_step_log(self, **values: object) -> TaskStepLogRecord:
        record = TaskStepLogRecord(**values)
        self.session.add(record)
        self.session.flush()
        return record

    def add_report(self, **values: object) -> ReportRecord:
        record = ReportRecord(created_at=now_utc(), **values)
        self.session.add(record)
        self.session.flush()
        return record

    def add_chat_message(self, **values: object) -> ChatMessageRecord:
        record = ChatMessageRecord(created_at=now_utc(), **values)
        self.session.add(record)
        self.session.flush()
        return record

    def get_task(self, task_id: str) -> TaskRecord | None:
        return self.session.get(TaskRecord, task_id)

    def list_tasks(self) -> Sequence[TaskRecord]:
        stmt = select(TaskRecord).order_by(desc(TaskRecord.created_at))
        return self.session.scalars(stmt).all()

    def list_step_logs(self, task_id: str) -> Sequence[TaskStepLogRecord]:
        stmt = (
            select(TaskStepLogRecord)
            .where(TaskStepLogRecord.task_id == task_id)
            .order_by(TaskStepLogRecord.started_at)
        )
        return self.session.scalars(stmt).all()

    def list_events(self, task_id: str) -> Sequence[EventRecord]:
        stmt = select(EventRecord).where(EventRecord.task_id == task_id).order_by(EventRecord.created_at)
        return self.session.scalars(stmt).all()

    def list_inputs(self, task_id: str) -> Sequence[TaskInputRecord]:
        stmt = select(TaskInputRecord).where(TaskInputRecord.task_id == task_id).order_by(TaskInputRecord.created_at)
        return self.session.scalars(stmt).all()

    def list_parsed_documents(self, task_id: str) -> Sequence[ParsedDocumentRecord]:
        stmt = (
            select(ParsedDocumentRecord)
            .where(ParsedDocumentRecord.task_id == task_id)
            .order_by(ParsedDocumentRecord.created_at)
        )
        return self.session.scalars(stmt).all()

    def list_llm_calls(self, task_id: str) -> Sequence[LlmCallLogRecord]:
        stmt = select(LlmCallLogRecord).where(LlmCallLogRecord.task_id == task_id).order_by(LlmCallLogRecord.created_at)
        return self.session.scalars(stmt).all()

    def list_chat_messages(self, task_id: str) -> Sequence[ChatMessageRecord]:
        stmt = (
            select(ChatMessageRecord)
            .where(ChatMessageRecord.task_id == task_id)
            .order_by(ChatMessageRecord.created_at)
        )
        return self.session.scalars(stmt).all()

    def latest_report(self, task_id: str) -> ReportRecord | None:
        stmt = (
            select(ReportRecord)
            .where(ReportRecord.task_id == task_id)
            .order_by(desc(ReportRecord.created_at))
        )
        return self.session.scalars(stmt).first()

    def clear_derived_records(self, task_id: str) -> None:
        """Remove task outputs that must be regenerated after new inputs arrive."""

        self.session.execute(
            update(ChatMessageRecord)
            .where(ChatMessageRecord.task_id == task_id)
            .values(llm_call_id=None)
        )
        for model in (
            ReportRecord,
            EventRecord,
            ParsedDocumentRecord,
            TaskStepLogRecord,
            LlmCallLogRecord,
        ):
            self.session.execute(delete(model).where(model.task_id == task_id))
        self.session.flush()

    def update_task_status(
        self,
        task: TaskRecord,
        *,
        status: str,
        error_message: str | None = None,
        finished: bool = False,
    ) -> TaskRecord:
        task.status = status
        task.updated_at = now_utc()
        task.error_message = error_message
        if finished:
            task.finished_at = now_utc()
        self.session.add(task)
        self.session.flush()
        return task
