import type { EsExportTask, EsPreviewResult } from '../types'

const API_BASE = '/api/es-export'

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || res.statusText)
  }
  return res.json()
}

export async function createTask(data: {
  title?: string
  es_host: string
  es_username?: string
  es_password?: string
}): Promise<EsExportTask> {
  return request<EsExportTask>(`${API_BASE}/tasks`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function listTasks(): Promise<EsExportTask[]> {
  return request<EsExportTask[]>(`${API_BASE}/tasks`)
}

export async function getTask(taskId: string): Promise<EsExportTask> {
  return request<EsExportTask>(`${API_BASE}/tasks/${taskId}`)
}

export async function updateTask(
  taskId: string,
  data: {
    title?: string
    es_host?: string
    es_username?: string
    es_password?: string
    index_name?: string
    query_dsl?: string
    output_fields?: string
    config_json?: string
  },
): Promise<EsExportTask> {
  return request<EsExportTask>(`${API_BASE}/tasks/${taskId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteTask(taskId: string): Promise<void> {
  await request(`${API_BASE}/tasks/${taskId}`, { method: 'DELETE' })
}

export async function testConnection(taskId: string): Promise<{ ok: boolean; info: { version: string; cluster_name: string } }> {
  return request(`${API_BASE}/tasks/${taskId}/test-connection`, { method: 'POST' })
}

export async function listIndices(taskId: string): Promise<{ indices: string[] }> {
  return request(`${API_BASE}/tasks/${taskId}/indices`)
}

export async function getMapping(taskId: string, index: string): Promise<{ fields: Record<string, string> }> {
  return request(`${API_BASE}/tasks/${taskId}/mapping?index=${encodeURIComponent(index)}`)
}

export async function previewQuery(
  taskId: string,
  data: {
    query_dsl?: Record<string, unknown>
    output_fields?: string[]
    page?: number
    page_size?: number
    top_n?: number
  },
): Promise<EsPreviewResult> {
  return request<EsPreviewResult>(`${API_BASE}/tasks/${taskId}/preview`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function getExportUrl(taskId: string): string {
  return `${API_BASE}/tasks/${taskId}/export`
}

export function getDownloadUrl(taskId: string): string {
  return `${API_BASE}/tasks/${taskId}/download`
}

export function getFileDownloadUrl(fileId: string): string {
  return `${API_BASE}/files/${fileId}/download`
}
