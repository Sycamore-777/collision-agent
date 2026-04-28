"""Task creation, chat, and read-model assembly."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterator

from fastapi import BackgroundTasks, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_session_factory
from app.core.enums import InputType, TaskStatus
from app.core.errors import NotFoundError, ValidationFailure
from app.llm.clients import build_llm_client
from app.repositories.task_repository import TaskRepository
from app.schemas.document import ParsedDocument
from app.schemas.event import ConjunctionEvent
from app.schemas.task import (
    ChatMessage,
    ReportPayload,
    ResultPayload,
    TaskDetail,
    TaskInputSpec,
    TaskOptions,
    TaskResponse,
    TaskSummary,
    TaskTrace,
    TraceStep,
)
from app.services.storage import StorageService


class TaskService:
    """Create tasks, handle task chat, and compose task-centric API responses."""

    def __init__(self) -> None:
        self.storage = StorageService()

    def create_task(
        self,
        session: Session,
        background_tasks: BackgroundTasks,
        *,
        task_type: str,
        options: TaskOptions,
        uploaded_files: list[UploadFile] | None = None,
        url: str | None = None,
        inline_payload: str | None = None,
        user_requirement: str | None = None,
        enqueue_runner: bool = True,
    ) -> TaskResponse:
        normalized_requirement = user_requirement.strip() if user_requirement else None
        if not uploaded_files and not url and not inline_payload and not normalized_requirement:
            raise ValidationFailure("至少提供一个需求说明、文件、URL 或内联载荷。")

        repo = TaskRepository(session)
        config_json = options.model_dump(mode="json")
        config_json["user_requirement"] = normalized_requirement
        task = repo.create_task(
            task_type=task_type,
            status=TaskStatus.PENDING.value,
            config_json=config_json,
        )
        initial_attachments: list[dict[str, Any]] = []

        for upload in uploaded_files or []:
            payload = upload.file.read()
            local_path, file_hash = self.storage.save_upload(upload.filename or "upload.bin", payload)
            initial_attachments.append(
                {
                    "name": upload.filename or Path(local_path).name,
                    "content_type": upload.content_type,
                    "file_hash": file_hash,
                }
            )
            repo.add_task_input(
                task_id=task.id,
                input_type=InputType.FILE.value,
                source_uri=None,
                source_name=upload.filename or Path(local_path).name,
                file_hash=file_hash,
                confidentiality="internal",
                content_type=upload.content_type,
                local_path=local_path,
            )

        if url:
            initial_attachments.append({"name": Path(url).name or "remote_url", "source_uri": url, "type": "url"})
            repo.add_task_input(
                task_id=task.id,
                input_type=InputType.URL.value,
                source_uri=url,
                source_name=Path(url).name or "remote_url",
                file_hash=None,
                confidentiality="external",
                content_type="text/plain",
                local_path=None,
            )

        if inline_payload:
            local_path, file_hash = self.storage.save_upload("inline_payload.json", inline_payload.encode("utf-8"))
            initial_attachments.append({"name": "inline_payload.json", "type": "inline", "file_hash": file_hash})
            repo.add_task_input(
                task_id=task.id,
                input_type=InputType.INLINE.value,
                source_uri=None,
                source_name="inline_payload.json",
                file_hash=file_hash,
                confidentiality="internal",
                content_type="application/json",
                local_path=local_path,
            )

        if normalized_requirement:
            repo.add_chat_message(
                task_id=task.id,
                role="user",
                content=normalized_requirement,
                attachments_json=initial_attachments,
                llm_call_id=None,
            )

        session.commit()

        if enqueue_runner:
            from app.orchestrator.runner import TaskRunner

            background_tasks.add_task(TaskRunner().run_task, task.id)
        return TaskResponse(task_id=task.id, status=task.status, created_at=task.created_at)

    def list_tasks(self, session: Session) -> list[TaskSummary]:
        repo = TaskRepository(session)
        summaries: list[TaskSummary] = []
        for task in repo.list_tasks():
            task_events = list(repo.list_events(task.id))
            latest_event = task_events[-1] if task_events else None
            summaries.append(
                TaskSummary(
                    task_id=task.id,
                    task_type=task.task_type,
                    status=task.status,
                    created_at=task.created_at,
                    updated_at=task.updated_at,
                    latest_risk_level=latest_event.risk_level if latest_event else None,
                    event_count=len(task_events),
                )
            )
        return summaries

    def get_task_detail(self, session: Session, task_id: str) -> TaskDetail:
        repo = TaskRepository(session)
        task = repo.get_task(task_id)
        if task is None:
            raise NotFoundError(f"未找到任务 {task_id}。")

        parsed_documents = self._load_parsed_documents(repo, task_id)
        events = self._load_events(repo, task_id)
        latest_report = repo.latest_report(task_id)

        artifacts = {}
        if latest_report is not None:
            artifacts = {
                "report_path": latest_report.report_path,
                "result_json_path": latest_report.result_json_path,
                "trace_json_path": latest_report.trace_json_path,
            }

        return TaskDetail(
            task_id=task.id,
            task_type=task.task_type,
            user_requirement=(task.config_json or {}).get("user_requirement"),
            status=task.status,
            created_at=task.created_at,
            updated_at=task.updated_at,
            finished_at=task.finished_at,
            error_message=task.error_message,
            inputs=[
                TaskInputSpec(
                    input_type=item.input_type,
                    source_uri=item.source_uri,
                    source_name=item.source_name,
                    content_type=item.content_type,
                    local_path=item.local_path,
                    confidentiality=item.confidentiality,
                    file_hash=item.file_hash,
                )
                for item in repo.list_inputs(task_id)
            ],
            parsed_documents=parsed_documents,
            events=events,
            step_logs=[
                TraceStep(
                    step_name=step.step_name,
                    step_status=step.step_status,
                    started_at=step.started_at,
                    finished_at=step.finished_at,
                    latency_ms=step.latency_ms,
                    input_ref=step.input_ref,
                    output_ref=step.output_ref,
                    error_code=step.error_code,
                    error_message=step.error_message,
                    retry_count=step.retry_count,
                )
                for step in repo.list_step_logs(task_id)
            ],
            artifacts=artifacts,
        )

    def get_result(self, session: Session, task_id: str) -> ResultPayload:
        repo = TaskRepository(session)
        latest_report = repo.latest_report(task_id)
        if latest_report is None:
            raise NotFoundError(f"任务 {task_id} 的结果产物尚未生成。")
        return ResultPayload.model_validate(self.storage.read_json(latest_report.result_json_path))

    def get_report(self, session: Session, task_id: str) -> ReportPayload:
        repo = TaskRepository(session)
        latest_report = repo.latest_report(task_id)
        if latest_report is None:
            raise NotFoundError(f"任务 {task_id} 的报告产物尚未生成。")
        markdown = self.storage.read_text(latest_report.report_path)
        html_path = str(Path(latest_report.report_path).with_suffix(".html"))
        html = (
            self.storage.read_text(html_path)
            if Path(html_path).exists()
            else "<html><body><pre>暂无 HTML 报告。</pre></body></html>"
        )
        return ReportPayload(
            task_id=task_id,
            markdown=markdown,
            html=html,
            result_json_path=latest_report.result_json_path,
            trace_json_path=latest_report.trace_json_path,
        )

    def get_trace(self, session: Session, task_id: str) -> TaskTrace:
        repo = TaskRepository(session)
        latest_report = repo.latest_report(task_id)
        if latest_report is None:
            raise NotFoundError(f"任务 {task_id} 的 Trace 产物尚未生成。")
        return TaskTrace.model_validate(self.storage.read_json(latest_report.trace_json_path))

    def get_llm_calls(self, session: Session, task_id: str) -> list[dict[str, Any]]:
        repo = TaskRepository(session)
        return [
            {
                "id": item.id,
                "step_name": item.step_name,
                "provider_name": item.provider_name,
                "model_name": item.model_name,
                "status": item.status,
                "created_at": item.created_at,
                "prompt_text": item.prompt_text,
                "response_text": item.response_text,
                "prompt_name": item.parsed_output_json.get("prompt_name"),
                "prompt_lang": item.parsed_output_json.get("prompt_lang"),
                "parsed_output_json": item.parsed_output_json,
            }
            for item in repo.list_llm_calls(task_id)
        ]

    def get_chat_messages(self, session: Session, task_id: str) -> list[ChatMessage]:
        repo = TaskRepository(session)
        if repo.get_task(task_id) is None:
            raise NotFoundError(f"未找到任务 {task_id}。")
        return [self._chat_message_from_record(item) for item in repo.list_chat_messages(task_id)]

    def create_chat_reply(
        self,
        session: Session,
        task_id: str,
        *,
        content: str,
        attachments: list[dict] | None = None,
    ) -> ChatMessage:
        normalized_content = content.strip()
        if not normalized_content:
            raise ValidationFailure("请输入要追问的内容。")

        repo = TaskRepository(session)
        task = repo.get_task(task_id)
        if task is None:
            raise NotFoundError(f"未找到任务 {task_id}。")

        repo.add_chat_message(
            task_id=task_id,
            role="user",
            content=normalized_content,
            attachments_json=attachments or [],
            llm_call_id=None,
        )
        session.commit()

        history = [
            {
                "role": item.role,
                "content": item.content,
                "created_at": item.created_at.isoformat(),
            }
            for item in repo.list_chat_messages(task_id)
        ]
        task_context = self._build_chat_context(repo, task)
        execution = build_llm_client().generate_chat_reply(
            user_message=normalized_content,
            history=history,
            task_context=task_context,
        )
        llm_call = repo.add_llm_call(
            task_id=task_id,
            step_name="chat_reply",
            provider_name="mock" if execution.used_mock else "openai_compatible",
            model_name="mock-template" if execution.used_mock else "chat-model",
            temperature=0.0,
            max_tokens=0,
            prompt_text=execution.prompt_text,
            response_text=execution.response_text,
            parsed_output_json={
                "reply_text": execution.reply_text,
                "prompt_name": execution.prompt_name,
                "prompt_lang": execution.prompt_lang,
                "used_mock": execution.used_mock,
            },
            status="succeeded",
            error_message=None,
        )
        assistant_message = repo.add_chat_message(
            task_id=task_id,
            role="assistant",
            content=execution.reply_text,
            attachments_json=[],
            llm_call_id=llm_call.id,
        )
        session.commit()
        return self._chat_message_from_record(assistant_message)

    def stream_chat_reply(
        self,
        task_id: str,
        *,
        content: str,
        attachments: list[dict] | None = None,
        persist_user: bool = True,
    ) -> Iterator[str]:
        normalized_content = content.strip()
        if not normalized_content:
            raise ValidationFailure("请输入要追问的内容。")

        session = get_session_factory()()
        try:
            repo = TaskRepository(session)
            task = repo.get_task(task_id)
            if task is None:
                raise NotFoundError(f"未找到任务 {task_id}。")

            if persist_user:
                repo.add_chat_message(
                    task_id=task_id,
                    role="user",
                    content=normalized_content,
                    attachments_json=attachments or [],
                    llm_call_id=None,
                )
                session.commit()

            history = [
                {
                    "role": item.role,
                    "content": item.content,
                    "created_at": item.created_at.isoformat(),
                }
                for item in repo.list_chat_messages(task_id)
            ]
            task_context = self._build_chat_context(repo, task)
            stream = build_llm_client().stream_chat_reply(
                user_message=normalized_content,
                history=history,
                task_context=task_context,
            )

            chunks: list[str] = []
            for chunk in stream.chunks:
                chunks.append(chunk)
                yield chunk

            response_text = "".join(chunks)
            llm_call = repo.add_llm_call(
                task_id=task_id,
                step_name="chat_reply",
                provider_name=stream.provider_name,
                model_name=stream.model_name,
                temperature=0.0,
                max_tokens=0,
                prompt_text=stream.prompt_text,
                response_text=response_text,
                parsed_output_json={
                    "reply_text": response_text,
                    "prompt_name": stream.prompt_name,
                    "prompt_lang": stream.prompt_lang,
                    "used_mock": stream.used_mock,
                    "streamed": True,
                },
                status="succeeded",
                error_message=None,
            )
            repo.add_chat_message(
                task_id=task_id,
                role="assistant",
                content=response_text,
                attachments_json=[],
                llm_call_id=llm_call.id,
            )
            session.commit()
        finally:
            session.close()

    def stream_chat_reply_with_files(
        self,
        task_id: str,
        *,
        content: str,
        uploaded_files: list[dict[str, Any]] | None = None,
    ) -> Iterator[str]:
        normalized_content = content.strip()
        if not normalized_content:
            raise ValidationFailure("请输入要追问的内容。")

        files = uploaded_files or []
        if not files:
            yield from self.stream_chat_reply(task_id, content=normalized_content)
            return

        session = get_session_factory()()
        try:
            repo = TaskRepository(session)
            task = repo.get_task(task_id)
            if task is None:
                raise NotFoundError(f"未找到任务 {task_id}。")

            attachments = self._persist_followup_files(repo, task_id, files)
            repo.add_chat_message(
                task_id=task_id,
                role="user",
                content=normalized_content,
                attachments_json=attachments,
                llm_call_id=None,
            )
            repo.clear_derived_records(task_id)
            session.commit()
        finally:
            session.close()

        yield f"已收到 {len(files)} 个新附件，正在加入任务输入并重新解析。\n\n"
        from app.orchestrator.runner import TaskRunner

        TaskRunner().run_task(task_id)
        yield "任务已基于新文件重新生成结果，下面基于最新证据回答。\n\n"
        yield from self.stream_chat_reply(
            task_id,
            content=normalized_content,
            attachments=attachments,
            persist_user=False,
        )

    def _load_parsed_documents(self, repo: TaskRepository, task_id: str) -> list[ParsedDocument]:
        documents: list[ParsedDocument] = []
        for record in repo.list_parsed_documents(task_id):
            documents.append(ParsedDocument.model_validate(self.storage.read_json(record.output_path)))
        return documents

    def _persist_followup_files(
        self,
        repo: TaskRepository,
        task_id: str,
        uploaded_files: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        attachments: list[dict[str, Any]] = []
        for upload in uploaded_files:
            filename = str(upload.get("filename") or "upload.bin")
            payload = upload.get("payload") or b""
            content_type = upload.get("content_type")
            local_path, file_hash = self.storage.save_upload(filename, payload)
            attachments.append(
                {
                    "name": filename,
                    "content_type": content_type,
                    "file_hash": file_hash,
                    "type": "followup_file",
                }
            )
            repo.add_task_input(
                task_id=task_id,
                input_type=InputType.FILE.value,
                source_uri=None,
                source_name=filename,
                file_hash=file_hash,
                confidentiality="internal",
                content_type=content_type,
                local_path=local_path,
            )
        return attachments

    def _load_events(self, repo: TaskRepository, task_id: str) -> list[ConjunctionEvent]:
        events: list[ConjunctionEvent] = []
        for record in repo.list_events(task_id):
            events.append(
                ConjunctionEvent(
                    event_id=record.event_id,
                    message_id=record.message_id,
                    conjunction_id=record.conjunction_id,
                    primary_object_name=record.primary_object_name,
                    secondary_object_name=record.secondary_object_name,
                    primary_norad_id=record.primary_norad_id,
                    secondary_norad_id=record.secondary_norad_id,
                    tca_utc=record.tca_utc,
                    miss_distance_m=record.miss_distance_m,
                    relative_speed_mps=record.relative_speed_mps,
                    collision_probability=record.collision_probability,
                    reference_frame=record.reference_frame,
                    covariance_present=record.covariance_present,
                    risk_level=record.risk_level,
                    action_recommendation=record.action_recommendation,
                    needs_manual_review=record.needs_manual_review,
                    evidence_refs=record.evidence_json,
                    version_group_key=record.version_group_key,
                )
            )
        return events

    def _chat_message_from_record(self, record) -> ChatMessage:
        return ChatMessage(
            id=record.id,
            task_id=record.task_id,
            role=record.role,
            content=record.content,
            attachments=record.attachments_json or [],
            llm_call_id=record.llm_call_id,
            created_at=record.created_at,
        )

    def _build_chat_context(self, repo: TaskRepository, task) -> dict[str, Any]:
        latest_report = repo.latest_report(task.id)
        events = self._load_events(repo, task.id)
        event_payloads = [
            {
                "event_id": event.event_id,
                "primary_object_name": event.primary_object_name,
                "secondary_object_name": event.secondary_object_name,
                "tca_utc": event.tca_utc.isoformat() if event.tca_utc else None,
                "miss_distance_m": event.miss_distance_m,
                "collision_probability": event.collision_probability,
                "risk_level": event.risk_level,
                "needs_manual_review": event.needs_manual_review,
                "action_recommendation": event.action_recommendation,
                "evidence_refs": [item.model_dump(mode="json") for item in event.evidence_refs[:8]],
            }
            for event in events
        ]

        report_excerpt = None
        trace_payload: dict[str, Any] | None = None
        degraded_modes: list[str] = []
        if latest_report is not None:
            if Path(latest_report.report_path).exists():
                report_excerpt = self.storage.read_text(latest_report.report_path)[:4000]
            if Path(latest_report.trace_json_path).exists():
                trace_payload = self.storage.read_json(latest_report.trace_json_path)
            if Path(latest_report.result_json_path).exists():
                result_payload = self.storage.read_json(latest_report.result_json_path)
                degraded_modes = result_payload.get("degraded_modes", [])

        return {
            "task_id": task.id,
            "status": task.status,
            "task_type": task.task_type,
            "user_requirement": (task.config_json or {}).get("user_requirement"),
            "events": event_payloads,
            "degraded_modes": degraded_modes,
            "report_excerpt": report_excerpt,
            "trace": trace_payload,
        }
