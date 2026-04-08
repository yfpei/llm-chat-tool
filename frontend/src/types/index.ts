export interface ApiKeyConfig {
  id: number
  name: string
  provider: 'openai' | 'anthropic'
  base_url: string
  model: string
  max_context_tokens: number
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
}

export interface Conversation {
  id: string
  title: string
  api_key_id: number | null
  created_at: string
  updated_at: string
}

export interface Message {
  id: number
  role: 'user' | 'assistant' | 'system'
  content: string
  created_at: string
}

export interface ConversationDetail extends Conversation {
  messages: Message[]
}

export interface ChatEvent {
  type: 'chunk' | 'done' | 'error'
  content: string
}
