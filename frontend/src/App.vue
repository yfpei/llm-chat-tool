<template>
  <n-config-provider :theme-overrides="themeOverrides">
    <n-message-provider>
      <div class="app-layout">
        <aside class="sidebar">
          <div class="sidebar-brand">
            <div class="brand-icon">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </div>
            <span class="brand-text">LLM Chat</span>
          </div>
          <div class="sidebar-new-chat">
            <n-button block @click="handleNewChat" size="large" class="new-chat-btn">
              <template #icon>
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                  <path d="M8 3v10M3 8h10" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                </svg>
              </template>
              {{ currentView === 'batch' ? '新任务' : '新对话' }}
            </n-button>
          </div>

          <div class="sidebar-nav">
            <button :class="['nav-item', { active: currentView === 'chat' }]" @click="currentView = 'chat'">
              <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
                <path d="M2.5 3.5h10v8h-10v-8z" stroke="currentColor" stroke-width="1.2"/>
                <path d="M5 7h5M5 9.5h3" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/>
              </svg>
              对话
            </button>
            <button :class="['nav-item', { active: currentView === 'batch' }]" @click="currentView = 'batch'">
              <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
                <rect x="1.5" y="1.5" width="12" height="12" rx="1.5" stroke="currentColor" stroke-width="1.2"/>
                <path d="M5 5.5h5M5 7.5h5M5 9.5h3" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/>
              </svg>
              跑批
            </button>
          </div>

          <SessionList :view="currentView" />
          <div class="sidebar-footer">
            <div class="footer-key" @click="store.showSettings = true">
              <div class="key-dot" :class="{ active: store.activeKey() }"></div>
              <span class="key-label">{{ store.activeKey()?.name || '未配置 API Key' }}</span>
              <svg class="footer-chevron" width="14" height="14" viewBox="0 0 14 14" fill="none">
                <path d="M5 3l4 4-4 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </div>
          </div>
        </aside>
        <main class="main-area">
          <KeepAlive>
            <ChatWindow v-if="currentView === 'chat'" key="chat" />
            <BatchPanel v-else-if="currentView === 'batch'" key="batch" />
          </KeepAlive>
        </main>
        <SettingsPanel />
      </div>
    </n-message-provider>
  </n-config-provider>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { NConfigProvider, NMessageProvider, NButton } from 'naive-ui'
import { useChatStore } from './stores/chat'
import { useBatchStore } from './stores/batch'
import SessionList from './components/SessionList.vue'
import ChatWindow from './components/ChatWindow.vue'
import BatchPanel from './components/BatchPanel.vue'
import SettingsPanel from './components/SettingsPanel.vue'

const store = useChatStore()
const batchStore = useBatchStore()
const currentView = ref<'chat' | 'batch'>('chat')

function handleNewChat() {
  if (currentView.value === 'batch') {
    batchStore.newBatchTask()
  } else {
    store.newConversation()
  }
}

const themeOverrides = {
  common: {
    primaryColor: '#6366f1',
    primaryColorHover: '#5558e6',
    primaryColorPressed: '#4a4edb',
    primaryColorSuppl: '#6366f1',
    borderRadius: '8px',
  },
  Button: {
    borderRadiusMedium: '8px',
    fontSizeMedium: '14px',
  },
  Drawer: {
    borderRadius: '0',
  },
}

onMounted(async () => {
  await Promise.all([store.loadKeys(), store.loadConversations(), batchStore.loadBatchTasks()])
})
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body, #app {
  height: 100%;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', 'Roboto', 'Helvetica Neue', sans-serif;
  background: #f5f5f7;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

::-webkit-scrollbar {
  width: 6px;
}
::-webkit-scrollbar-track {
  background: transparent;
}
::-webkit-scrollbar-thumb {
  background: #d9d9de;
  border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover {
  background: #b0b0b8;
}
</style>

<style scoped>
.app-layout {
  display: flex;
  height: 100vh;
  background: #f5f5f7;
}

/* ── Sidebar ─────────────────────────────── */

.sidebar {
  width: 280px;
  background: #1a1b23;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px 16px 12px;
}

.brand-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: linear-gradient(135deg, #6366f1, #5558e6);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
}

.brand-text {
  font-size: 16px;
  font-weight: 700;
  color: #ececf1;
  letter-spacing: -0.3px;
}

.sidebar-new-chat {
  padding: 0 12px 8px;
}

/* ── Sidebar nav ──────────────────────────── */

.sidebar-nav {
  display: flex;
  gap: 2px;
  padding: 0 12px 8px;
}

.nav-item {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  padding: 7px 0;
  border: none;
  border-radius: 7px;
  background: transparent;
  color: #9e9eae;
  font-size: 12.5px;
  cursor: pointer;
  transition: all 0.15s;
}

.nav-item:hover {
  background: #252530;
  color: #ececf1;
}

.nav-item.active {
  background: #252530;
  color: #fff;
}

.new-chat-btn {
  --n-color: #6366f1 !important;
  --n-color-hover: #5558e6 !important;
  --n-color-pressed: #4a4edb !important;
  --n-text-color: #fff !important;
  --n-font-weight: 600 !important;
  border: none !important;
  height: 42px !important;
  font-size: 14px !important;
  border-radius: 10px !important;
  transition: all 0.2s ease !important;
}

.new-chat-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(16, 163, 127, 0.3);
}

/* ── Sidebar footer ──────────────────────── */

.sidebar-footer {
  padding: 12px;
  border-top: 1px solid #2d2d38;
}

.footer-key {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s;
  color: #b4b4be;
}

.footer-key:hover {
  background: #252530;
}

.key-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #666;
  flex-shrink: 0;
}

.key-dot.active {
  background: #10a37f;
  box-shadow: 0 0 6px rgba(16, 163, 127, 0.5);
}

.key-label {
  flex: 1;
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.footer-chevron {
  flex-shrink: 0;
  opacity: 0.5;
}

/* ── Main area ───────────────────────────── */

.main-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  background: #f5f5f7;
}
</style>
