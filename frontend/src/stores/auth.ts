import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { AuthUser } from '../types'
import * as authApi from '../api/auth'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<AuthUser | null>(null)
  const token = ref<string | null>(null)

  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => user.value?.role === 'admin')

  function _loadFromStorage() {
    const savedToken = localStorage.getItem('token')
    const savedUser = localStorage.getItem('user')
    if (savedToken && savedUser) {
      token.value = savedToken
      try {
        user.value = JSON.parse(savedUser)
      } catch {
        _clear()
      }
    }
  }

  function _saveToStorage(t: string, u: AuthUser) {
    token.value = t
    user.value = u
    localStorage.setItem('token', t)
    localStorage.setItem('user', JSON.stringify(u))
  }

  function _clear() {
    token.value = null
    user.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('user')
  }

  async function login(username: string, password: string) {
    const resp = await authApi.login(username, password)
    _saveToStorage(resp.access_token, resp.user)
    return resp.user
  }

  async function register(username: string, password: string) {
    const resp = await authApi.register(username, password)
    _saveToStorage(resp.access_token, resp.user)
    return resp.user
  }

  function logout() {
    _clear()
    window.location.href = '/login'
  }

  _loadFromStorage()

  return { user, token, isLoggedIn, isAdmin, login, register, logout }
})
