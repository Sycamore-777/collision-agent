export type ApiEnvelope<T> = {
  success: boolean;
  message: string;
  data: T;
  error: { code: string; details?: unknown } | null;
  timestamp: string;
};

export type TaskSummary = {
  task_id: string;
  task_type: string;
  status: string;
  created_at: string;
  updated_at: string;
  latest_risk_level?: string | null;
  event_count: number;
};

export type TaskInputSpec = {
  input_type: string;
  source_uri?: string | null;
  source_name?: string | null;
  content_type?: string | null;
  local_path?: string | null;
  confidentiality?: string | null;
  file_hash?: string | null;
};

export type TraceStep = {
  step_name: string;
  step_status: string;
  started_at: string;
  finished_at?: string | null;
  latency_ms?: number | null;
  input_ref?: string | null;
  output_ref?: string | null;
  error_code?: string | null;
  error_message?: string | null;
  retry_count: number;
};

export type EvidenceRef = {
  doc_id: string;
  page?: number | null;
  element_id?: string | null;
  quote?: string | null;
  field_name: string;
};

export type ConjunctionEvent = {
  event_id: string;
  message_id?: string | null;
  conjunction_id?: string | null;
  primary_object_name?: string | null;
  secondary_object_name?: string | null;
  primary_norad_id?: string | null;
  secondary_norad_id?: string | null;
  tca_utc?: string | null;
  miss_distance_m?: number | null;
  relative_speed_mps?: number | null;
  collision_probability?: number | null;
  reference_frame?: string | null;
  covariance_present: boolean;
  risk_level: string;
  action_recommendation?: string | null;
  needs_manual_review: boolean;
  evidence_refs: EvidenceRef[];
  external_context?: Record<string, unknown>;
  llm_suggestion?: {
    recommendation_text: string;
    reasoning_summary: string;
    confidence_hint?: string;
    risk_level?: string | null;
    needs_manual_review?: boolean | null;
    model_name: string;
    provider_name: string;
    used_mock: boolean;
  } | null;
};

export type ParsedDocument = {
  doc_id: string;
  doc_type: string;
  source: string;
  parser_name: string;
  confidence_summary: {
    overall: number;
    parser_backend: string;
    fallback_used: boolean;
    notes: string[];
  };
  elements: Array<{
    element_id: string;
    page?: number | null;
    kind: string;
    label: string;
    text: string;
    value?: string | number | boolean | null;
    confidence: number;
  }>;
};

export type TaskDetail = {
  task_id: string;
  task_type: string;
  user_requirement?: string | null;
  status: string;
  created_at: string;
  updated_at: string;
  finished_at?: string | null;
  error_message?: string | null;
  inputs: TaskInputSpec[];
  parsed_documents: ParsedDocument[];
  events: ConjunctionEvent[];
  step_logs: TraceStep[];
  artifacts: Record<string, string>;
};

export type TaskResult = {
  task_id: string;
  status: string;
  task_type: string;
  user_requirement?: string | null;
  parsed_documents: ParsedDocument[];
  events: ConjunctionEvent[];
  event_threads: Record<string, string[]>;
  generated_at: string;
  degraded_modes: string[];
  artifacts: Record<string, string>;
};

export type TaskReport = {
  task_id: string;
  markdown: string;
  html: string;
  result_json_path: string;
  trace_json_path: string;
};

export type TaskTrace = {
  task_id: string;
  final_status: string;
  steps: TraceStep[];
  errors: string[];
  retries: number;
  metadata: Record<string, unknown>;
};

export type LlmCallSummary = {
  id: string;
  step_name: string;
  provider_name: string;
  model_name: string;
  status: string;
  created_at: string;
  prompt_text: string;
  response_text: string;
  prompt_name?: string | null;
  prompt_lang?: string | null;
  parsed_output_json: Record<string, unknown>;
};

export type ChatMessage = {
  id: string;
  task_id: string;
  role: "user" | "assistant" | string;
  content: string;
  attachments: Array<Record<string, unknown>>;
  llm_call_id?: string | null;
  created_at: string;
};
