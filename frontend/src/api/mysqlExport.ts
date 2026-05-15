import type { MySQLExportTask, MySQLPreviewResult } from '../types'
import { authFetch } from './client'

const API_BASE = '/api/mysql-export'

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await authFetch(url, {
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
  mysql_host: string
  mysql_port?: number
  mysql_username?: string
  mysql_password?: string
}): Promise<MySQLExportTask> {
  return request<MySQLExportTask>(`${API_BASE}/tasks`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function listTasks(): Promise<MySQLExportTask[]> {
  return request<MySQLExportTask[]>(`${API_BASE}/tasks`)
}

export async function getTask(taskId: string): Promise<MySQLExportTask> {
  return request<MySQLExportTask>(`${API_BASE}/tasks/${taskId}`)
}

export async function updateTask(
  taskId: string,
  data: {
    title?: string
    mysql_host?: string
    mysql_port?: number
    mysql_username?: string
    mysql_password?: string
    database_name?: string
    table_name?: string
    where_clause?: string
    custom_sql?: string
    output_columns?: string
    config_json?: string
  },
): Promise<MySQLExportTask> {
  return request<MySQLExportTask>(`${API_BASE}/tasks/${taskId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteTask(taskId: string): Promise<void> {
  await request(`${API_BASE}/tasks/${taskId}`, { method: 'DELETE' })
}

export async function testConnection(taskId: string): Promise<{ ok: boolean; info: { version: string } }> {
  return request(`${API_BASE}/tasks/${taskId}/test-connection`, { method: 'POST' })
}

export async function listDatabases(taskId: string): Promise<{ databases: string[] }> {
  return request(`${API_BASE}/tasks/${taskId}/databases`)
}

export async function listTables(taskId: string, database: string): Promise<{ tables: string[] }> {
  return request(`${API_BASE}/tasks/${taskId}/tables?database=${encodeURIComponent(database)}`)
}

export async function getColumns(taskId: string, database: string, table: string): Promise<{ fields: Record<string, string> }> {
  return request(`${API_BASE}/tasks/${taskId}/columns?database=${encodeURIComponent(database)}&table=${encodeURIComponent(table)}`)
}

export async function previewQuery(
  taskId: string,
  data: {
    database_name?: string
    table_name?: string
    where_clause?: string
    custom_sql?: string
    output_columns?: string[]
    page?: number
    page_size?: number
    top_n?: number
  },
): Promise<MySQLPreviewResult> {
  return request<MySQLPreviewResult>(`${API_BASE}/tasks/${taskId}/preview`, {
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
