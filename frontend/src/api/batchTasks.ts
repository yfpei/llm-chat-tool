import type { BatchTask } from '../types'
import { authFetch } from './client'

const BASE = '/api/batch-tasks'

export async function fetchBatchTasks(): Promise<BatchTask[]> {
  const res = await authFetch(BASE)
  return res.json()
}

export async function getBatchTask(id: string): Promise<BatchTask> {
  const res = await authFetch(`${BASE}/${id}`)
  return res.json()
}

export async function updateBatchTask(
  id: string,
  data: { title?: string; config_json?: string; status?: string; progress_completed?: number; progress_total?: number }
): Promise<BatchTask> {
  const res = await authFetch(`${BASE}/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  return res.json()
}

export async function deleteBatchTask(id: string): Promise<void> {
  await authFetch(`${BASE}/${id}`, { method: 'DELETE' })
}

export async function getTaskPreview(id: string): Promise<{ columns: string[]; headers: string[]; total_rows: number; preview: any[] }> {
  const res = await authFetch(`${BASE}/${id}/preview`)
  return res.json()
}

export async function getTaskResults(id: string): Promise<{ row: number; input: string; output: string; status: string }[]> {
  const res = await authFetch(`${BASE}/${id}/results`)
  return res.json()
}
