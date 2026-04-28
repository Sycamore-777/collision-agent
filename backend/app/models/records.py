"""Primary relational models for tasks, parsing, events, and artifacts."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


def generate_id() -> str:
    """Generate a stable string identifier."""

    return str(uuid4())


class TaskRecord(Base):
    __tablename__ = "task"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    task_type: Mapped[str] = mapped_column(String(64), default="collision_warning")
    status: Mapped[str] = mapped_column(String(32), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    config_json: Mapped[dict] = mapped_column(JSON, default=dict)

    inputs: Mapped[list["TaskInputRecord"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
    )
    parsed_documents: Mapped[list["ParsedDocumentRecord"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
    )
    events: Mapped[list["EventRecord"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
    )
    llm_calls: Mapped[list["LlmCallLogRecord"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
    )
    step_logs: Mapped[list["TaskStepLogRecord"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
    )
    reports: Mapped[list["ReportRecord"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
    )
    chat_messages: Mapped[list["ChatMessageRecord"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
    )


class TaskInputRecord(Base):
    __tablename__ = "task_input"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    task_id: Mapped[str] = mapped_column(ForeignKey("task.id", ondelete="CASCADE"))
    input_type: Mapped[str] = mapped_column(String(32))
    source_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    confidentiality: Mapped[str | None] = mapped_column(String(32), nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    local_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    task: Mapped[TaskRecord] = relationship(back_populates="inputs")


class ParsedDocumentRecord(Base):
    __tablename__ = "parsed_document"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    task_id: Mapped[str] = mapped_column(ForeignKey("task.id", ondelete="CASCADE"))
    doc_type: Mapped[str] = mapped_column(String(64))
    parser_name: Mapped[str] = mapped_column(String(64))
    parse_status: Mapped[str] = mapped_column(String(32))
    output_path: Mapped[str] = mapped_column(Text)
    confidence_summary: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    task: Mapped[TaskRecord] = relationship(back_populates="parsed_documents")


class EventRecord(Base):
    __tablename__ = "event_record"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    task_id: Mapped[str] = mapped_column(ForeignKey("task.id", ondelete="CASCADE"))
    event_id: Mapped[str] = mapped_column(String(128))
    message_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    conjunction_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    primary_object_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    secondary_object_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    primary_norad_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    secondary_norad_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tca_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    miss_distance_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    relative_speed_mps: Mapped[float | None] = mapped_column(Float, nullable=True)
    collision_probability: Mapped[float | None] = mapped_column(Float, nullable=True)
    reference_frame: Mapped[str | None] = mapped_column(String(64), nullable=True)
    covariance_present: Mapped[bool] = mapped_column(Boolean, default=False)
    risk_level: Mapped[str] = mapped_column(String(32), default="unknown")
    action_recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    needs_manual_review: Mapped[bool] = mapped_column(Boolean, default=False)
    evidence_json: Mapped[list] = mapped_column(JSON, default=list)
    version_group_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    task: Mapped[TaskRecord] = relationship(back_populates="events")


class LlmCallLogRecord(Base):
    __tablename__ = "llm_call_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    task_id: Mapped[str] = mapped_column(ForeignKey("task.id", ondelete="CASCADE"))
    step_name: Mapped[str] = mapped_column(String(64))
    provider_name: Mapped[str] = mapped_column(String(64))
    model_name: Mapped[str] = mapped_column(String(128))
    temperature: Mapped[float] = mapped_column(Float, default=0.2)
    max_tokens: Mapped[int] = mapped_column(Integer, default=2048)
    prompt_text: Mapped[str] = mapped_column(Text)
    response_text: Mapped[str] = mapped_column(Text)
    parsed_output_json: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(32), default="succeeded")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    task: Mapped[TaskRecord] = relationship(back_populates="llm_calls")


class TaskStepLogRecord(Base):
    __tablename__ = "task_step_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    task_id: Mapped[str] = mapped_column(ForeignKey("task.id", ondelete="CASCADE"))
    step_name: Mapped[str] = mapped_column(String(64))
    step_status: Mapped[str] = mapped_column(String(32))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    input_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)

    task: Mapped[TaskRecord] = relationship(back_populates="step_logs")


class ChatMessageRecord(Base):
    __tablename__ = "chat_message"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    task_id: Mapped[str] = mapped_column(ForeignKey("task.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String(32))
    content: Mapped[str] = mapped_column(Text)
    attachments_json: Mapped[list] = mapped_column(JSON, default=list)
    llm_call_id: Mapped[str | None] = mapped_column(ForeignKey("llm_call_log.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    task: Mapped[TaskRecord] = relationship(back_populates="chat_messages")


class ReportRecord(Base):
    __tablename__ = "report_record"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    task_id: Mapped[str] = mapped_column(ForeignKey("task.id", ondelete="CASCADE"))
    report_path: Mapped[str] = mapped_column(Text)
    result_json_path: Mapped[str] = mapped_column(Text)
    trace_json_path: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    task: Mapped[TaskRecord] = relationship(back_populates="reports")
