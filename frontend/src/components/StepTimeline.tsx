import type { TraceStep } from "../types";
import { formatDateTime, formatWorkflowStep } from "../utils/labels";
import { StatusBadge } from "./StatusBadge";

export function StepTimeline({ steps }: { steps: TraceStep[] }) {
  if (!steps.length) {
    return <p className="muted">当前还没有记录到工作流步骤。</p>;
  }

  return (
    <div className="timeline">
      {steps.map((step) => (
        <article className="timeline-item" key={`${step.step_name}-${step.started_at}`}>
          <div className="timeline-row">
            <strong>{formatWorkflowStep(step.step_name)}</strong>
            <StatusBadge value={step.step_status} />
          </div>
          <p className="muted">
            开始时间：{formatDateTime(step.started_at)} | 耗时：{step.latency_ms ?? 0} ms
          </p>
          {step.input_ref ? <p>输入：{step.input_ref}</p> : null}
          {step.output_ref ? <p>输出：{step.output_ref}</p> : null}
          {step.error_message ? <p className="error-text">错误：{step.error_message}</p> : null}
        </article>
      ))}
    </div>
  );
}
