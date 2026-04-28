import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { MarkdownView } from "../components/MarkdownView";
import { StatusBadge } from "../components/StatusBadge";
import { fetchTaskChat, fetchTaskDetail, streamTaskChat, streamTaskChatForm } from "../services/api";
import type { ChatMessage, TaskDetail } from "../types";
import { formatDateTime } from "../utils/labels";

export function TaskChatPage() {
  const { taskId = "" } = useParams();
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const chatThreadRef = useRef<HTMLDivElement | null>(null);
  const [detail, setDetail] = useState<TaskDetail | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [content, setContent] = useState("");
  const [files, setFiles] = useState<FileList | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const streamingRef = useRef(false);
  const finalReportStartedRef = useRef(false);

  async function load() {
    const [detailData, chatData] = await Promise.all([
      fetchTaskDetail(taskId),
      fetchTaskChat(taskId)
    ]);
    setDetail(detailData);
    if (!streamingRef.current) {
      setMessages(chatData);
    }
  }

  useEffect(() => {
    void load();
    const timer = window.setInterval(() => {
      void load();
    }, 5000);
    return () => window.clearInterval(timer);
  }, [taskId]);

  useEffect(() => {
    const completed = detail?.status === "succeeded" || detail?.status === "manual_review";
    const hasFinalReport = messages.some(
      (message) => message.role === "assistant" && message.content.includes("## 原因")
    );
    if (!completed || hasFinalReport || finalReportStartedRef.current || streamingRef.current) {
      return;
    }
    finalReportStartedRef.current = true;
    void runStreamingReply("请基于当前任务结果生成最终报告，并按原因、判据、结论、建议四段输出。", {
      persistUser: false,
      showUser: false,
      files: []
    });
  }, [detail?.status, messages, taskId]);

  useEffect(() => {
    const element = chatThreadRef.current;
    if (element) {
      element.scrollTop = element.scrollHeight;
    }
  }, [messages]);

  async function runStreamingReply(
    message: string,
    options: { persistUser: boolean; showUser: boolean; files: File[] }
  ) {
    const assistantId = `local-assistant-${Date.now()}`;
    const localMessages: ChatMessage[] = [];
    if (options.showUser) {
      localMessages.push({
        id: `local-user-${Date.now()}`,
        task_id: taskId,
        role: "user",
        content: message,
        attachments: options.files.map((file) => ({ name: file.name, type: "followup_file" })),
        created_at: new Date().toISOString()
      });
    }
    localMessages.push({
      id: assistantId,
      task_id: taskId,
      role: "assistant",
      content: "",
      attachments: [],
      created_at: new Date().toISOString()
    });

    streamingRef.current = true;
    setSubmitting(true);
    setError(null);
    setMessages((current) => [...current, ...localMessages]);

    try {
      const onChunk = (chunk: string) => {
        setMessages((current) =>
          current.map((item) =>
            item.id === assistantId ? { ...item, content: `${item.content}${chunk}` } : item
          )
        );
      };

      if (options.files.length) {
        await streamTaskChatForm(taskId, message, options.files, onChunk);
      } else {
        await streamTaskChat(taskId, message, onChunk, { persistUser: options.persistUser });
      }

      streamingRef.current = false;
      await load();
    } catch (submitError) {
      streamingRef.current = false;
      setError(submitError instanceof Error ? submitError.message : "追问失败，请稍后重试。");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const message = content.trim();
    const selectedFiles = Array.from(files ?? []);
    if ((!message && !selectedFiles.length) || streamingRef.current) {
      return;
    }
    setContent("");
    setFiles(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
    await runStreamingReply(message || "请基于新上传文件重新分析。", {
      persistUser: true,
      showUser: true,
      files: selectedFiles
    });
  }

  const selectedFiles = Array.from(files ?? []);

  return (
    <section className="chat-workspace with-inspector">
      <aside className="task-inspector">
        <div>
          <span className="muted">任务</span>
          <strong>{taskId}</strong>
        </div>
        <div>
          <span className="muted">状态</span>
          <StatusBadge value={detail?.status} />
        </div>
        <div>
          <span className="muted">需求说明</span>
          <p>{detail?.user_requirement || "未提供"}</p>
        </div>
        <div className="inline-actions vertical">
          <Link to={`/tasks/${taskId}`}>任务详情</Link>
          <Link to={`/tasks/${taskId}/logs`}>日志与证据</Link>
        </div>
      </aside>

      <div className="chat-main">
        <div className="chat-thread" ref={chatThreadRef}>
          {!messages.length ? (
            <article className="message-row assistant">
              <div className="message-bubble">
                <strong>碰撞预警助手</strong>
                <MarkdownView content="任务已创建。等待结果生成后，可以继续追问风险、证据链和报告摘要。" />
              </div>
            </article>
          ) : null}
          {messages.map((message) => (
            <article className={`message-row ${message.role === "user" ? "user" : "assistant"}`} key={message.id}>
              <div className="message-bubble">
                <strong>{message.role === "user" ? "你" : "碰撞预警助手"}</strong>
                <MarkdownView content={message.content || "正在生成..."} />
                {message.attachments.length ? (
                  <div className="attached-files">
                    {message.attachments.map((attachment, index) => (
                      <span className="file-chip" key={`${message.id}-${index}`}>
                        {String(attachment.name ?? attachment.type ?? "附件")}
                      </span>
                    ))}
                  </div>
                ) : null}
                <small>{formatDateTime(message.created_at)}</small>
              </div>
            </article>
          ))}
        </div>

        <form className="composer-shell compact-composer" onSubmit={handleSubmit}>
          <textarea
            aria-label="继续追问"
            className="chat-input"
            placeholder="继续追问，或上传新版 CDM / 约束文件后要求重新分析。"
            rows={3}
            value={content}
            onChange={(event) => setContent(event.target.value)}
          />
          {selectedFiles.length ? (
            <div className="attached-files">
              {selectedFiles.map((file) => (
                <span className="file-chip" key={`${file.name}-${file.size}`}>{file.name}</span>
              ))}
            </div>
          ) : null}
          <div className="composer-actions">
            <input
              ref={fileInputRef}
              className="visually-hidden"
              multiple
              type="file"
              onChange={(event) => setFiles(event.target.files)}
            />
            <button type="button" onClick={() => fileInputRef.current?.click()}>
              追加文件
            </button>
            <button className="primary-button" disabled={submitting} type="submit">
              {submitting ? "生成中..." : "发送追问"}
            </button>
          </div>
          {error ? <p className="error-text">{error}</p> : null}
        </form>
      </div>
    </section>
  );
}
