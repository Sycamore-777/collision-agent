# Prompt Templates

可编辑提示词统一放在 `prompts/` 目录下，当前已经接入的模板为：

- `action/system.zh-CN.md`
- `action/user.zh-CN.md`
- `chat/system.zh-CN.md`
- `chat/user.zh-CN.md`
- `report/system.zh-CN.md`
- `report/user.zh-CN.md`

约定：

- `system` 用于系统角色约束。
- `user` 用于任务输入和事件上下文。
- 支持通过 `PROMPT_DIR` 和 `PROMPT_LANG` 切换目录与语言。
- 当前模板变量：
  - `$event_json`
  - `$strict_json_instruction`
  - `$rule_policy`
  - `$user_requirement`
  - `$user_message`
  - `$task_context_json`
  - `$history_json`

风险等级、人工复核、处置建议和最终报告的判定规则都应写入提示词，由大模型执行；程序只负责解析事实、调用模型、落库和展示。
