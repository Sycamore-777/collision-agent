const valueLabels: Record<string, string> = {
  pending: "待处理",
  running: "运行中",
  succeeded: "已完成",
  failed: "失败",
  manual_review: "待人工复核",
  critical: "极高",
  high: "高",
  medium: "中",
  low: "低",
  unknown: "未知",
  succeeded_step: "成功",
  failed_step: "失败"
};

const degradedModeLabels: Record<string, string> = {
  external_context_fallback: "外部上下文回退",
  llm_mock_fallback: "大模型 Mock 回退",
  url_fetch_fallback: "URL 抓取回退",
  llm_disabled_manual_review: "大模型关闭，转人工复核"
};

const parserLabels: Record<string, string> = {
  structured_input_parser: "结构化输入解析器",
  mineru_adapter: "MinerU 适配器",
  mock_parser: "Mock 解析器"
};

const fieldLabels: Record<string, string> = {
  message_id: "消息 ID",
  conjunction_id: "会合 ID",
  primary_object_name: "主目标名称",
  secondary_object_name: "次目标名称",
  primary_norad_id: "主目标 NORAD",
  secondary_norad_id: "次目标 NORAD",
  tca_utc: "最近接时刻",
  miss_distance_m: "最小距离",
  relative_speed_mps: "相对速度",
  collision_probability: "碰撞概率",
  reference_frame: "参考坐标系",
  covariance_present: "协方差可用性"
};

export function formatStatusLabel(value: string | null | undefined): string {
  if (!value) {
    return "未知";
  }
  return valueLabels[value] ?? value;
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) {
    return "暂无";
  }
  return new Date(value).toLocaleString("zh-CN");
}

export function formatBooleanZh(value: boolean): string {
  return value ? "是" : "否";
}

export function formatTaskType(value: string): string {
  if (value === "collision_warning") {
    return "碰撞预警";
  }
  return value;
}

export function formatParserBackend(value: string): string {
  return parserLabels[value] ?? value;
}

export function formatDegradedMode(value: string): string {
  return degradedModeLabels[value] ?? value;
}

export function formatFieldLabel(value: string): string {
  return fieldLabels[value] ?? value;
}

export function formatWorkflowStep(value: string): string {
  if (value.startsWith("parse_")) {
    return `解析输入：${value.replace("parse_", "")}`;
  }
  if (value === "extract_events") {
    return "提取碰撞事件";
  }
  if (value.startsWith("context_")) {
    return `外部上下文：${value.replace("context_", "").slice(0, 8)}`;
  }
  if (value === "llm_final_report") {
    return "大模型最终报告";
  }
  if (value.startsWith("llm_")) {
    return `大模型研判：${value.replace("llm_", "").slice(0, 8)}`;
  }
  if (value === "generate_outputs") {
    return "生成结果产物";
  }
  if (value === "task_failed") {
    return "任务失败";
  }
  return value;
}
