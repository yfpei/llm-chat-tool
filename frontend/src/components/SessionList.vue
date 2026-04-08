<template>
  <div class="session-list">
    <n-button block type="primary" @click="store.newConversation()" style="margin-bottom: 12px">
      + 新会话
    </n-button>
    <div
      v-for="conv in store.conversations"
      :key="conv.id"
      :class="['session-item', { active: store.currentConversation?.id === conv.id }]"
      @click="store.selectConversation(conv.id)"
    >
      <span class="session-title">{{ conv.title }}</span>
      <n-popconfirm @positive-click="store.removeConversation(conv.id)">
        <template #trigger>
          <n-button text size="tiny" class="delete-btn" @click.stop>×</n-button>
        </template>
        确认删除此会话？
      </n-popconfirm>
    </div>
  </div>
</template>

<script setup lang="ts">
import { NButton, NPopconfirm } from 'naive-ui'
import { useChatStore } from '../stores/chat'

const store = useChatStore()
</script>

<style scoped>
.session-list {
  padding: 12px;
  height: 100%;
  overflow-y: auto;
}

.session-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  margin-bottom: 4px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.2s;
}

.session-item:hover {
  background: rgba(0, 0, 0, 0.05);
}

.session-item.active {
  background: rgba(0, 0, 0, 0.08);
}

.session-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}

.delete-btn {
  opacity: 0;
  transition: opacity 0.2s;
}

.session-item:hover .delete-btn {
  opacity: 1;
}
</style>
