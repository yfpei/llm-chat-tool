<template>
  <div :class="['message-bubble', message.role]">
    <div class="message-role">{{ message.role === 'user' ? '你' : 'AI' }}</div>
    <div class="message-content" v-if="message.role === 'user'">{{ message.content }}</div>
    <div class="message-content" v-else v-html="renderedContent"></div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import MarkdownIt from 'markdown-it'
import type { Message } from '../types'

const props = defineProps<{ message: Message }>()

const md = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
})

const renderedContent = computed(() => md.render(props.message.content || ''))
</script>

<style scoped>
.message-bubble {
  margin-bottom: 16px;
  padding: 12px 16px;
  border-radius: 8px;
  max-width: 80%;
}

.message-bubble.user {
  background: #e3f2fd;
  margin-left: auto;
}

.message-bubble.assistant {
  background: #f5f5f5;
  margin-right: auto;
}

.message-role {
  font-size: 12px;
  color: #888;
  margin-bottom: 4px;
}

.message-content {
  line-height: 1.6;
  word-break: break-word;
}

.message-content :deep(pre) {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 12px;
  border-radius: 6px;
  overflow-x: auto;
}

.message-content :deep(code) {
  background: #e8e8e8;
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 0.9em;
}

.message-content :deep(pre code) {
  background: none;
  padding: 0;
}
</style>
