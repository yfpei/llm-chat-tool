import type { ApiKeyConfig, ApiKeyCreateRequest } from '../types'
import { authFetch } from './client'

const BASE = '/api/keys'

export async function fetchKeys(): Promise<ApiKeyConfig[]> {
  const res = await authFetch(BASE)
  return res.json()
}

export async function createKey(data: ApiKeyCreateRequest): Promise<ApiKeyConfig> {
  const res = await authFetch(BASE, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  return res.json()
}

export async function updateKey(id: number, data: Partial<ApiKeyCreateRequest>): Promise<ApiKeyConfig> {
  const res = await authFetch(`${BASE}/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  return res.json()
}

export async function deleteKey(id: number): Promise<void> {
  await authFetch(`${BASE}/${id}`, { method: 'DELETE' })
}

export async function verifyKey(id: number): Promise<{ is_valid: boolean; message: string }> {
  const res = await authFetch(`${BASE}/${id}/verify`, { method: 'POST' })
  return res.json()
}

export async function activateKey(id: number): Promise<ApiKeyConfig> {
  const res = await authFetch(`${BASE}/${id}/activate`, { method: 'POST' })
  return res.json()
}

export async function setKeyOverride(keyId: number, data: { enable_thinking?: boolean | null; max_context_tokens?: number | null }): Promise<void> {
  await authFetch(`${BASE}/${keyId}/overrides`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}
