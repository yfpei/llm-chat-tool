export interface AuthUser {
  id: number
  username: string
  role: 'admin' | 'user'
  active_key_id?: number | null
}

export interface AuthResponse {
  access_token: string
  user: AuthUser
}

export interface UserInfo {
  id: number
  username: string
  role: string
  is_active: boolean
  created_at: string
}

export interface ApiKeyConfig {
  id: number
  name: string
  provider: 'openai' | 'anthropic'
  base_url: string
  model: string
  max_context_tokens: number
  enable_thinking: boolean
  model_type?: string | null
  is_active: boolean
  is_valid: boolean
  user_id?: number | null
  created_at: string
}

export interface ApiKeyCreateRequest {
  name: string
  provider: 'openai' | 'anthropic'
  base_url: string
  api_key: string
  model: string
  max_context_tokens: number
  enable_thinking: boolean
  model_type?: string | null
}

export interface Conversation {
  id: string
  title: string
  api_key_id: number | null
  created_at: string
  updated_at: string
}

export interface TokenUsage {
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
  tokens_per_second?: number
}

export interface Message {
  id: number
  role: 'user' | 'assistant' | 'system'
  content: string
  created_at: string
  usage?: TokenUsage
}

export interface ConversationDetail extends Conversation {
  messages: Message[]
}

export interface ChatEvent {
  type: 'chunk' | 'done' | 'error' | 'usage'
  content: string | TokenUsage
}

// ── Batch Types ──────────────────────────────

export interface UploadResponse {
  task_id: string
  file_id: string
  filename: string
  columns: string[]
  headers: string[]
  total_rows: number
  preview: PreviewRow[]
}

export interface PreviewRow {
  row: number
  cells: Record<string, string>
}

export interface FilterCondition {
  field: string
  operator: 'contains' | 'equals' | 'gt' | 'lt' | 'gte' | 'lte' | 'not_empty' | 'is_empty'
  value: string
}

export interface FilterGroup {
  logic: 'and' | 'or'
  conditions: FilterCondition[]
}

export interface FilterConfig {
  top_n?: number | null
  groups: FilterGroup[]
  logic: 'and' | 'or'
}

export interface BatchRunConfig {
  task_id: string
  file_id: string
  input_columns: string[]
  output_column_name: string
  prompt: string
  api_key_id: number
  concurrency: number
  strip_thinking: boolean
  parse_json: boolean
  filter?: FilterConfig | null
}

export interface BatchEvent {
  type: 'progress' | 'row_result' | 'row_error' | 'done' | 'error'
  completed?: number
  total?: number
  row?: number
  input?: string
  output?: string
  error?: string
  success?: boolean
  task_id?: string
  content?: string
  parsed?: Record<string, string>
}

export interface BatchTask {
  id: string
  title: string
  file_id: string
  filename: string
  columns: string
  headers: string
  total_rows: number
  status: 'uploaded' | 'running' | 'completed' | 'failed'
  config_json: string | null
  eval_config_json: string | null
  source: 'batch' | 'eval'
  progress_completed: number
  progress_total: number
  created_at: string
  updated_at: string
}

// ── Eval Types ────────────────────────────────

export interface MappingRule {
  model_output: string
  label_value: string
}

export interface ClassificationEvalConfig {
  label_column: string
  predict_column: string
  mappings: MappingRule[]
}

export interface LLMScoringEvalConfig {
  api_key_id: number
  prompt: string
  input_columns: string[]
  output_column_name: string
  concurrency: number
}

export interface EvalConfigData {
  enabled: boolean
  method: 'classification' | 'llm_scoring' | 'both'
  classification?: ClassificationEvalConfig | null
  llm_scoring?: LLMScoringEvalConfig | null
}

export interface PerClassMetric {
  class_name: string
  precision: number | null
  recall: number | null
  f1: number | null
}

export interface AvgMetric {
  precision: number
  recall: number
  f1: number
}

export interface ClassificationEvalResult {
  accuracy: number
  total_samples: number
  num_classes: number
  confusion_matrix: number[][]
  labels: string[]
  per_class: PerClassMetric[]
  micro_avg: AvgMetric
  macro_avg: AvgMetric
  skipped_count: number
}

export interface LLMScoringEvalEvent {
  type: 'progress' | 'row_result' | 'row_error' | 'done' | 'error'
  completed?: number
  total?: number
  row?: number
  score?: string
  error?: string
  avg_score?: number
  message?: string
}

// ── ES Export Types ───────────────────────────

export interface EsExportTask {
  id: string
  title: string
  es_host: string
  es_username?: string | null
  index_name?: string | null
  query_dsl?: string | null
  output_fields?: string | null
  status: 'created' | 'running' | 'completed' | 'failed'
  total_hits: number
  exported_count: number
  file_id?: string | null
  config_json?: string | null
  created_at?: string | null
  updated_at?: string | null
}

export interface EsPreviewResult {
  total: number
  rows: Record<string, unknown>[]
  fields: string[]
}

// ── MySQL Export Types ──────────────────────

export interface MySQLExportTask {
  id: string
  title: string
  mysql_host: string
  mysql_port: number
  mysql_username?: string | null
  database_name?: string | null
  table_name?: string | null
  where_clause?: string | null
  custom_sql?: string | null
  output_columns?: string | null
  status: 'created' | 'running' | 'completed' | 'failed'
  total_rows: number
  exported_count: number
  file_id?: string | null
  config_json?: string | null
  created_at?: string | null
  updated_at?: string | null
}

export interface MySQLPreviewResult {
  total: number
  rows: Record<string, unknown>[]
  fields: string[]
}
