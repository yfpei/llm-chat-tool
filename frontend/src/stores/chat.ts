import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { ApiKeyConfig, Conversation, ConversationDetail, Message } from '../types'
import * as keysApi from '../api/keys'
import * as convApi from '../api/conversations'
import * as chatApi from '../api/chat'

export const useChatStore = defineStore('chat', () => {
  const apiKeys = ref<ApiKeyConfig[]>([])
  const conversations = ref<Conversation[]>([])
  const currentConversation = ref<ConversationDetail | null>(null)
  const isStreaming = ref(false)
  const streamingContent = ref('')
  const showSettings = ref(false)

  let abortController: AbortController | null = null

  async function loadKeys() {
    apiKeys.value = await keysApi.fetchKeys()
  }

  async function addKey(data: Parameters<typeof keysApi.createKey>[0]) {
    const key = await keysApi.createKey(data)
    apiKeys.value.unshift(key)
    return key
  }

  async function removeKey(id: number) {
    await keysApi.deleteKey(id)
    apiKeys.value = apiKeys.value.filter((k) => k.id !== id)
  }

  async function setActiveKey(id: number) {
    await keysApi.activateKey(id)
    apiKeys.value.forEach((k) => (k.is_active = k.id === id))
  }

  function activeKey(): ApiKeyConfig | undefined {
    return apiKeys.value.find((k) => k.is_active)
  }

  async function loadConversations() {
    conversations.value = await convApi.fetchConversations()
  }

  async function newConversation() {
    const conv = await convApi.createConversation()
    conversations.value.unshift(conv)
    await selectConversation(conv.id)
  }

  async function selectConversation(id: string) {
    currentConversation.value = await convApi.getConversation(id)
  }

  async function removeConversation(id: string) {
    await convApi.deleteConversation(id)
    conversations.value = conversations.value.filter((c) => c.id !== id)
    if (currentConversation.value?.id === id) {
      currentConversation.value = null
    }
  }

  async function renameConversation(id: string, title: string) {
    await convApi.updateConversation(id, { title })
    const conv = conversations.value.find((c) => c.id === id)
    if (conv) conv.title = title
    if (currentConversation.value?.id === id) {
      currentConversation.value.title = title
    }
  }

  function sendMessage(content: string) {
    if (!currentConversation.value || isStreaming.value) return

    const convId = currentConversation.value.id

    const userMsg: Message = {
      id: Date.now(),
      role: 'user',
      content,
      created_at: new Date().toISOString(),
    }
    currentConversation.value.messages.push(userMsg)

    isStreaming.value = true
    streamingContent.value = ''

    const assistantMsg: Message = {
      id: Date.now() + 1,
      role: 'assistant',
      content: '',
      created_at: new Date().toISOString(),
    }
    currentConversation.value.messages.push(assistantMsg)

    abortController = chatApi.sendMessage(
      convId,
      content,
      (chunk) => {
        streamingContent.value += chunk
        assistantMsg.content = streamingContent.value
      },
      () => {
        isStreaming.value = false
        streamingContent.value = ''
        loadConversations()
      },
      (error) => {
        isStreaming.value = false
        assistantMsg.content = `[错误] ${error}`
      },
    )
  }

  function stopStreaming() {
    if (abortController) {
      abortController.abort()
      abortController = null
      isStreaming.value = false
    }
  }

  return {
    apiKeys, conversations, currentConversation,
    isStreaming, streamingContent, showSettings,
    loadKeys, addKey, removeKey, setActiveKey, activeKey,
    loadConversations, newConversation, selectConversation,
    removeConversation, renameConversation,
    sendMessage, stopStreaming,
  }
})
