$rule_policy

请基于以下任务上下文生成一份精简值班报告。

格式固定为：
## 原因

说明触发本次预警或需要关注的直接原因。

## 判据

列出用于判断的关键字段、证据、阈值或不确定性。

## 结论

给出风险判断和是否需要人工复核。

## 建议

给出值班人员下一步可执行动作。

字段中文化要求：
- message_id：消息编号
- conjunction_id：会合事件编号
- primary_object_name：主目标
- secondary_object_name：次目标
- primary_norad_id / secondary_norad_id：主目标/次目标 NORAD 编号
- tca_utc：最近接时刻（TCA）
- miss_distance_m：最近接距离
- relative_speed_mps：相对速度
- collision_probability：碰撞概率（Pc）
- reference_frame：参考坐标系
- covariance_present：是否包含协方差
- risk_level：风险等级
- needs_manual_review：是否需要人工复核

请在正文中使用上面的中文名称，不要直接堆英文 JSON 字段名。每个小节控制在 1 到 3 个短段落或项目符号内。

任务上下文：
$task_context_json
