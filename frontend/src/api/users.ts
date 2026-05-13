import { authFetch } from './client'
import type { UserInfo } from '../types'

export async function fetchUsers(): Promise<UserInfo[]> {
  const res = await authFetch('/api/users')
  return res.json()
}

export async function createUser(data: { username: string; password: string; role: string }): Promise<UserInfo> {
  const res = await authFetch('/api/users', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || '创建用户失败')
  }
  return res.json()
}

export async function updateUser(id: number, data: Record<string, unknown>): Promise<UserInfo> {
  const res = await authFetch(`/api/users/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || '更新用户失败')
  }
  return res.json()
}

export async function deleteUser(id: number): Promise<void> {
  const res = await authFetch(`/api/users/${id}`, { method: 'DELETE' })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || '删除用户失败')
  }
}

export async function resetUserPassword(id: number): Promise<string> {
  const res = await authFetch(`/api/auth/reset-password/${id}`, { method: 'POST' })
  const data = await res.json()
  return data.new_password
}
