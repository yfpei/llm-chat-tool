import type { ApiKeyConfig, ApiKeyCreateRequest } from '../types'

const BASE = '/api/keys'

export async function fetchKeys(): Promise<ApiKeyConfig[]> {
  const res = await fetch(BASE)
  return res.json()
}

export async function createKey(data: ApiKeyCreateRequest): Promise<ApiKeyConfig> {
  const res = await fetch(BASE, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  return res.json()
}

export async function updateKey(id: number, data: Partial<ApiKeyCreateRequest>): Promise<ApiKeyConfig> {
  const res = await fetch(`${BASE}/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  return res.json()
}

export async function deleteKey(id: number): Promise<void> {
  await fetch(`${BASE}/${id}`, { method: 'DELETE' })
}

export async function verifyKey(id: number): Promise<{ is_valid: boolean; message: string }> {
  const res = await fetch(`${BASE}/${id}/verify`, { method: 'POST' })
  return res.json()
}

export async function activateKey(id: number): Promise<ApiKeyConfig> {
  const res = await fetch(`${BASE}/${id}/activate`, { method: 'POST' })
  return res.json()
}
