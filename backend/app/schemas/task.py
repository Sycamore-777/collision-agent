"""Schemas for task APIs, result payloads, and traces."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.document import ParsedDocument
from app.schemas.event import ConjunctionEvent


class TaskInputSpec(BaseModel):
    """Unified internal input description."""

    input_type: str
    source_uri: str | None = None
    source_name: str | None = None
    content_type: str | None = None
    local_path: str | None = None
    confidentiality: str | None = None
    file_hash: str | None = None


class TaskOptions(BaseModel):
    """Task-level feature flags."""

    enable_external_context: bool = True
    enable_llm_suggestion: bool = True
    enable_report_generation: bool = True
    enable_manual_review_route: bool = True


class TaskCreatePayload(BaseModel):
    """Canonical task creation payload used after request normalization."""

    task_type: str = "collision_warning"
    inputs: list[TaskInputSpec] = Field(default_factory=list)
    options: TaskOptions = Field(default_factory=TaskOptions)
    user_requirement: str | None = None


class TaskResponse(BaseModel):
    """Simple task creation response."""

    task_id: str
    status: str
    created_at: datetime


class TaskSummary(BaseModel):
    """List view for tasks."""

    task_id: str
    task_type: str
    status: str
    created_at: datetime
    updated_at: datetime
    latest_risk_level: str | None = None
    event_count: int = 0


class TraceStep(BaseModel):
    """Trace information for a workflow step."""

    step_name: str
    step_status: str
    started_at: datetime
    finished_at: datetime | None = None
    latency_ms: int | None = None
    input_ref: str | None = None
    output_ref: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    retry_count: int = 0


class TaskTrace(BaseModel):
    """Full task trace payload."""

    task_id: str
    final_status: str
    steps: list[TraceStep] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    retries: int = 0
    metadata: dict = Field(default_factory=dict)


class ResultPayload(BaseModel):
    """Structured task result payload."""

    task_id: str
    status: str
    task_type: str
    user_requirement: str | None = None
    parsed_documents: list[ParsedDocument] = Field(default_factory=list)
    events: list[ConjunctionEvent] = Field(default_factory=list)
    event_threads: dict[str, list[str]] = Field(default_factory=dict)
    generated_at: datetime
    degraded_modes: list[str] = Field(default_factory=list)
    artifacts: dict = Field(default_factory=dict)


class ReportPayload(BaseModel):
    """Human-readable report response."""

    task_id: str
    markdown: str
    html: str
    result_json_path: str
    trace_json_path: str


class TaskDetail(BaseModel):
    """Detailed task view for frontend and API consumers."""

    task_id: str
    task_type: str
    user_requirement: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime
    finished_at: datetime | None = None
    error_message: str | None = None
    inputs: list[TaskInputSpec] = Field(default_factory=list)
    parsed_documents: list[ParsedDocument] = Field(default_factory=list)
    events: list[ConjunctionEvent] = Field(default_factory=list)
    step_logs: list[TraceStep] = Field(default_factory=list)
    artifacts: dict = Field(default_factory=dict)


class ChatMessageCreate(BaseModel):
    """Request payload for a follow-up chat message."""

    content: str
    attachments: list[dict] = Field(default_factory=list)
    persist_user: bool = True


class ChatMessage(BaseModel):
    """Persisted task chat message."""

    id: str
    task_id: str
    role: str
    content: str
    attachments: list[dict] = Field(default_factory=list)
    llm_call_id: str | None = None
    created_at: datetime
