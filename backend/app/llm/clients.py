"""Real and mock LLM clients."""

from __future__ import annotations

import json
import re
from collections.abc import Iterator

import httpx

from app.core.config import get_settings
from app.llm.base import BaseLLMClient, ChatExecutionResult, ChatStreamResult, LlmExecutionResult
from app.llm.prompts import PromptRepository
from app.schemas.event import ConjunctionEvent, LlmSuggestion


def _strip_code_fences(content: str) -> str:
    stripped = content.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    return stripped.strip()


def _parse_suggestion_payload(
    text: str,
    *,
    model_name: str,
    provider_name: str,
) -> LlmSuggestion:
    cleaned = _strip_code_fences(text)
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError:
        payload = {}

    if not isinstance(payload, dict):
        payload = {}

    return LlmSuggestion(
        recommendation_text=str(payload.get("recommendation_text") or cleaned or "模型未返回有效建议，请人工复核。").strip(),
        reasoning_summary=str(payload.get("reasoning_summary") or "模型未提供额外说明。").strip(),
        confidence_hint=str(payload.get("confidence_hint") or "模型生成").strip(),
        risk_level=str(payload.get("risk_level") or "unknown").strip(),
        needs_manual_review=payload.get("needs_manual_review") if isinstance(payload.get("needs_manual_review"), bool) else None,
        model_name=model_name,
        provider_name=provider_name,
        used_mock=False,
    )


def _chunk_text(text: str, size: int = 18) -> Iterator[str]:
    for index in range(0, len(text), size):
        yield text[index:index + size]


class MockLLMClient(BaseLLMClient):
    """Deterministic fallback when a live model is unavailable."""

    provider_name = "mock"

    def __init__(self) -> None:
        self.prompts = PromptRepository()

    def generate_suggestion(
        self,
        event: ConjunctionEvent,
        user_requirement: str | None = None,
    ) -> LlmExecutionResult:
        bundle = self.prompts.render_action_prompt(event, user_requirement=user_requirement)
        suggestion = LlmSuggestion(
            recommendation_text="实时大模型不可用，不能完成模型风险判定。建议转人工复核并补充最新会合数据。",
            reasoning_summary="系统已停止程序规则判定；当前 fallback 不替代大模型判断。",
            confidence_hint="低",
            risk_level="unknown",
            needs_manual_review=True,
            model_name="mock-template",
            provider_name=self.provider_name,
            used_mock=True,
        )
        return LlmExecutionResult(
            suggestion=suggestion,
            prompt_text=bundle.audit_text,
            response_text=suggestion.model_dump_json(indent=2),
            prompt_name=bundle.prompt_name,
            prompt_lang=bundle.prompt_lang,
        )

    def generate_final_report(self, task_context: dict) -> ChatExecutionResult:
        bundle = self.prompts.render_report_prompt(task_context)
        events = task_context.get("events") or []
        user_requirement = task_context.get("user_requirement") or "未提供"
        event = events[0] if events else {}
        evidence_items = [
            ("事件编号", event.get("event_id")),
            ("最近接时刻（TCA）", event.get("tca_utc")),
            ("最近接距离", event.get("miss_distance_m")),
            ("碰撞概率（Pc）", event.get("collision_probability")),
        ]
        evidence = "；".join(
            f"{label}：{value}" for label, value in evidence_items if value not in (None, "")
        ) or "暂无可引用事件字段"
        report = (
            "## 原因\n"
            f"{user_requirement}。当前实时大模型不可用，系统只能给出回退摘要。\n\n"
            "## 判据\n"
            f"可用证据：{evidence}。回退摘要不替代正式模型研判。\n\n"
            "## 结论\n"
            "风险等级暂未确定，需要人工复核。\n\n"
            "## 建议\n"
            "补充最新 CDM、协方差、任务约束和外部轨道上下文后，重新调用大模型生成正式研判报告。"
        )
        return ChatExecutionResult(
            reply_text=report,
            prompt_text=bundle.audit_text,
            response_text=report,
            prompt_name=bundle.prompt_name,
            prompt_lang=bundle.prompt_lang,
            provider_name=self.provider_name,
            model_name="mock-template",
            used_mock=True,
        )

    def generate_chat_reply(
        self,
        *,
        user_message: str,
        history: list[dict],
        task_context: dict,
    ) -> ChatExecutionResult:
        bundle = self.prompts.render_chat_prompt(
            user_message=user_message,
            history=history,
            task_context=task_context,
        )
        report_excerpt = task_context.get("report_excerpt")
        if report_excerpt:
            reply = f"以下基于当前任务报告回答：\n\n{report_excerpt[:1200]}"
        else:
            reply = "任务结果尚未生成完整报告。请等待任务完成后继续追问，或查看日志确认解析是否成功。"
        return ChatExecutionResult(
            reply_text=reply,
            prompt_text=bundle.audit_text,
            response_text=reply,
            prompt_name=bundle.prompt_name,
            prompt_lang=bundle.prompt_lang,
            provider_name=self.provider_name,
            model_name="mock-template",
            used_mock=True,
        )

    def stream_chat_reply(
        self,
        *,
        user_message: str,
        history: list[dict],
        task_context: dict,
    ) -> ChatStreamResult:
        execution = self.generate_chat_reply(
            user_message=user_message,
            history=history,
            task_context=task_context,
        )
        return ChatStreamResult(
            chunks=_chunk_text(execution.reply_text),
            prompt_text=execution.prompt_text,
            prompt_name=execution.prompt_name,
            prompt_lang=execution.prompt_lang,
            provider_name=execution.provider_name,
            model_name=execution.model_name,
            used_mock=True,
        )


class OpenAICompatibleLLMClient(BaseLLMClient):
    """OpenAI-compatible chat completions client."""

    provider_name = "openai_compatible"

    def __init__(self) -> None:
        self.settings = get_settings()
        self.fallback = MockLLMClient()
        self.prompts = PromptRepository()

    def generate_suggestion(
        self,
        event: ConjunctionEvent,
        user_requirement: str | None = None,
    ) -> LlmExecutionResult:
        bundle = self.prompts.render_action_prompt(event, user_requirement=user_requirement)
        model_name = self.settings.llm_model_for_action or self.settings.model_name
        if not (self.settings.base_url and self.settings.api_key and model_name):
            return self.fallback.generate_suggestion(event, user_requirement=user_requirement)

        payload = self._payload(model_name, bundle.system_prompt, bundle.user_prompt)
        try:
            text = self._post_chat(payload)
            suggestion = _parse_suggestion_payload(
                text,
                model_name=model_name,
                provider_name=self.provider_name,
            )
            return LlmExecutionResult(
                suggestion=suggestion,
                prompt_text=bundle.audit_text,
                response_text=text,
                prompt_name=bundle.prompt_name,
                prompt_lang=bundle.prompt_lang,
            )
        except Exception:
            return self.fallback.generate_suggestion(event, user_requirement=user_requirement)

    def generate_final_report(self, task_context: dict) -> ChatExecutionResult:
        bundle = self.prompts.render_report_prompt(task_context)
        model_name = self.settings.llm_model_for_report or self.settings.model_name
        if not (self.settings.base_url and self.settings.api_key and model_name):
            return self.fallback.generate_final_report(task_context)

        payload = self._payload(model_name, bundle.system_prompt, bundle.user_prompt)
        try:
            text = self._post_chat(payload)
            return ChatExecutionResult(
                reply_text=text,
                prompt_text=bundle.audit_text,
                response_text=text,
                prompt_name=bundle.prompt_name,
                prompt_lang=bundle.prompt_lang,
                provider_name=self.provider_name,
                model_name=model_name,
                used_mock=False,
            )
        except Exception:
            return self.fallback.generate_final_report(task_context)

    def generate_chat_reply(
        self,
        *,
        user_message: str,
        history: list[dict],
        task_context: dict,
    ) -> ChatExecutionResult:
        stream = self.stream_chat_reply(user_message=user_message, history=history, task_context=task_context)
        text = "".join(stream.chunks)
        return ChatExecutionResult(
            reply_text=text,
            prompt_text=stream.prompt_text,
            response_text=text,
            prompt_name=stream.prompt_name,
            prompt_lang=stream.prompt_lang,
            provider_name=stream.provider_name,
            model_name=stream.model_name,
            used_mock=stream.used_mock,
        )

    def stream_chat_reply(
        self,
        *,
        user_message: str,
        history: list[dict],
        task_context: dict,
    ) -> ChatStreamResult:
        bundle = self.prompts.render_chat_prompt(
            user_message=user_message,
            history=history,
            task_context=task_context,
        )
        model_name = self.settings.llm_model_for_review or self.settings.model_name
        if not (self.settings.base_url and self.settings.api_key and model_name):
            return self.fallback.stream_chat_reply(
                user_message=user_message,
                history=history,
                task_context=task_context,
            )

        payload = self._payload(model_name, bundle.system_prompt, bundle.user_prompt)
        payload["stream"] = True

        return ChatStreamResult(
            chunks=self._stream_chat(payload, user_message, history, task_context),
            prompt_text=bundle.audit_text,
            prompt_name=bundle.prompt_name,
            prompt_lang=bundle.prompt_lang,
            provider_name=self.provider_name,
            model_name=model_name,
            used_mock=False,
        )

    def _payload(self, model_name: str, system_prompt: str, user_prompt: str) -> dict:
        return {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self.settings.llm_temperature,
            "max_tokens": self.settings.llm_max_tokens,
            "top_p": self.settings.llm_top_p,
        }

    def _post_chat(self, payload: dict) -> str:
        response = httpx.post(
            f"{self.settings.base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {self.settings.api_key}"},
            json=payload,
            timeout=self.settings.llm_timeout,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()

    def _stream_chat(
        self,
        payload: dict,
        user_message: str,
        history: list[dict],
        task_context: dict,
    ) -> Iterator[str]:
        try:
            with httpx.stream(
                "POST",
                f"{self.settings.base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {self.settings.api_key}"},
                json=payload,
                timeout=self.settings.llm_timeout,
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data_text = line.removeprefix("data:").strip()
                    if data_text == "[DONE]":
                        break
                    try:
                        data = json.loads(data_text)
                    except json.JSONDecodeError:
                        continue
                    token = data.get("choices", [{}])[0].get("delta", {}).get("content")
                    if token:
                        yield token
        except Exception:
            fallback = self.fallback.stream_chat_reply(
                user_message=user_message,
                history=history,
                task_context=task_context,
            )
            yield from fallback.chunks


def build_llm_client() -> BaseLLMClient:
    """Return the configured LLM client."""

    settings = get_settings()
    if settings.llm_enabled and settings.llm_provider == "openai_compatible":
        return OpenAICompatibleLLMClient()
    return MockLLMClient()
