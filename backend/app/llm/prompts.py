"""Prompt template loading and rendering helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from string import Template

from app.core.config import get_settings
from app.schemas.event import ConjunctionEvent


RULE_POLICY = """模型判定规则：
- risk_level 只能是 critical、high、medium、low、unknown。
- 若 collision_probability >= 1e-3 或 miss_distance_m <= 500，通常判为 critical。
- 若 collision_probability >= 1e-4 或 miss_distance_m <= 1000，通常判为 high。
- 若 collision_probability >= 1e-5 或 miss_distance_m <= 5000，通常判为 medium。
- 其余信息充分且风险较低时可判为 low。
- 如果缺少 message_id、tca_utc、miss_distance_m、collision_probability，或者 covariance_present 为 false，应倾向 needs_manual_review=true。
- 如果任务约束与事件字段冲突，应说明冲突并倾向 needs_manual_review=true。
- 以上规则由你在提示词中执行，系统不再使用程序规则覆盖你的判断。"""


FALLBACK_TEMPLATES: dict[tuple[str, str], str] = {
    ("action", "system"): (
        "你是碰撞预警 Data Agent 的轨道安全分析模型。\n"
        "你必须始终使用简体中文输出，不要编造原始事件中不存在的事实。\n"
        "$strict_json_instruction"
    ),
    ("action", "user"): (
        "$rule_policy\n\n"
        "用户需求说明：$user_requirement\n\n"
        "标准化碰撞事件数据：\n$event_json\n\n"
        "请由你判断风险等级、是否需要人工复核，并生成值班人员可执行的建议。"
    ),
    ("report", "system"): (
        "你是碰撞预警 Data Agent 的值班报告撰写模型。\n"
        "始终使用简体中文，直接输出 Markdown。只允许输出四个二级小节：原因、判据、结论、建议。\n"
        "每个标题必须独占一行，标题后空一行再写正文。参数优先使用中文名称，例如碰撞概率（Pc）、最近接时刻（TCA）、最近接距离、相对速度、协方差。"
    ),
    ("report", "user"): (
        "$rule_policy\n\n"
        "请基于以下任务上下文生成精简值班报告，格式固定为：\n"
        "## 原因\n\n正文。\n\n## 判据\n\n正文。\n\n## 结论\n\n正文。\n\n## 建议\n\n正文。\n\n"
        "不要把标题和正文写在同一行。不要直接堆英文 JSON 字段名。\n\n"
        "$task_context_json"
    ),
    ("chat", "system"): (
        "你是碰撞预警 Data Agent 的任务问答助手。\n"
        "始终使用简体中文回答，只能基于任务结果、报告、证据链和历史对话进行解释。\n"
        "如用户要求报告，必须输出原因、判据、结论、建议四个 Markdown 二级小节，标题独占一行，参数优先中文化。"
    ),
    ("chat", "user"): (
        "$rule_policy\n\n"
        "用户最新问题：$user_message\n\n"
        "任务上下文：\n$task_context_json\n\n"
        "历史对话：\n$history_json\n\n"
        "请像 ChatGPT 一样直接回答用户问题。若输出报告，标题和正文必须分行，并尽量使用中文参数名。"
    ),
}


@dataclass(slots=True)
class PromptBundle:
    """Rendered prompt pair ready for an LLM call."""

    prompt_name: str
    prompt_lang: str
    system_prompt: str
    user_prompt: str

    @property
    def audit_text(self) -> str:
        return f"[system]\n{self.system_prompt}\n\n[user]\n{self.user_prompt}"


class PromptRepository:
    """Load editable prompt templates from the project prompt directory."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.prompt_root = Path(self.settings.prompt_dir)

    def render_action_prompt(
        self,
        event: ConjunctionEvent,
        user_requirement: str | None = None,
    ) -> PromptBundle:
        lang = self.settings.prompt_lang or "zh-CN"
        context = {
            "event_json": json.dumps(event.model_dump(mode="json"), ensure_ascii=False, default=str, indent=2),
            "strict_json_instruction": self._strict_json_instruction(),
            "user_requirement": user_requirement or "未提供",
            "rule_policy": RULE_POLICY,
        }
        return self._render_bundle("action", lang, context)

    def render_report_prompt(self, task_context: dict) -> PromptBundle:
        lang = self.settings.prompt_lang or "zh-CN"
        context = {
            "task_context_json": json.dumps(task_context, ensure_ascii=False, default=str, indent=2),
            "rule_policy": RULE_POLICY,
        }
        return self._render_bundle("report", lang, context)

    def render_chat_prompt(
        self,
        *,
        user_message: str,
        history: list[dict],
        task_context: dict,
    ) -> PromptBundle:
        lang = self.settings.prompt_lang or "zh-CN"
        context = {
            "user_message": user_message,
            "history_json": json.dumps(history, ensure_ascii=False, default=str, indent=2),
            "task_context_json": json.dumps(task_context, ensure_ascii=False, default=str, indent=2),
            "rule_policy": RULE_POLICY,
        }
        return self._render_bundle("chat", lang, context)

    def _render_bundle(self, prompt_name: str, lang: str, context: dict[str, str]) -> PromptBundle:
        return PromptBundle(
            prompt_name=prompt_name,
            prompt_lang=lang,
            system_prompt=self._render_template(prompt_name, "system", lang, context),
            user_prompt=self._render_template(prompt_name, "user", lang, context),
        )

    def _strict_json_instruction(self) -> str:
        if self.settings.prompt_strict_json:
            return (
                "你必须只返回一个 JSON 对象，字段固定为 "
                "recommendation_text、reasoning_summary、confidence_hint、risk_level、needs_manual_review。"
                "不要输出 Markdown 代码块，不要添加额外解释。"
            )
        return "你可以输出简洁的自然语言，但仍需保持结构清晰。"

    def _render_template(
        self,
        prompt_name: str,
        role: str,
        lang: str,
        context: dict[str, str],
    ) -> str:
        template_text = self._read_template(prompt_name, role, lang)
        return Template(template_text).safe_substitute(context).strip()

    def _read_template(self, prompt_name: str, role: str, lang: str) -> str:
        for candidate in self._candidate_paths(prompt_name, role, lang):
            if candidate.exists():
                return candidate.read_text(encoding="utf-8")
        return FALLBACK_TEMPLATES[(prompt_name, role)]

    def _candidate_paths(self, prompt_name: str, role: str, lang: str) -> list[Path]:
        names = [
            f"{role}.{lang}.md",
            f"{role}.{lang}.txt",
            f"{role}.zh-CN.md",
            f"{role}.zh-CN.txt",
            f"{role}.md",
            f"{role}.txt",
        ]
        prompt_dir = self.prompt_root / prompt_name
        return [prompt_dir / name for name in names]
