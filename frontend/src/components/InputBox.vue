<template>
  <div class="input-area">
    <div class="input-card">
      <n-input
        v-model:value="inputText"
        type="textarea"
        :autosize="{ minRows: 1, maxRows: 8 }"
        placeholder="输入消息... (Enter 发送, Shift+Enter 换行)"
        @keydown="handleKeydown"
        :disabled="store.isStreaming"
        class="msg-input"
      />
      <div class="input-actions">
        <span class="input-hint">Enter 发送 · Shift+Enter 换行</span>
        <n-button
          v-if="store.isStreaming"
          @click="store.stopStreaming()"
          secondary
          size="small"
          class="stop-btn"
        >
          <template #icon>
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <rect x="2" y="2" width="10" height="10" rx="2" stroke="currentColor" stroke-width="1.3"/>
            </svg>
          </template>
          停止
        </n-button>
        <n-button
          v-else
          @click="send"
          :disabled="!inputText.trim()"
          type="primary"
          size="small"
          class="send-btn"
        >
          <template #icon>
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <path d="M2 2l11 5-11 5 2-5-2-5z" fill="currentColor"/>
            </svg>
          </template>
          发送
        </n-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { NInput, NButton } from 'naive-ui'
import { useChatStore } from '../stores/chat'

const store = useChatStore()
const inputText = ref('')

function send() {
  const text = inputText.value.trim()
  if (!text || store.isStreaming) return
  store.sendMessage(text)
  inputText.value = ''
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    send()
  }
}
</script>

<style scoped>
.input-area {
  flex-shrink: 0;
  padding: 16px 24px 20px;
}

.input-card {
  max-width: 820px;
  margin: 0 auto;
  background: #fff;
  border: 1px solid #e5e5ea;
  border-radius: 16px;
  padding: 8px 12px 10px;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.input-card:focus-within {
  border-color: #6366f1;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.08);
}

.msg-input {
  --n-border: none !important;
  --n-border-hover: none !important;
  --n-border-focus: none !important;
  --n-box-shadow-focus: none !important;
}

.msg-input :deep(.n-input__textarea-el) {
  font-size: 14.5px;
  line-height: 1.6;
  background: transparent;
  resize: none;
}

.input-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 2px;
}

.input-hint {
  font-size: 11px;
  color: #b0b0b8;
  margin-right: auto;
}

.send-btn {
  --n-font-weight: 600 !important;
  height: 32px !important;
  padding: 0 14px !important;
  border-radius: 8px !important;
}

.stop-btn {
  --n-font-weight: 600 !important;
  height: 32px !important;
  padding: 0 14px !important;
  border-radius: 8px !important;
}
</style>
