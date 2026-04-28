"""In-memory trace builder used by the task runner."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.schemas.task import TaskTrace, TraceStep


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class TraceBuilder:
    """Collect step-level execution trace information."""

    task_id: str
    steps: list[TraceStep] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    retries: int = 0
    metadata: dict = field(default_factory=dict)

    def add_step(
        self,
        *,
        step_name: str,
        step_status: str,
        started_at: datetime,
        finished_at: datetime | None = None,
        latency_ms: int | None = None,
        input_ref: str | None = None,
        output_ref: str | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        retry_count: int = 0,
    ) -> None:
        step = TraceStep(
            step_name=step_name,
            step_status=step_status,
            started_at=started_at,
            finished_at=finished_at,
            latency_ms=latency_ms,
            input_ref=input_ref,
            output_ref=output_ref,
            error_code=error_code,
            error_message=error_message,
            retry_count=retry_count,
        )
        self.steps.append(step)
        if error_message:
            self.errors.append(f"{step_name}: {error_message}")
        self.retries += retry_count

    def build(self, final_status: str) -> TaskTrace:
        return TaskTrace(
            task_id=self.task_id,
            final_status=final_status,
            steps=self.steps,
            errors=self.errors,
            retries=self.retries,
            metadata=self.metadata,
        )
