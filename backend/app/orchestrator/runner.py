"""Task runner that executes the end-to-end data agent workflow."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import httpx
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_session_factory
from app.core.enums import StepStatus, TaskStatus
from app.extractors.conjunction_extractor import ConjunctionExtractor
from app.external_sources.celestrak import CelesTrakClient
from app.llm.clients import build_llm_client
from app.parsers.base import ParserSource
from app.parsers.registry import ParserRegistry
from app.reporting.markdown import markdown_to_html, normalize_report_markdown
from app.repositories.task_repository import TaskRepository
from app.schemas.task import ResultPayload
from app.services.rules import EventAggregator
from app.services.storage import StorageService
from app.tracing.builder import TraceBuilder


class TaskRunner:
    """Execute a task and persist every meaningful step."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.storage = StorageService()
        self.parsers = ParserRegistry()
        self.extractor = ConjunctionExtractor()
        self.aggregator = EventAggregator()
        self.celestrak = CelesTrakClient()
        self.llm_client = build_llm_client()

    def run_task(self, task_id: str) -> None:
        session: Session = get_session_factory()()
        repo = TaskRepository(session)
        trace = TraceBuilder(task_id=task_id)
        degraded_modes: list[str] = []

        try:
            task = repo.get_task(task_id)
            if task is None:
                return

            repo.update_task_status(task, status=TaskStatus.RUNNING.value)
            session.commit()

            parsed_documents = self._parse_inputs(session, repo, task_id, trace, degraded_modes)
            events, constraints = self._extract_events(session, repo, task_id, parsed_documents, trace)
            events, event_threads = self.aggregator.aggregate(events)
            self._apply_external_context(session, repo, task_id, events, trace, degraded_modes)
            user_requirement = (task.config_json or {}).get("user_requirement")
            self._apply_llm_suggestions(session, repo, task_id, events, trace, degraded_modes, user_requirement)
            self._persist_events(session, repo, task_id, events)
            result_payload = self._build_and_persist_outputs(
                session,
                repo,
                task_id,
                task.task_type,
                user_requirement,
                parsed_documents,
                events,
                event_threads,
                trace,
                degraded_modes,
            )

            final_status = (
                TaskStatus.MANUAL_REVIEW.value
                if any(event.needs_manual_review for event in events)
                else TaskStatus.SUCCEEDED.value
            )
            repo.update_task_status(task, status=final_status, finished=True)
            session.commit()
            trace.metadata["final_artifacts"] = result_payload.artifacts
            self._write_trace_artifact(repo, session, task_id, trace, final_status)
        except Exception as exc:
            task = repo.get_task(task_id)
            if task is not None:
                repo.update_task_status(
                    task,
                    status=TaskStatus.FAILED.value,
                    error_message=str(exc),
                    finished=True,
                )
            trace.errors.append(str(exc))
            self._log_step(
                repo,
                session,
                trace,
                step_name="task_failed",
                step_status=StepStatus.FAILED.value,
                input_ref=task_id,
                output_ref=None,
                error_code="task_failed",
                error_message=str(exc),
            )
            self._write_trace_artifact(repo, session, task_id, trace, TaskStatus.FAILED.value)
            session.commit()
        finally:
            session.close()

    def _parse_inputs(
        self,
        session: Session,
        repo: TaskRepository,
        task_id: str,
        trace: TraceBuilder,
        degraded_modes: list[str],
    ) -> list:
        documents = []
        for input_record in repo.list_inputs(task_id):
            parser_source = self._build_parser_source(input_record, degraded_modes)
            parser = self.parsers.resolve(parser_source)

            started_at = self._now()
            document = parser.parse(parser_source)
            output_path = self.storage.save_json(
                self.settings.parsed_dir,
                f"{task_id}_{document.doc_type}",
                document.model_dump(mode="json"),
            )
            repo.add_parsed_document(
                task_id=task_id,
                doc_type=document.doc_type,
                parser_name=document.parser_name,
                parse_status="succeeded",
                output_path=output_path,
                confidence_summary=document.confidence_summary.model_dump(mode="json"),
            )
            session.commit()
            self._log_step(
                repo,
                session,
                trace,
                step_name=f"parse_{Path(input_record.source_name or 'input').stem}",
                step_status=StepStatus.SUCCEEDED.value,
                started_at=started_at,
                input_ref=input_record.local_path or input_record.source_uri,
                output_ref=output_path,
            )
            documents.append(document)
        return documents

    def _extract_events(
        self,
        session: Session,
        repo: TaskRepository,
        task_id: str,
        parsed_documents: list,
        trace: TraceBuilder,
    ) -> tuple[list, list]:
        started_at = self._now()
        events, constraints = self.extractor.extract_events(parsed_documents)
        self._log_step(
            repo,
            session,
            trace,
            step_name="extract_events",
            step_status=StepStatus.SUCCEEDED.value,
            started_at=started_at,
            input_ref=str(len(parsed_documents)),
            output_ref=str(len(events)),
        )
        session.commit()
        return events, constraints

    def _apply_external_context(
        self,
        session: Session,
        repo: TaskRepository,
        task_id: str,
        events: list,
        trace: TraceBuilder,
        degraded_modes: list[str],
    ) -> None:
        for event in events:
            started_at = self._now()
            primary_context = self.celestrak.fetch_context(event.primary_norad_id)
            secondary_context = self.celestrak.fetch_context(event.secondary_norad_id)
            event.external_context = {
                "primary": primary_context,
                "secondary": secondary_context,
            }
            if primary_context["source"] != "celestrak" or secondary_context["source"] != "celestrak":
                degraded_modes.append("external_context_fallback")

            self._log_step(
                repo,
                session,
                trace,
                step_name=f"context_{event.event_id}",
                step_status=StepStatus.SUCCEEDED.value,
                started_at=started_at,
                input_ref=event.event_id,
                output_ref="external_context",
            )

    def _apply_llm_suggestions(
        self,
        session: Session,
        repo: TaskRepository,
        task_id: str,
        events: list,
        trace: TraceBuilder,
        degraded_modes: list[str],
        user_requirement: str | None,
    ) -> None:
        if not self.settings.enable_llm_suggestion:
            for event in events:
                event.risk_level = "unknown"
                event.needs_manual_review = True
                event.action_recommendation = "大模型建议已关闭，系统不使用程序规则替代判断；请转人工复核。"
            degraded_modes.append("llm_disabled_manual_review")
            return

        for event in events:
            started_at = self._now()
            execution = self.llm_client.generate_suggestion(event, user_requirement=user_requirement)
            suggestion = execution.suggestion
            if suggestion.used_mock:
                degraded_modes.append("llm_mock_fallback")
            event.llm_suggestion = suggestion
            event.risk_level = suggestion.risk_level or "unknown"
            event.needs_manual_review = (
                suggestion.needs_manual_review
                if suggestion.needs_manual_review is not None
                else True
            )
            event.action_recommendation = suggestion.recommendation_text
            trace.metadata.setdefault("llm_prompts", {})[event.event_id] = {
                "prompt_name": execution.prompt_name,
                "prompt_lang": execution.prompt_lang,
            }

            repo.add_llm_call(
                task_id=task_id,
                step_name=f"llm_{event.event_id}",
                provider_name=suggestion.provider_name,
                model_name=suggestion.model_name,
                temperature=self.settings.llm_temperature,
                max_tokens=self.settings.llm_max_tokens,
                prompt_text=execution.prompt_text,
                response_text=execution.response_text,
                parsed_output_json={
                    **suggestion.model_dump(mode="json"),
                    "prompt_name": execution.prompt_name,
                    "prompt_lang": execution.prompt_lang,
                },
                status="succeeded",
                error_message=None,
            )
            session.commit()
            self._log_step(
                repo,
                session,
                trace,
                step_name=f"llm_{event.event_id}",
                step_status=StepStatus.SUCCEEDED.value,
                started_at=started_at,
                input_ref=event.event_id,
                output_ref=suggestion.model_name,
            )

    def _persist_events(
        self,
        session: Session,
        repo: TaskRepository,
        task_id: str,
        events: list,
    ) -> None:
        for event in events:
            repo.add_event(
                task_id=task_id,
                event_id=event.event_id,
                message_id=event.message_id,
                conjunction_id=event.conjunction_id,
                primary_object_name=event.primary_object_name,
                secondary_object_name=event.secondary_object_name,
                primary_norad_id=event.primary_norad_id,
                secondary_norad_id=event.secondary_norad_id,
                tca_utc=event.tca_utc,
                miss_distance_m=event.miss_distance_m,
                relative_speed_mps=event.relative_speed_mps,
                collision_probability=event.collision_probability,
                reference_frame=event.reference_frame,
                covariance_present=event.covariance_present,
                risk_level=event.risk_level,
                action_recommendation=event.action_recommendation,
                needs_manual_review=event.needs_manual_review,
                evidence_json=[item.model_dump(mode="json") for item in event.evidence_refs],
                version_group_key=event.version_group_key,
            )
        session.commit()

    def _build_and_persist_outputs(
        self,
        session: Session,
        repo: TaskRepository,
        task_id: str,
        task_type: str,
        user_requirement: str | None,
        parsed_documents: list,
        events: list,
        event_threads: dict[str, list[str]],
        trace: TraceBuilder,
        degraded_modes: list[str],
    ) -> ResultPayload:
        started_at = self._now()
        unique_degraded = sorted(set(degraded_modes))
        result_payload = ResultPayload(
            task_id=task_id,
            status=TaskStatus.MANUAL_REVIEW.value if any(event.needs_manual_review for event in events) else TaskStatus.SUCCEEDED.value,
            task_type=task_type,
            user_requirement=user_requirement,
            parsed_documents=parsed_documents,
            events=events,
            event_threads=event_threads,
            generated_at=self._now(),
            degraded_modes=unique_degraded,
            artifacts={},
        )

        result_path = str(Path(self.settings.report_dir) / f"{task_id}_result.json")
        provisional_trace_path = str(Path(self.settings.trace_dir) / f"{task_id}_trace.json")
        markdown_path = str(Path(self.settings.report_dir) / f"{task_id}_report.md")
        html_path = str(Path(self.settings.report_dir) / f"{task_id}_report.html")
        result_payload.artifacts = {
            "result_json_path": result_path,
            "report_markdown_path": markdown_path,
            "report_html_path": html_path,
        }
        report_execution = self.llm_client.generate_final_report(result_payload.model_dump(mode="json"))
        if report_execution.used_mock:
            degraded_modes.append("llm_mock_fallback")
            result_payload.degraded_modes = sorted(set(degraded_modes))
        markdown = normalize_report_markdown(report_execution.reply_text)
        html = markdown_to_html(markdown)
        markdown_path = self.storage.save_named_text(self.settings.report_dir, f"{task_id}_report.md", markdown)
        html_path = self.storage.save_named_text(self.settings.report_dir, f"{task_id}_report.html", html)
        result_path = self.storage.save_named_json(
            self.settings.report_dir,
            f"{task_id}_result.json",
            result_payload.model_dump(mode="json"),
        )
        repo.add_report(
            task_id=task_id,
            report_path=markdown_path,
            result_json_path=result_path,
            trace_json_path=provisional_trace_path,
        )
        llm_call = repo.add_llm_call(
            task_id=task_id,
            step_name="llm_final_report",
            provider_name=report_execution.provider_name,
            model_name=report_execution.model_name,
            temperature=self.settings.llm_temperature,
            max_tokens=self.settings.llm_max_tokens,
            prompt_text=report_execution.prompt_text,
            response_text=report_execution.response_text,
            parsed_output_json={
                "report_markdown": markdown,
                "prompt_name": report_execution.prompt_name,
                "prompt_lang": report_execution.prompt_lang,
                "used_mock": report_execution.used_mock,
            },
            status="succeeded",
            error_message=None,
        )
        session.commit()
        self._log_step(
            repo,
            session,
            trace,
            step_name="generate_outputs",
            step_status=StepStatus.SUCCEEDED.value,
            started_at=started_at,
            input_ref=str(len(events)),
            output_ref=result_path,
        )
        return result_payload

    def _write_trace_artifact(
        self,
        repo: TaskRepository,
        session: Session,
        task_id: str,
        trace: TraceBuilder,
        final_status: str,
    ) -> None:
        trace_payload = trace.build(final_status)
        trace_path = self.storage.save_named_json(
            self.settings.trace_dir,
            f"{task_id}_trace.json",
            trace_payload.model_dump(mode="json"),
        )
        latest_report = repo.latest_report(task_id)
        if latest_report is not None:
            latest_report.trace_json_path = trace_path
            session.add(latest_report)
            session.commit()

    def _build_parser_source(self, input_record, degraded_modes: list[str]) -> ParserSource:
        text_content: str | None = None
        if input_record.input_type == "url" and input_record.source_uri:
            try:
                response = httpx.get(input_record.source_uri, timeout=10.0)
                response.raise_for_status()
                text_content = response.text
            except Exception:
                degraded_modes.append("url_fetch_fallback")
                text_content = input_record.source_uri
        elif input_record.local_path:
            path = Path(input_record.local_path)
            if path.exists() and path.suffix.lower() in {".json", ".xml", ".kvn", ".txt"}:
                text_content = path.read_text(encoding="utf-8", errors="ignore")

        return ParserSource(
            source_name=input_record.source_name or "input",
            input_type=input_record.input_type,
            content_type=input_record.content_type,
            local_path=input_record.local_path,
            source_uri=input_record.source_uri,
            text_content=text_content,
            metadata={"file_hash": input_record.file_hash},
        )

    def _log_step(
        self,
        repo: TaskRepository,
        session: Session,
        trace: TraceBuilder,
        *,
        step_name: str,
        step_status: str,
        started_at: datetime | None = None,
        input_ref: str | None = None,
        output_ref: str | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        retry_count: int = 0,
    ) -> None:
        started_at = started_at or self._now()
        finished_at = self._now()
        latency_ms = int((finished_at - started_at).total_seconds() * 1000)
        repo.add_step_log(
            task_id=trace.task_id,
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
        session.commit()
        trace.add_step(
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

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)
