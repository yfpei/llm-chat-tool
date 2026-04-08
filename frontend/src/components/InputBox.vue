<template>
  <div class="input-box">
    <n-input
      v-model:value="inputText"
      type="textarea"
      :autosize="{ minRows: 1, maxRows: 5 }"
      placeholder="输入消息... (Enter 发送, Shift+Enter 换行)"
      @keydown="handleKeydown"
      :disabled="store.isStreaming"
    />
    <n-button
      type="primary"
      :disabled="!inputText.trim() || store.isStreaming"
      @click="send"
      style="margin-left: 8px; align-self: flex-end"
    >
      {{ store.isStreaming ? '生成中...' : '发送' }}
    </n-button>
    <n-button
      v-if="store.isStreaming"
      @click="store.stopStreaming()"
      style="margin-left: 4px; align-self: flex-end"
    >
      停止
    </n-button>
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
.input-box {
  display: flex;
  align-items: flex-start;
  padding: 12px 16px;
  border-top: 1px solid #e8e8e8;
}
</style>
