import type { Conversation, ConversationDetail } from '../types'

const BASE = '/api/conversations'

export async function fetchConversations(): Promise<Conversation[]> {
  const res = await fetch(BASE)
  return res.json()
}

export async function createConversation(title?: string): Promise<Conversation> {
  const res = await fetch(BASE, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title }),
  })
  return res.json()
}

export async function getConversation(id: string): Promise<ConversationDetail> {
  const res = await fetch(`${BASE}/${id}`)
  return res.json()
}

export async function updateConversation(id: string, data: { title?: string; api_key_id?: number }): Promise<Conversation> {
  const res = await fetch(`${BASE}/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  return res.json()
}

export async function deleteConversation(id: string): Promise<void> {
  await fetch(`${BASE}/${id}`, { method: 'DELETE' })
}
