<template>
  <n-config-provider>
    <n-message-provider>
      <div class="app-layout">
        <header class="app-header">
          <n-button text @click="store.showSettings = true" style="font-size: 18px">
            设置
          </n-button>
          <span class="current-model" v-if="store.activeKey()">
            当前模型: {{ store.activeKey()!.model }}
          </span>
          <span class="current-model" v-else style="color: #f5a623">
            未配置 API Key
          </span>
        </header>
        <div class="app-body">
          <aside class="sidebar">
            <SessionList />
          </aside>
          <main class="main-content">
            <ChatWindow />
          </main>
        </div>
        <SettingsPanel />
      </div>
    </n-message-provider>
  </n-config-provider>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { NConfigProvider, NMessageProvider, NButton } from 'naive-ui'
import { useChatStore } from './stores/chat'
import SessionList from './components/SessionList.vue'
import ChatWindow from './components/ChatWindow.vue'
import SettingsPanel from './components/SettingsPanel.vue'

const store = useChatStore()

onMounted(async () => {
  await Promise.all([store.loadKeys(), store.loadConversations()])
})
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

.app-layout {
  display: flex;
  flex-direction: column;
  height: 100vh;
}

.app-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 16px;
  border-bottom: 1px solid #e8e8e8;
  background: #fafafa;
}

.current-model {
  font-size: 13px;
  color: #666;
}

.app-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.sidebar {
  width: 260px;
  border-right: 1px solid #e8e8e8;
  background: #f7f7f7;
  overflow-y: auto;
}

.main-content {
  flex: 1;
  overflow: hidden;
}
</style>
