# 人工验收测试用例

本目录包含 10 个可在前端对话框中直接使用的验收用例。每个用例目录都包含：

- `case.json`：智能问答输入、需要上传的文件、后续追问和预期结果。
- `README.md`：人工操作说明。
- `inputs/`：该用例需要上传的测试文件。

## 启动

后端：

```powershell
conda activate Competition
cd D:\Program\python\MinerU_Competition\collision-agent
uvicorn app.main:app --app-dir backend --reload --host 0.0.0.0 --port 8000
```

前端：

```powershell
conda activate Competition
cd D:\Program\python\MinerU_Competition\collision-agent\frontend
npm run dev
```

打开 `http://localhost:5173`，将 `case.json` 中的 `initial_question` 粘贴到需求说明框，将 `files` 中列出的文件上传，然后点击“发送并创建任务”。任务生成后进入问答页，按 `follow_up_questions` 继续追问。

## 验收要点

- 任务能创建并进入任务问答页。
- 报告、结果、Trace、证据链可打开。
- `/llm-calls` 审计中能看到 prompt 和原始响应。
- 后续追问能产生助手回复，并写入聊天记录。
