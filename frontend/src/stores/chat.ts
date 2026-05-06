import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { ApiKeyConfig, Conversation, ConversationDetail, Message } from '../types'
import * as keysApi from '../api/keys'
import * as convApi from '../api/conversations'
import * as chatApi from '../api/chat'

export const useChatStore = defineStore('chat', () => {
  const apiKeys = ref<ApiKeyConfig[]>([])
  const conversations = ref<Conversation[]>([])
  const currentConversation = ref<ConversationDetail | null>(null)
  const showSettings = ref(false)

  // Per-conversation streaming state so each conversation streams independently.
  const streamingStates = ref<Record<string, { abortController: AbortController | null; content: string; startTime: number }>>({})

  // Conversation detail cache — preserves in-progress streaming state across switches.
  const conversationCache = ref<Record<string, ConversationDetail>>({})

  const isStreaming = computed(() => {
    const id = currentConversation.value?.id
    if (!id) return false
    return streamingStates.value[id]?.abortController != null
  })

  function getStreamState(convId: string) {
    if (!streamingStates.value[convId]) {
      streamingStates.value[convId] = { abortController: null, content: '', startTime: 0 }
    }
    return streamingStates.value[convId]
  }

  function cleanupStreamState(convId: string) {
    delete streamingStates.value[convId]
  }

  async function loadKeys() {
    apiKeys.value = await keysApi.fetchKeys()
  }

  async function addKey(data: Parameters<typeof keysApi.createKey>[0]) {
    const key = await keysApi.createKey(data)
    apiKeys.value.unshift(key)
    return key
  }

  async function updateKey(id: number, data: Parameters<typeof keysApi.updateKey>[1]) {
    const key = await keysApi.updateKey(id, data)
    const idx = apiKeys.value.findIndex((k) => k.id === id)
    if (idx !== -1) apiKeys.value[idx] = key
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
    // If cached and currently streaming, reuse the cache so in-progress
    // assistant messages survive the re-select.
    const cached = conversationCache.value[id]
    if (cached && streamingStates.value[id]?.abortController != null) {
      currentConversation.value = cached
      return
    }

    const detail = await convApi.getConversation(id)
    conversationCache.value[id] = detail
    currentConversation.value = detail
  }

  async function removeConversation(id: string) {
    const streamState = streamingStates.value[id]
    if (streamState?.abortController) {
      streamState.abortController.abort()
    }
    cleanupStreamState(id)
    delete conversationCache.value[id]

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
    if (conversationCache.value[id]) {
      conversationCache.value[id].title = title
    }
    if (currentConversation.value?.id === id) {
      currentConversation.value.title = title
    }
  }

  function sendMessage(content: string) {
    if (!currentConversation.value || isStreaming.value) return

    const convId = currentConversation.value.id
    // Capture the conversation object so callbacks always update the correct
    // conversation, regardless of what currentConversation.value points to later.
    const conv = currentConversation.value

    const userMsg: Message = {
      id: Date.now(),
      role: 'user',
      content,
      created_at: new Date().toISOString(),
    }
    conv.messages.push(userMsg)

    const streamState = getStreamState(convId)
    streamState.content = ''
    streamState.startTime = Date.now()

    const assistantMsg: Message = {
      id: Date.now() + 1,
      role: 'assistant',
      content: '',
      created_at: new Date().toISOString(),
    }
    conv.messages.push(assistantMsg)
    const assistantIdx = conv.messages.length - 1

    streamState.abortController = chatApi.sendMessage(
      convId,
      content,
      (chunk) => {
        streamState.content += chunk
        conv.messages[assistantIdx].content = streamState.content
      },
      () => {
        cleanupStreamState(convId)
        loadConversations()
      },
      (error) => {
        conv.messages[assistantIdx].content = `[错误] ${error}`
        cleanupStreamState(convId)
      },
      (usage) => {
        const elapsed = (Date.now() - streamState.startTime) / 1000
        if (elapsed > 0 && usage.completion_tokens > 0) {
          usage.tokens_per_second = Math.round(usage.completion_tokens / elapsed)
        }
        conv.messages[assistantIdx].usage = usage
      },
    )
  }

  function stopStreaming() {
    const id = currentConversation.value?.id
    if (!id) return
    const streamState = streamingStates.value[id]
    if (streamState?.abortController) {
      streamState.abortController.abort()
      cleanupStreamState(id)
    }
  }

  return {
    apiKeys, conversations, currentConversation,
    isStreaming, showSettings,
    loadKeys, addKey, updateKey, removeKey, setActiveKey, activeKey,
    loadConversations, newConversation, selectConversation,
    removeConversation, renameConversation,
    sendMessage, stopStreaming,
  }
})
