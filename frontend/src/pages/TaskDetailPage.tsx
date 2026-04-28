import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { MarkdownView } from "../components/MarkdownView";
import { Panel } from "../components/Panel";
import { StatusBadge } from "../components/StatusBadge";
import { fetchTaskDetail, fetchTaskReport, fetchTaskResult } from "../services/api";
import type { TaskDetail, TaskReport, TaskResult } from "../types";
import {
  formatBooleanZh,
  formatDateTime,
  formatDegradedMode,
  formatParserBackend,
  formatTaskType
} from "../utils/labels";

export function TaskDetailPage() {
  const { taskId = "" } = useParams();
  const [detail, setDetail] = useState<TaskDetail | null>(null);
  const [result, setResult] = useState<TaskResult | null>(null);
  const [report, setReport] = useState<TaskReport | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      const [detailData, resultData, reportData] = await Promise.all([
        fetchTaskDetail(taskId),
        fetchTaskResult(taskId).catch(() => null),
        fetchTaskReport(taskId).catch(() => null)
      ]);
      if (!cancelled) {
        setDetail(detailData);
        setResult(resultData);
        setReport(reportData);
      }
    }

    void load();
    const timer = window.setInterval(() => {
      void load();
    }, 5000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [taskId]);

  if (!detail) {
    return <p className="muted">正在加载任务详情...</p>;
  }

  return (
    <div className="stack">
      <Panel
        title={`任务 ${detail.task_id}`}
        subtitle="结构化事件、解析产物、降级模式和模型报告集中展示。"
        actions={
          <div className="inline-actions">
            <Link to={`/tasks/${detail.task_id}/chat`}>继续问答</Link>
            <Link to={`/tasks/${detail.task_id}/logs`}>日志与证据链</Link>
          </div>
        }
      >
        <div className="grid two-columns">
          <div className="summary-card">
            <span className="muted">任务状态</span>
            <StatusBadge value={detail.status} />
          </div>
          <div className="summary-card">
            <span className="muted">任务类型</span>
            <strong>{formatTaskType(detail.task_type)}</strong>
          </div>
          <div className="summary-card">
            <span className="muted">创建时间</span>
            <strong>{formatDateTime(detail.created_at)}</strong>
          </div>
          <div className="summary-card">
            <span className="muted">输入数量</span>
            <strong>{detail.inputs.length}</strong>
          </div>
          <div className="summary-card full-span">
            <span className="muted">需求说明</span>
            <strong>{detail.user_requirement || "未提供"}</strong>
          </div>
          <div className="summary-card full-span">
            <span className="muted">降级模式</span>
            <strong>
              {result?.degraded_modes.length
                ? result.degraded_modes.map((mode) => formatDegradedMode(mode)).join("、")
                : "无"}
            </strong>
          </div>
        </div>
      </Panel>

      <Panel title="碰撞事件" subtitle="模型风险判断、人工复核标记和证据摘要。">
        {!result?.events.length ? <p className="muted">当前还没有提取到事件。</p> : null}
        <div className="stack">
          {result?.events.map((event) => (
            <article className="event-card" key={event.event_id}>
              <div className="timeline-row">
                <strong>{event.primary_object_name} vs {event.secondary_object_name}</strong>
                <StatusBadge value={event.risk_level} />
              </div>
              <p className="muted">
                TCA：{formatDateTime(event.tca_utc)} | 最小距离：{event.miss_distance_m ?? "暂无"} m | Pc：{event.collision_probability ?? "暂无"}
              </p>
              <p>模型处置建议：{event.action_recommendation ?? "暂无"}</p>
              <p>是否人工复核：{formatBooleanZh(event.needs_manual_review)}</p>
              {event.llm_suggestion ? (
                <div className="stack">
                  <p>
                    大模型建议：{event.llm_suggestion.recommendation_text}
                    {event.llm_suggestion.used_mock ? "（Mock 回退）" : ""}
                  </p>
                  <p className="muted">建议依据：{event.llm_suggestion.reasoning_summary}</p>
                </div>
              ) : null}
            </article>
          ))}
        </div>
      </Panel>

      <Panel title="解析文档" subtitle="查看归一化文档元素和解析器来源。">
        <div className="stack">
          {detail.parsed_documents.map((document) => (
            <article className="summary-card" key={document.doc_id}>
              <strong>{document.source}</strong>
              <p className="muted">
                {document.doc_type} | 解析器：{formatParserBackend(document.parser_name)} | 置信度：{document.confidence_summary.overall}
              </p>
              <p>{document.elements.slice(0, 3).map((element) => element.text).join(" | ")}</p>
            </article>
          ))}
        </div>
      </Panel>

      <Panel title="报告预览" subtitle="Markdown 已渲染，固定为原因、判据、结论、建议四段。">
        {report ? (
          <div className="report-preview">
            <MarkdownView content={report.markdown} />
          </div>
        ) : (
          <p className="muted">报告尚未生成。</p>
        )}
      </Panel>
    </div>
  );
}
