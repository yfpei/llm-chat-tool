<template>
  <div :class="['msg', message.role]">
    <div class="msg-avatar">
      <template v-if="message.role === 'user'">
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
          <circle cx="8" cy="6" r="3" stroke="currentColor" stroke-width="1.3"/>
          <path d="M3 14c0-2.8 2.2-5 5-5s5 2.2 5 5" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/>
        </svg>
      </template>
      <template v-else>
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
          <rect x="2" y="2" width="12" height="10" rx="2" stroke="currentColor" stroke-width="1.3"/>
          <path d="M5 7h6M5 9.5h4" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/>
        </svg>
      </template>
    </div>
    <div class="msg-body">
      <div class="msg-role">{{ message.role === 'user' ? '你' : 'AI 助手' }}</div>

      <!-- Thinking section -->
      <div v-if="parsed.thinking != null && parsed.thinking.length > 0" class="think-section">
        <button class="think-header" @click="thinkExpanded = !thinkExpanded">
          <span v-if="!parsed.thinkingComplete" class="think-spinner spinning">
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <circle cx="7" cy="7" r="5.5" stroke="currentColor" stroke-width="1.2" opacity="0.2"/>
              <path d="M12.5 7A5.5 5.5 0 007 1.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
            </svg>
          </span>
          <span class="think-label">
            {{ parsed.thinkingComplete ? '思考过程' : '思考中...' }}
          </span>
          <svg
            class="think-chevron"
            :class="{ open: thinkExpanded }"
            width="10" height="10" viewBox="0 0 10 10" fill="none"
          >
            <path d="M3.5 1.5l3.5 3.5-3.5 3.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </button>
        <div v-if="thinkExpanded" class="think-body">
          <pre class="think-text">{{ parsed.thinking }}</pre>
        </div>
      </div>

      <!-- Main content -->
      <div class="msg-content-wrap">
        <div v-if="message.role === 'user'" class="msg-content user-content">{{ message.content }}</div>
        <div v-else-if="parsed.displayContent" class="msg-content markdown-body" v-html="renderedContent"></div>
        <div
          v-if="message.role === 'assistant' && parsed.displayContent && parsed.displayContent.length > 0"
          class="msg-copy"
        >
          <button class="copy-btn" @click="copyContent" :title="copied ? '已复制' : '复制'">
            <svg v-if="!copied" width="14" height="14" viewBox="0 0 14 14" fill="none">
              <rect x="4" y="4" width="9" height="9" rx="1.5" stroke="currentColor" stroke-width="1.2"/>
              <path d="M2 10V2.5A.5.5 0 012.5 2H10" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/>
            </svg>
            <svg v-else width="14" height="14" viewBox="0 0 14 14" fill="none">
              <path d="M3 7l3 3 5-6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </button>
        </div>
      </div>

      <div v-if="message.usage" class="token-usage">
        <span class="usage-item"><span>输入</span> <strong>{{ message.usage.prompt_tokens }}</strong></span>
        <span class="usage-dot">·</span>
        <span class="usage-item"><span>输出</span> <strong>{{ message.usage.completion_tokens }}</strong></span>
        <span v-if="message.usage.tokens_per_second" class="usage-dot">·</span>
        <span v-if="message.usage.tokens_per_second" class="usage-item usage-speed">
          <strong>{{ message.usage.tokens_per_second }}</strong><span> tok/s</span>
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import MarkdownIt from 'markdown-it'
import type { Message } from '../types'

interface ParsedContent {
  thinking: string | null
  thinkingComplete: boolean
  displayContent: string
}

// Patterns for thinking boundaries: <think>, </think>, and <unusedN> / <unusedM>.
const THINK_PAIR = /<think>([\s\S]*?)<\/think>/
const THINK_OPEN = /<think>([\s\S]*)$/
const THINK_CLOSE = /^([\s\S]*?)<\/think>([\s\S]*)$/
const UNUSED_PAIR = /<unused\d+>([\s\S]*?)<unused\d+>/
const UNUSED_OPEN = /<unused\d+>([\s\S]*)$/
const UNUSED_CLOSE = /^([\s\S]*?)<unused\d+>([\s\S]*)$/

function parseContent(raw: string): ParsedContent {
  if (!raw) return { thinking: null, thinkingComplete: true, displayContent: '' }

  // Try <think> patterns first
  for (const re of [THINK_PAIR, UNUSED_PAIR]) {
    const m = raw.match(re)
    if (m) {
      return {
        thinking: m[1],
        thinkingComplete: true,
        displayContent: raw.replace(m[0], '').trimStart(),
      }
    }
  }

  // Open without close — streaming
  for (const re of [THINK_OPEN, UNUSED_OPEN]) {
    const m = raw.match(re)
    if (m) {
      return { thinking: m[1], thinkingComplete: false, displayContent: '' }
    }
  }

  // Close without explicit open
  for (const re of [THINK_CLOSE, UNUSED_CLOSE]) {
    const m = raw.match(re)
    if (m) {
      return { thinking: m[1], thinkingComplete: true, displayContent: m[2].trimStart() }
    }
  }

  return { thinking: null, thinkingComplete: true, displayContent: raw }
}

const props = defineProps<{ message: Message }>()
const copied = ref(false)
const thinkExpanded = ref(false)

const md = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
})

const parsed = computed(() => parseContent(props.message.content || ''))

const renderedContent = computed(() => {
  if (!parsed.value.displayContent) return ''
  return md.render(parsed.value.displayContent)
})

// Auto-expand thinking while it's streaming; collapse when complete.
watch(
  () => parsed.value.thinkingComplete,
  (complete) => {
    thinkExpanded.value = !complete
  },
  { immediate: true },
)

async function copyContent() {
  try {
    await navigator.clipboard.writeText(parsed.value.displayContent)
    copied.value = true
    setTimeout(() => { copied.value = false }, 2000)
  } catch {
    // Clipboard not available
  }
}
</script>

<style scoped>
.msg {
  display: flex;
  gap: 14px;
  padding: 8px 0;
  max-width: 860px;
  margin: 0 auto;
  width: 100%;
}

.msg.user {
  flex-direction: row-reverse;
}

/* ── Avatar ────────────────────────────────── */

.msg-avatar {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-top: 2px;
}

.msg.assistant .msg-avatar {
  background: #6366f1;
  color: #fff;
}

.msg.user .msg-avatar {
  background: #6c63ff;
  color: #fff;
}

/* ── Body ──────────────────────────────────── */

.msg-body {
  flex: 1;
  min-width: 0;
}

.msg.user .msg-body {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.msg-role {
  font-size: 12px;
  font-weight: 600;
  color: #8e8e9a;
  margin-bottom: 4px;
  padding: 0 4px;
}

/* ── Thinking section ──────────────────────── */

.think-section {
  margin-bottom: 8px;
}

.think-header {
  display: flex;
  align-items: center;
  gap: 6px;
  border: none;
  background: none;
  padding: 2px 0;
  cursor: pointer;
  font-size: 12px;
  color: #9e9eae;
  transition: color 0.15s;
}

.think-header:hover {
  color: #6e6e82;
}

.think-spinner {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

.think-spinner.spinning {
  animation: think-spin 1s linear infinite;
}

@keyframes think-spin {
  to { transform: rotate(360deg); }
}

.think-label {
  flex: 1;
  text-align: left;
}

.think-chevron {
  flex-shrink: 0;
  opacity: 0.4;
  transition: transform 0.2s;
}

.think-chevron.open {
  transform: rotate(90deg);
}

.think-body {
  /* no background, no border */
}

.think-text {
  margin: 4px 0 0;
  padding: 0;
  font-size: 12px;
  line-height: 1.6;
  color: #9e9eae;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: inherit;
  background: transparent;
}

/* ── Content wrap ──────────────────────────── */

.msg-content-wrap {
  position: relative;
  max-width: 100%;
}

.msg.user .msg-content-wrap {
  max-width: 80%;
}

.msg-content {
  font-size: 14.5px;
  line-height: 1.75;
  color: #1a1a2e;
}

.user-content {
  background: #6c63ff;
  color: #fff;
  padding: 10px 16px;
  border-radius: 18px 18px 4px 18px;
  word-break: normal !important;
  overflow-wrap: break-word;
  white-space: pre-wrap;
}

.msg-copy {
  margin-top: 6px;
  opacity: 0;
  transition: opacity 0.15s;
}

.msg-content-wrap:hover .msg-copy {
  opacity: 1;
}

.copy-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: 1px solid #e5e5ea;
  border-radius: 6px;
  background: #fff;
  cursor: pointer;
  color: #8e8e9a;
  transition: all 0.15s;
}

.copy-btn:hover {
  color: #6366f1;
  border-color: #6366f1;
}

/* ── Token usage ───────────────────────────── */

.token-usage {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
  font-size: 11.5px;
  color: #8e8e9a;
}

.usage-item strong {
  font-weight: 600;
  color: #6b6b80;
  font-variant-numeric: tabular-nums;
}

.usage-dot {
  font-weight: 700;
  color: #d9d9de;
}

/* ── Markdown ──────────────────────────────── */

.markdown-body :deep(p) {
  margin-bottom: 10px;
}
.markdown-body :deep(p:last-child) {
  margin-bottom: 0;
}

.markdown-body :deep(pre) {
  background: #1e1e2e;
  color: #cdd6f4;
  padding: 16px;
  border-radius: 10px;
  overflow-x: auto;
  margin: 10px 0;
  font-size: 13px;
  line-height: 1.6;
  border: 1px solid #313145;
}

.markdown-body :deep(code) {
  background: rgba(99, 102, 241, 0.08);
  color: #6366f1;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.88em;
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
}

.markdown-body :deep(pre code) {
  background: none;
  color: inherit;
  padding: 0;
  border-radius: 0;
  font-size: inherit;
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  margin: 8px 0;
  padding-left: 20px;
}

.markdown-body :deep(li) {
  margin: 4px 0;
}

.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3),
.markdown-body :deep(h4) {
  margin: 14px 0 6px;
  font-weight: 600;
  color: #1a1a2e;
}

.markdown-body :deep(h1) { font-size: 1.3em; }
.markdown-body :deep(h2) { font-size: 1.15em; }
.markdown-body :deep(h3) { font-size: 1.05em; }

.markdown-body :deep(blockquote) {
  border-left: 3px solid #6366f1;
  padding-left: 14px;
  margin: 8px 0;
  color: #6b6b80;
}

.markdown-body :deep(table) {
  border-collapse: collapse;
  margin: 8px 0;
  font-size: 13px;
}

.markdown-body :deep(th),
.markdown-body :deep(td) {
  border: 1px solid #e5e5ea;
  padding: 6px 12px;
  text-align: left;
}

.markdown-body :deep(th) {
  background: #f5f5f7;
  font-weight: 600;
}

.markdown-body :deep(a) {
  color: #6366f1;
  text-decoration: none;
}

.markdown-body :deep(a:hover) {
  text-decoration: underline;
}

.markdown-body :deep(hr) {
  border: none;
  border-top: 1px solid #e5e5ea;
  margin: 12px 0;
}
</style>
