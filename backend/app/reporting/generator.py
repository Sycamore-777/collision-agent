"""Generate Markdown and HTML reports from result payloads."""

from __future__ import annotations

from app.schemas.task import ReportPayload, ResultPayload
from app.reporting.markdown import markdown_to_html, normalize_report_markdown


class ReportGenerator:
    """Create human-readable report artifacts."""

    def render(self, result: ResultPayload, trace_path: str, result_path: str) -> tuple[str, str]:
        degraded_mode_labels = {
            "external_context_fallback": "外部上下文回退",
            "llm_mock_fallback": "大模型 Mock 回退",
            "url_fetch_fallback": "URL 抓取回退",
        }
        degraded_modes = (
            "、".join(degraded_mode_labels.get(mode, mode) for mode in result.degraded_modes)
            if result.degraded_modes
            else "无"
        )
        event_lines: list[str] = []
        for event in result.events:
            event_lines.append(
                "\n".join(
                    [
                        f"- 事件：{event.primary_object_name} 与 {event.secondary_object_name}",
                        f"  最近接时刻（TCA）：{event.tca_utc}",
                        f"  最近接距离：{event.miss_distance_m} 米",
                        f"  碰撞概率（Pc）：{event.collision_probability}",
                        f"  风险等级：{event.risk_level}",
                        f"  是否需要人工复核：{'是' if event.needs_manual_review else '否'}",
                    ]
                )
            )

        markdown = "\n\n".join(
            [
                "## 原因",
                f"用户需求：{result.user_requirement or '未提供'}。系统已完成任务输入解析、事件提取和报告生成。",
                "## 判据",
                "\n\n".join(event_lines) if event_lines else "暂无可展示的碰撞事件。",
                "## 结论",
                f"任务状态为 {result.status}。降级模式：{degraded_modes}。",
                "## 建议",
                f"请在值班台核对结果文件和追溯文件：结果文件 {result_path}；追溯文件 {trace_path}。",
            ]
        )
        markdown = normalize_report_markdown(markdown)
        html = markdown_to_html(markdown)
        return markdown, html
