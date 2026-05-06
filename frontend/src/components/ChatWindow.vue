<template>
  <div class="chat-window">
    <div v-if="!store.currentConversation" class="empty-state">
      <div class="empty-logo">
        <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
          <rect width="48" height="48" rx="14" fill="url(#g)"/>
          <path d="M24 10l-14 7v14l14 7 14-7V17l-14-7z" stroke="#fff" stroke-width="2" stroke-linejoin="round"/>
          <defs>
            <linearGradient id="g" x1="0" y1="0" x2="48" y2="48">
              <stop stop-color="#6366f1"/>
              <stop offset="1" stop-color="#5558e6"/>
            </linearGradient>
          </defs>
        </svg>
      </div>
      <h2>开始对话</h2>
      <p>点击左侧「新对话」按钮，或选择一个历史对话</p>
    </div>
    <template v-else>
      <header class="chat-top-bar">
        <div class="chat-title">{{ store.currentConversation.title }}</div>
        <div class="chat-model" v-if="store.activeKey()">
          <span class="model-badge">{{ store.activeKey()!.model }}</span>
        </div>
      </header>
      <div class="messages" ref="messagesRef">
        <MessageBubble
          v-for="msg in store.currentConversation.messages"
          :key="msg.id"
          :message="msg"
        />
        <div v-if="store.isStreaming && store.currentConversation.messages.length === 0" class="streaming-hint">
          正在生成回复...
        </div>
      </div>
      <InputBox />
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import { useChatStore } from '../stores/chat'
import MessageBubble from './MessageBubble.vue'
import InputBox from './InputBox.vue'

const store = useChatStore()
const messagesRef = ref<HTMLElement>()

watch(
  () => {
    const msgs = store.currentConversation?.messages
    if (!msgs || msgs.length === 0) return ''
    return msgs[msgs.length - 1].content
  },
  async () => {
    await nextTick()
    if (messagesRef.value) {
      messagesRef.value.scrollTop = messagesRef.value.scrollHeight
    }
  },
)
</script>

<style scoped>
.chat-window {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #f5f5f7;
}

/* ── Top bar ──────────────────────────────── */

.chat-top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  height: 52px;
  background: rgba(255,255,255,0.7);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(0,0,0,0.06);
  flex-shrink: 0;
}

.chat-title {
  font-size: 15px;
  font-weight: 600;
  color: #1a1a2e;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.model-badge {
  font-size: 12px;
  font-weight: 500;
  color: #6366f1;
  background: rgba(99, 102, 241, 0.08);
  padding: 4px 10px;
  border-radius: 20px;
}

/* ── Messages ─────────────────────────────── */

.messages {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

.messages::-webkit-scrollbar {
  width: 6px;
}
.messages::-webkit-scrollbar-track {
  background: transparent;
}
.messages::-webkit-scrollbar-thumb {
  background: #d9d9de;
  border-radius: 3px;
}

.streaming-hint {
  text-align: center;
  color: #999;
  font-size: 13px;
  padding: 12px;
}

/* ── Empty state ──────────────────────────── */

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 16px;
  color: #8e8e9a;
}

.empty-logo {
  margin-bottom: 8px;
  opacity: 0.6;
}

.empty-state h2 {
  font-size: 22px;
  font-weight: 600;
  color: #1a1a2e;
}

.empty-state p {
  font-size: 15px;
  color: #8e8e9a;
}
</style>
