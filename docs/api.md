# API Reference

## Task APIs

### `POST /v1/tasks`

Multipart form fields:

- `task_type`
- `user_requirement`
- `url`
- `inline_payload`
- `options_json`
- `files`

Example:

```bash
curl -X POST http://localhost:8000/v1/tasks \
  -F "task_type=collision_warning" \
  -F "inline_payload={\"message_id\":\"CDM-001\"}"
```

### `GET /v1/tasks`

Returns all tasks ordered by creation time.

### `GET /v1/tasks/{task_id}`

Returns task detail, parsed document summaries, events, step logs, and artifact pointers.

### `GET /v1/tasks/{task_id}/result`

Returns the structured result payload.

### `GET /v1/tasks/{task_id}/report`

Returns Markdown and HTML report content plus artifact paths.

### `GET /v1/tasks/{task_id}/trace`

Returns the trace JSON payload.

### `GET /v1/tasks/{task_id}/llm-calls`

Returns LLM audit logs, including:

- rendered `prompt_text`
- raw `response_text`
- `prompt_name` and `prompt_lang`
- parsed structured output

### `GET /v1/tasks/{task_id}/chat`

Returns task-scoped chat messages, including the initial requirement and follow-up replies.

### `POST /v1/tasks/{task_id}/chat`

Creates a follow-up message and returns the assistant reply.

```json
{
  "content": "为什么需要人工复核？证据来自哪里？",
  "attachments": []
}
```

## System APIs

- `GET /healthz`
- `GET /metrics`

## Evaluation API

### `POST /v1/eval/run`

Creates and runs a task using local mock data, then returns the generated artifact paths.

## Error Format

All errors use the standard envelope:

```json
{
  "success": false,
  "message": "未找到任务 abc。",
  "data": null,
  "error": {
    "code": "not_found",
    "details": null
  },
  "timestamp": "2026-04-22T12:00:00Z"
}
```
