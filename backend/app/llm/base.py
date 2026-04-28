"""LLM client abstractions."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass

from app.schemas.event import ConjunctionEvent, LlmSuggestion


@dataclass(slots=True)
class LlmExecutionResult:
    """Complete LLM execution record for audit and persistence."""

    suggestion: LlmSuggestion
    prompt_text: str
    response_text: str
    prompt_name: str = "action"
    prompt_lang: str = "zh-CN"


@dataclass(slots=True)
class ChatExecutionResult:
    """Complete chat/report execution record for audit and persistence."""

    reply_text: str
    prompt_text: str
    response_text: str
    prompt_name: str = "chat"
    prompt_lang: str = "zh-CN"
    provider_name: str = "mock"
    model_name: str = "mock-template"
    used_mock: bool = False


@dataclass(slots=True)
class ChatStreamResult:
    """Streaming chat reply plus immutable audit metadata."""

    chunks: Iterator[str]
    prompt_text: str
    prompt_name: str = "chat"
    prompt_lang: str = "zh-CN"
    provider_name: str = "mock"
    model_name: str = "mock-template"
    used_mock: bool = False


class BaseLLMClient(ABC):
    """Contract for LLM-backed suggestion providers."""

    provider_name: str = "base"

    @abstractmethod
    def generate_suggestion(
        self,
        event: ConjunctionEvent,
        user_requirement: str | None = None,
    ) -> LlmExecutionResult:
        """Generate model-driven event judgment and recommendation."""

    def generate_final_report(self, task_context: dict) -> ChatExecutionResult:
        """Generate the final task report as model text."""

        raise NotImplementedError

    def generate_chat_reply(
        self,
        *,
        user_message: str,
        history: list[dict],
        task_context: dict,
    ) -> ChatExecutionResult:
        """Generate a task-scoped chat reply."""

        raise NotImplementedError

    def stream_chat_reply(
        self,
        *,
        user_message: str,
        history: list[dict],
        task_context: dict,
    ) -> ChatStreamResult:
        """Stream a task-scoped chat reply."""

        raise NotImplementedError
