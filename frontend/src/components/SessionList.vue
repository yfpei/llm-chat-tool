<template>
  <div class="session-list">
    <!-- Chat mode: conversations -->
    <template v-if="view === 'chat'">
      <div
        v-for="conv in store.conversations"
        :key="conv.id"
        :class="['session-item', { active: store.currentConversation?.id === conv.id }]"
        @click="handleConvClick(conv)"
      >
        <div class="session-content">
          <div class="session-icon">
            <svg v-if="store.currentConversation?.id === conv.id" width="15" height="15" viewBox="0 0 15 15" fill="none">
              <path d="M7.5 1L1.875 4.25v6.5L7.5 14l5.625-3.25v-6.5L7.5 1z" stroke="currentColor" stroke-width="1.2" stroke-linejoin="round"/>
            </svg>
            <svg v-else width="15" height="15" viewBox="0 0 15 15" fill="none">
              <path d="M2.5 3.5h10v8h-10v-8z" stroke="currentColor" stroke-width="1.2"/>
              <path d="M5 7h5M5 9.5h3" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/>
            </svg>
          </div>
          <span v-if="editingConvId !== conv.id" class="session-title">{{ conv.title }}</span>
          <n-input v-else
                   size="tiny"
                   v-model:value="editConvTitle"
                   @blur="finishEditConv(conv.id)"
                   @keyup.enter="finishEditConv(conv.id)"
                   @click.stop />
        </div>
        <n-popconfirm @positive-click="store.removeConversation(conv.id)" :negative-text="null">
          <template #trigger>
            <button class="delete-btn" @click.stop title="删除">
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                <path d="M3 4h8M5.5 4V3a1 1 0 011-1h1a1 1 0 011 1v1M11 4v7.5a1 1 0 01-1 1H4a1 1 0 01-1-1V4" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </button>
          </template>
          确认删除此对话？
        </n-popconfirm>
      </div>
    </template>

    <!-- Batch mode: batch tasks -->
    <template v-else>
      <div
        v-for="task in batchStore.batchTasks"
        :key="task.id"
        :class="['session-item', { active: batchStore.currentTask?.id === task.id }]"
        @click="handleTaskClick(task)"
      >
        <div class="session-content">
          <div class="session-icon">
            <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
              <rect x="1.5" y="1.5" width="12" height="12" rx="1.5" stroke="currentColor" stroke-width="1.2"/>
              <path d="M5 5.5h5M5 7.5h5M5 9.5h3" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/>
            </svg>
          </div>
          <span v-if="editingTaskId !== task.id" class="session-title">{{ task.title }}</span>
          <n-input v-else
                   size="tiny"
                   v-model:value="editTaskTitle"
                   @blur="finishEditTask(task.id)"
                   @keyup.enter="finishEditTask(task.id)"
                   @click.stop />
        </div>
        <n-popconfirm @positive-click="batchStore.removeBatchTask(task.id)" :negative-text="null">
          <template #trigger>
            <button class="delete-btn" @click.stop title="删除">
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                <path d="M3 4h8M5.5 4V3a1 1 0 011-1h1a1 1 0 011 1v1M11 4v7.5a1 1 0 01-1 1H4a1 1 0 01-1-1V4" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </button>
          </template>
          确认删除此任务？
        </n-popconfirm>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { NPopconfirm, NInput } from 'naive-ui'
import { useChatStore } from '../stores/chat'
import { useBatchStore } from '../stores/batch'
import type { BatchTask, Conversation } from '../types'

defineProps<{
  view: 'chat' | 'batch'
}>()

const store = useChatStore()
const batchStore = useBatchStore()

// ── Conversation rename ──────────────────────
const editingConvId = ref<string | null>(null)
const editConvTitle = ref('')

function handleConvClick(conv: Conversation) {
  if (editingConvId.value) return
  if (store.currentConversation?.id === conv.id) {
    editingConvId.value = conv.id
    editConvTitle.value = conv.title
  } else {
    store.selectConversation(conv.id)
  }
}

async function finishEditConv(convId: string) {
  const newTitle = editConvTitle.value.trim()
  if (newTitle) {
    await store.renameConversation(convId, newTitle)
  }
  editingConvId.value = null
}

// ── Batch task rename ────────────────────────
const editingTaskId = ref<string | null>(null)
const editTaskTitle = ref('')

function handleTaskClick(task: BatchTask) {
  if (editingTaskId.value) return
  if (batchStore.currentTask?.id === task.id) {
    editingTaskId.value = task.id
    editTaskTitle.value = task.title
  } else {
    batchStore.selectBatchTask(task.id)
  }
}

async function finishEditTask(taskId: string) {
  const newTitle = editTaskTitle.value.trim()
  if (newTitle) {
    await batchStore.renameBatchTask(taskId, newTitle)
  }
  editingTaskId.value = null
}
</script>

<style scoped>
.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px 8px;
}

.session-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  margin-bottom: 2px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.15s ease;
  color: #b4b4be;
  position: relative;
}

.session-item:hover {
  background: #252530;
  color: #ececf1;
}

.session-item.active {
  background: #252530;
  color: #fff;
  font-weight: 500;
}

.session-item.active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 8px;
  bottom: 8px;
  width: 3px;
  border-radius: 0 2px 2px 0;
  background: #10a37f;
}

.session-content {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
  overflow: hidden;
}

.session-icon {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  opacity: 0.6;
}

.session-item.active .session-icon {
  opacity: 1;
  color: #10a37f;
}

.session-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13.5px;
  line-height: 1.4;
}

.delete-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: inherit;
  cursor: pointer;
  opacity: 0;
  transition: all 0.15s;
  flex-shrink: 0;
}

.session-item:hover .delete-btn {
  opacity: 0.5;
}

.delete-btn:hover {
  opacity: 1 !important;
  background: #3d3d4a;
  color: #ef4444;
}
</style>
