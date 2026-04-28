# 碰撞预警 Data Agent

这是一个本地单体全栈项目，用于碰撞预警数据处理和问答式研判。系统支持上传 CDM、KVN、XML、TXT、JSON 等文件，后端完成解析、字段抽取、事件聚合和外部上下文补全，大模型根据 `prompts/` 中可编辑提示词完成风险判断、人工复核建议、连续问答和最终报告生成。

## 正常启动方式

推荐使用两个终端分别启动后端和前端。所有命令都使用本机 `Competition` conda 环境。

### 第一次运行前安装依赖

在项目目录执行：

```powershell
cd D:\Program\python\MinerU_Competition\collision-agent
conda run -n Competition python -m pip install -e .[dev]
cd frontend
conda run -n Competition npm install
```

### 终端 1：启动后端

```powershell
cd D:\Program\python\MinerU_Competition\collision-agent
conda run -n Competition alembic -c backend/alembic.ini upgrade head
conda run --no-capture-output -n Competition uvicorn app.main:app --app-dir backend --reload --host 0.0.0.0 --port 8000
```

本地 `.env` 中的 `ALLOWED_ORIGINS` 应同时包含 `localhost` 和 `127.0.0.1`：

```env
ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

如果修改过 `.env`，需要重启后端服务，配置才会生效。否则浏览器可能看到“无法连接后端服务”，但后端日志里仍显示 `POST /v1/tasks 200 OK`，这是 CORS 拦截导致的典型表现。

后端接口文档：

```text
http://localhost:8000/docs
```

### 终端 2：启动前端

```powershell
cd D:\Program\python\MinerU_Competition\collision-agent\frontend
conda run --no-capture-output -n Competition npm run dev
```

不要再追加旧参数 `-- --host 0.0.0.0 --port 5173`。如果终端输出里出现类似下面这一行：

```text
vite --host 127.0.0.1 --port 5173 --strictPort 0.0.0.0 5173
```

说明旧参数被拼到了新脚本后面，Vite 可能会把 `0.0.0.0` 当成项目根目录，结果就是服务启动了但 `/` 返回 404。

前端页面：

```text
http://127.0.0.1:5173
```

前端启动成功时，终端应看到类似输出：

```text
VITE ready
Local:   http://127.0.0.1:5173/
```

如果浏览器打开 `http://localhost:5173/` 显示 `HTTP ERROR 404`，先改用 `http://127.0.0.1:5173/`。Windows 上 `localhost` 可能受 IPv6、代理、浏览器缓存或其它本地服务影响，`127.0.0.1` 更直接。

如果 `127.0.0.1` 仍然异常，先确认前端终端没有退出，并且确实打印了 `VITE ready`。然后在第三个终端执行：

```powershell
curl.exe -I http://127.0.0.1:5173/
```

正常应返回 `HTTP/1.1 200 OK`。如果返回 404，说明 `5173` 端口上响应的不是当前 Vite 前端，或者启动目录不对。按下面方式排查：

```powershell
netstat -ano | findstr :5173
```

如果看到已有 PID 占用端口，查看它是谁：

```powershell
tasklist /FI "PID eq 进程号"
```

确认不是当前 Vite 进程后，可以结束它：

```powershell
taskkill /PID 进程号 /F
```

然后重新启动前端。当前项目已把 `host=127.0.0.1`、`port=5173` 和 `strictPort=true` 固化到 Vite 配置与 `npm run dev` 脚本中，如果 `5173` 被占用，Vite 会直接报错，不会悄悄切到 `5174`，这样可以避免打开错端口。

## 如何使用

打开前端后，首页就是类似 ChatGPT 的任务入口：

1. 在输入框中写需求说明，例如“请评估这次会合风险，说明是否需要人工复核，并给出值班人员可执行的处置建议”。
2. 点击“上传文件”，上传 CDM、KVN、XML、TXT、JSON 等输入文件。
3. 如需 URL、内联载荷或开关配置，展开“高级设置”。
4. 点击“发送并创建任务”。
5. 进入任务会话页后，可以继续追问，例如“为什么需要复核？”、“证据来自哪里？”、“给我一份汇报摘要”。

任务完成后，大模型会在会话中生成最终报告。任务详情页可以查看结构化结果、报告预览、日志和证据链。

### 追问时追加文件

在任务会话页底部点击“追加文件”，选择新版 CDM、约束文件或补充材料后发送追问。系统会把新文件加入当前任务输入，清理旧的解析结果、事件、报告、trace 和模型审计记录，然后重新解析并生成最新结果。聊天历史会保留，新的回答基于重跑后的结果流式输出。

### 报告格式

最终报告和“生成报告”类追问统一使用 Markdown 渲染，并固定为四段：

- `原因`
- `判据`
- `结论`
- `建议`

如果未配置真实大模型，Mock/fallback 报告也会遵守这四段结构。

## 测试命令

后端测试：

```powershell
cd D:\Program\python\MinerU_Competition\collision-agent
conda run -n Competition pytest backend/tests
```

前端测试：

```powershell
cd D:\Program\python\MinerU_Competition\collision-agent\frontend
conda run -n Competition npm test
```

前端构建：

```powershell
cd D:\Program\python\MinerU_Competition\collision-agent\frontend
conda run -n Competition npm run build
```

如果你在 `D:\Program\python\MinerU_Competition` 根目录运行测试，不要写 `pytest backend/tests`，因为这个目录不存在。应进入 `collision-agent` 后再运行，或直接运行：

```powershell
cd D:\Program\python\MinerU_Competition
conda run -n Competition pytest
```

## 大模型配置

默认没有真实大模型配置时，系统会自动 fallback，不中断主流程。配置真实 OpenAI-compatible 服务时，修改 `.env`：

```env
LLM_ENABLED=true
LLM_PROVIDER=openai_compatible
BASE_URL=https://your-openai-compatible-endpoint/v1
API_KEY=your_api_key
MODEL_NAME=your_model
```

可按用途分别配置模型槽位：

```env
LLM_MODEL_FOR_ACTION=your_action_model
LLM_MODEL_FOR_REPORT=your_report_model
LLM_MODEL_FOR_REVIEW=your_chat_model
```

## 提示词目录

提示词全部暴露在 `prompts/`，可以直接修改，不需要改后端代码：

- `prompts/action/system.zh-CN.md`
- `prompts/action/user.zh-CN.md`
- `prompts/chat/system.zh-CN.md`
- `prompts/chat/user.zh-CN.md`
- `prompts/report/system.zh-CN.md`
- `prompts/report/user.zh-CN.md`

风险等级、人工复核、处置建议和最终报告的判断规则都应写入提示词，由大模型执行。程序只负责解析事实、调用模型、落库和展示。

## MinerU 接入

MinerU 当前用于 PDF、DOCX、PPTX 这类非结构化任务文件解析。路由位置是：

```text
ParserRegistry -> MinerUAdapter -> ParsedDocument.elements
```

默认 `PARSER_BACKEND=mock` 时，PDF、DOCX、PPTX 会进入 MinerUAdapter，但实际使用 MockParser fallback，并在解析摘要和 trace 中标记降级。要接入真实 MinerU 服务，修改 `.env`：

```env
PARSER_BACKEND=mineru
MINERU_BASE_URL=http://localhost:你的MinerU服务端口
MINERU_API_KEY=
MINERU_TIMEOUT=120
```

后端会向 `MINERU_BASE_URL/parse` 发送文件表单，期望返回 JSON。返回中如果包含 `elements` 或 `blocks`，系统会把它们转换为统一的 `ParsedDocument.elements`；如果只包含 `markdown`、`text` 或 `content`，系统会按文本块转换。每个元素都会生成 `element_id`，后续证据链可以引用这些元素。

本版本不建立长期知识库。原因是 CDM、任务约束和会合态势通常是任务级时效数据，应该直接进入当前任务链路；知识库更适合后续存放长期有效材料，例如处置规范、卫星背景资料、值班手册和历史案例。

## 项目结构

- `backend/`：FastAPI 后端、数据库模型、任务编排、迁移和测试。
- `frontend/`：Vite + React + TypeScript 前端。
- `data/`：上传文件、解析产物、报告、trace 和 mock 数据。
- `prompts/`：大模型提示词模板。
- `docs/`：架构、API、部署和开发文档。
- `scripts/`：辅助脚本。
- `test/`：人工验收和演示用例。

## 可选脚本

仓库中保留了 `start.sh`、`start.ps1`、`start.cmd`，但它们不是推荐启动方式。Windows 下脚本会受 shell、conda 激活方式和权限影响，调试时建议优先使用上面的“两终端命令”。
