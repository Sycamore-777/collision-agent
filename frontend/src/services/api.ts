import type {
  ApiEnvelope,
  ChatMessage,
  LlmCallSummary,
  TaskDetail,
  TaskReport,
  TaskResult,
  TaskSummary,
  TaskTrace
} from "../types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

const apiErrorMap: Record<string, string> = {
  validation_failure: "输入不完整，请至少提供需求说明、文件、URL 或内联载荷。",
  not_found: "请求的任务不存在，或对应产物尚未生成。",
  collision_agent_error: "任务处理失败，请检查输入内容或稍后重试。",
  Request_failed: "请求失败，请检查后端服务是否启动。"
};

function translateApiError(code?: string | null, message?: string | null): string {
  if (code && apiErrorMap[code]) {
    return apiErrorMap[code];
  }
  if (message && apiErrorMap[message]) {
    return apiErrorMap[message];
  }
  if (message?.includes("Failed to fetch")) {
    return "无法连接后端服务，请确认 API 已启动。";
  }
  return message ?? "请求失败，请稍后重试。";
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, init);
    const payload = (await response.json()) as ApiEnvelope<T>;
    if (!response.ok || !payload.success) {
      throw new Error(translateApiError(payload.error?.code, payload.message));
    }
    return payload.data;
  } catch (error) {
    if (error instanceof Error) {
      throw new Error(translateApiError(undefined, error.message));
    }
    throw new Error("请求失败，请稍后重试。");
  }
}

async function readStream(response: Response, onChunk: (chunk: string) => void): Promise<string> {
  if (!response.ok || !response.body) {
    throw new Error("流式回复失败，请检查后端服务。");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let fullText = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }
    const chunk = decoder.decode(value, { stream: true });
    fullText += chunk;
    onChunk(chunk);
  }

  const tail = decoder.decode();
  if (tail) {
    fullText += tail;
    onChunk(tail);
  }
  return fullText;
}

export async function createTask(formData: FormData): Promise<{ task_id: string; status: string; created_at: string }> {
  return request("/v1/tasks", {
    method: "POST",
    body: formData
  });
}

export async function fetchTasks(): Promise<TaskSummary[]> {
  return request("/v1/tasks");
}

export async function fetchTaskDetail(taskId: string): Promise<TaskDetail> {
  return request(`/v1/tasks/${taskId}`);
}

export async function fetchTaskResult(taskId: string): Promise<TaskResult> {
  return request(`/v1/tasks/${taskId}/result`);
}

export async function fetchTaskReport(taskId: string): Promise<TaskReport> {
  return request(`/v1/tasks/${taskId}/report`);
}

export async function fetchTaskTrace(taskId: string): Promise<TaskTrace> {
  return request(`/v1/tasks/${taskId}/trace`);
}

export async function fetchTaskLlmCalls(taskId: string): Promise<LlmCallSummary[]> {
  return request(`/v1/tasks/${taskId}/llm-calls`);
}

export async function fetchTaskChat(taskId: string): Promise<ChatMessage[]> {
  return request(`/v1/tasks/${taskId}/chat`);
}

export async function sendTaskChat(taskId: string, content: string): Promise<ChatMessage> {
  return request(`/v1/tasks/${taskId}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content })
  });
}

export async function streamTaskChat(
  taskId: string,
  content: string,
  onChunk: (chunk: string) => void,
  options: { persistUser?: boolean } = {}
): Promise<string> {
  const response = await fetch(`${API_BASE_URL}/v1/tasks/${taskId}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      content,
      persist_user: options.persistUser ?? true
    })
  });
  return readStream(response, onChunk);
}

export async function streamTaskChatForm(
  taskId: string,
  content: string,
  files: File[],
  onChunk: (chunk: string) => void
): Promise<string> {
  const formData = new FormData();
  formData.append("content", content);
  files.forEach((file) => formData.append("files", file));

  const response = await fetch(`${API_BASE_URL}/v1/tasks/${taskId}/chat/stream-form`, {
    method: "POST",
    body: formData
  });
  return readStream(response, onChunk);
}
