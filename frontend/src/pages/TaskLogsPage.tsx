import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { Panel } from "../components/Panel";
import { StepTimeline } from "../components/StepTimeline";
import { fetchTaskLlmCalls, fetchTaskResult, fetchTaskTrace } from "../services/api";
import type { LlmCallSummary, TaskResult, TaskTrace } from "../types";
import { formatDateTime, formatFieldLabel, formatStatusLabel, formatWorkflowStep } from "../utils/labels";

export function TaskLogsPage() {
  const { taskId = "" } = useParams();
  const [trace, setTrace] = useState<TaskTrace | null>(null);
  const [llmCalls, setLlmCalls] = useState<LlmCallSummary[]>([]);
  const [result, setResult] = useState<TaskResult | null>(null);

  useEffect(() => {
    async function load() {
      const [traceData, llmData, resultData] = await Promise.all([
        fetchTaskTrace(taskId),
        fetchTaskLlmCalls(taskId),
        fetchTaskResult(taskId).catch(() => null)
      ]);
      setTrace(traceData);
      setLlmCalls(llmData);
      setResult(resultData);
    }

    void load();
  }, [taskId]);

  return (
    <div className="stack">
      <Panel title="工作流日志" subtitle="查看任务编排过程中的逐步状态、输入输出和错误信息。">
        {trace ? <StepTimeline steps={trace.steps} /> : <p className="muted">正在加载执行轨迹...</p>}
      </Panel>

      <Panel title="模型调用审计" subtitle="查看实际提示词、原始模型响应和结构化解析结果。">
        {!llmCalls.length ? <p className="muted">当前还没有记录到模型调用。</p> : null}
        <div className="stack">
          {llmCalls.map((call) => (
            <article className="summary-card" key={call.id}>
              <div className="timeline-row">
                <strong>{formatWorkflowStep(call.step_name)}</strong>
                <span>{call.provider_name} / {call.model_name}</span>
              </div>
              <p className="muted">
                调用时间：{formatDateTime(call.created_at)} | 状态：{formatStatusLabel(call.status)}
              </p>
              {call.prompt_name || call.prompt_lang ? (
                <p className="muted">
                  模板：{call.prompt_name ?? "action"} / {call.prompt_lang ?? "zh-CN"}
                </p>
              ) : null}
              <div className="stack">
                <div>
                  <strong>提示词</strong>
                  <pre className="preformatted">{call.prompt_text}</pre>
                </div>
                <div>
                  <strong>原始响应</strong>
                  <pre className="preformatted">{call.response_text}</pre>
                </div>
                <div>
                  <strong>结构化结果</strong>
                  <pre className="preformatted">{JSON.stringify(call.parsed_output_json, null, 2)}</pre>
                </div>
              </div>
            </article>
          ))}
        </div>
      </Panel>

      <Panel title="证据链" subtitle="按事件查看字段来源、元素编号和原文片段，便于人工复核。">
        {!result?.events.length ? <p className="muted">当前还没有证据链数据。</p> : null}
        <div className="stack">
          {result?.events.map((event) => (
            <article className="summary-card" key={event.event_id}>
              <div className="timeline-row">
                <strong>{event.primary_object_name} vs {event.secondary_object_name}</strong>
                <span>{event.event_id}</span>
              </div>
              <div className="evidence-grid">
                {event.evidence_refs.map((evidence) => (
                  <div className="timeline-item" key={`${evidence.doc_id}-${evidence.element_id}-${evidence.field_name}`}>
                    <p><strong>字段：</strong>{formatFieldLabel(evidence.field_name)}</p>
                    <p><strong>文档：</strong>{evidence.doc_id}</p>
                    <p><strong>页码：</strong>{evidence.page ?? "未知"}</p>
                    <p><strong>元素：</strong>{evidence.element_id ?? "未知"}</p>
                    {evidence.quote ? <p className="muted">摘录：{evidence.quote}</p> : null}
                  </div>
                ))}
              </div>
            </article>
          ))}
        </div>
      </Panel>
    </div>
  );
}
