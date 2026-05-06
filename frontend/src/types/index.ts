export interface ApiKeyConfig {
  id: number
  name: string
  provider: 'openai' | 'anthropic'
  base_url: string
  model: string
  max_context_tokens: number
  enable_thinking: boolean
  is_xinghuo_x1: boolean
  is_active: boolean
  is_valid: boolean
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
  is_xinghuo_x1?: boolean
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
  progress_completed: number
  progress_total: number
  created_at: string
  updated_at: string
}
