$rule_policy

请基于以下标准化碰撞事件数据，由大模型自行完成风险等级、人工复核和处置建议判断。系统不会再用程序规则覆盖你的判断。

用户需求说明：
$user_requirement

输出要求：
只返回一个 JSON 对象，不要使用 Markdown 代码块，字段固定为：
1. risk_level：只能是 critical、high、medium、low、unknown。
2. needs_manual_review：布尔值，表示是否需要人工复核。
3. recommendation_text：一句到三句，给出明确处置建议。
4. reasoning_summary：简要解释依据，指出风险、缺失信息、证据来源或需要复核的原因。
5. confidence_hint：给出“高”“中”“低”之一。

标准化事件数据：
$event_json
