import { startTransition, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { createTask } from "../services/api";

export function TaskCreatePage() {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [taskType, setTaskType] = useState("collision_warning");
  const [userRequirement, setUserRequirement] = useState("");
  const [url, setUrl] = useState("");
  const [inlinePayload, setInlinePayload] = useState("");
  const [files, setFiles] = useState<FileList | null>(null);
  const [enableExternalContext, setEnableExternalContext] = useState(true);
  const [enableLlmSuggestion, setEnableLlmSuggestion] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);

    const formData = new FormData();
    formData.append("task_type", taskType);
    if (userRequirement.trim()) {
      formData.append("user_requirement", userRequirement.trim());
    }
    if (url.trim()) {
      formData.append("url", url.trim());
    }
    if (inlinePayload.trim()) {
      formData.append("inline_payload", inlinePayload.trim());
    }
    formData.append(
      "options_json",
      JSON.stringify({
        enable_external_context: enableExternalContext,
        enable_llm_suggestion: enableLlmSuggestion,
        enable_report_generation: true,
        enable_manual_review_route: true
      })
    );

    Array.from(files ?? []).forEach((file) => formData.append("files", file));

    try {
      const task = await createTask(formData);
      startTransition(() => navigate(`/tasks/${task.task_id}/chat`));
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "任务创建失败，请稍后重试。");
    } finally {
      setSubmitting(false);
    }
  }

  const selectedFiles = Array.from(files ?? []);

  return (
    <section className="command-page">
      <div className="command-hero">
        <p className="eyebrow">ORBITAL SAFETY CONSOLE</p>
        <h1>任务指令台</h1>
        <p>
          上传会合消息、约束文件或任务说明，系统将完成解析、证据链、模型研判和四段式报告。
        </p>
      </div>

      <form className="command-console" onSubmit={handleSubmit}>
        <div className="console-grid">
          <label className="command-input">
            <span>需求说明</span>
            <textarea
              aria-label="需求说明"
              placeholder="例如：请评估这次会合风险，说明是否需要人工复核，并给出值班人员可执行的处置建议。"
              rows={7}
              value={userRequirement}
              onChange={(event) => setUserRequirement(event.target.value)}
            />
          </label>

          <aside className="drop-zone">
            <input
              ref={fileInputRef}
              className="visually-hidden"
              multiple
              type="file"
              onChange={(event) => setFiles(event.target.files)}
            />
            <button type="button" onClick={() => fileInputRef.current?.click()}>
              选择任务文件
            </button>
            <p>支持 CDM、KVN、XML、TXT、JSON、PDF、DOCX、PPTX。</p>
            <div className="attached-files">
              {selectedFiles.length ? (
                selectedFiles.map((file) => (
                  <span className="file-chip" key={`${file.name}-${file.size}`}>
                    {file.name}
                  </span>
                ))
              ) : (
                <span className="muted">尚未选择附件</span>
              )}
            </div>
          </aside>
        </div>

        <details className="advanced-settings">
          <summary>高级设置</summary>
          <div className="form-grid compact">
            <label>
              任务类型
              <input value={taskType} onChange={(event) => setTaskType(event.target.value)} />
            </label>
            <label>
              URL 输入
              <input placeholder="https://..." value={url} onChange={(event) => setUrl(event.target.value)} />
            </label>
            <label className="full-span">
              内联载荷
              <textarea
                rows={7}
                placeholder='{"message_id":"CDM-...","collision_probability":1.2e-4}'
                value={inlinePayload}
                onChange={(event) => setInlinePayload(event.target.value)}
              />
            </label>
            <label className="checkbox">
              <input
                type="checkbox"
                checked={enableExternalContext}
                onChange={(event) => setEnableExternalContext(event.target.checked)}
              />
              启用外部上下文补全
            </label>
            <label className="checkbox">
              <input
                type="checkbox"
                checked={enableLlmSuggestion}
                onChange={(event) => setEnableLlmSuggestion(event.target.checked)}
              />
              启用大模型研判
            </label>
          </div>
        </details>

        <div className="command-footer">
          {error ? <p className="error-text">{error}</p> : <p className="muted">发送后进入任务会话，可继续追问或追加文件重跑。</p>}
          <button className="primary-button" disabled={submitting} type="submit">
            {submitting ? "正在创建任务..." : "发送并创建任务"}
          </button>
        </div>
      </form>
    </section>
  );
}
