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
        <n-popconfirm @positive-click="store.removeConversation(conv.id)">
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
    <template v-else-if="view === 'batch'">
      <div
        v-for="task in batchStore.batchTasks.filter(t => t.source !== 'eval')"
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
        <n-popconfirm @positive-click="batchStore.removeBatchTask(task.id)">
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

    <!-- Eval mode: eval tasks -->
    <template v-else-if="view === 'eval'">
      <div
        v-for="task in batchStore.batchTasks.filter(t => t.source === 'eval')"
        :key="task.id"
        :class="['session-item', { active: batchStore.currentTask?.id === task.id }]"
        @click="handleTaskClick(task)"
      >
        <div class="session-content">
          <div class="session-icon">
            <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
              <rect x="1.5" y="1" width="12" height="10" rx="1" stroke="currentColor" stroke-width="1.2"/>
              <path d="M4 5.5h7M4 8h5" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/>
              <rect x="4" y="12" width="7" height="2" rx="0.5" stroke="currentColor" stroke-width="1"/>
              <rect x="2" y="13.5" width="11" height="1" rx="0.3" stroke="currentColor" stroke-width="0.8"/>
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
        <n-popconfirm @positive-click="batchStore.removeBatchTask(task.id)">
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

    <!-- Export mode: both ES and MySQL tasks -->
    <template v-else-if="view === 'export'">
      <div
        v-for="task in exportTasks"
        :key="task._type + task.id"
        :class="['session-item', { active: isExportTaskActive(task) }]"
        @click="handleExportTaskClick(task)"
      >
        <div class="session-content">
          <div class="session-icon" :class="task._type">
            <svg v-if="task._type === 'es'" width="15" height="15" viewBox="0 0 15 15" fill="none">
              <ellipse cx="7.5" cy="5" rx="5.5" ry="2.5" stroke="currentColor" stroke-width="1.2"/>
              <path d="M2 5v5c0 1.4 2.5 2.5 5.5 2.5s5.5-1.1 5.5-2.5V5" stroke="currentColor" stroke-width="1.2"/>
              <path d="M2 7.5c0 1.4 2.5 2.5 5.5 2.5s5.5-1.1 5.5-2.5" stroke="currentColor" stroke-width="1.2"/>
            </svg>
            <svg v-else width="15" height="15" viewBox="0 0 15 15" fill="none">
              <rect x="1" y="1" width="13" height="13" rx="2" stroke="currentColor" stroke-width="1.2"/>
              <path d="M3 5h9M3 8h9M3 11h6" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/>
            </svg>
          </div>
          <span v-if="editingExportTaskId !== task._type + task.id" class="session-title">
            <span class="task-type-tag">{{ task._type === 'es' ? 'ES' : 'MySQL' }}</span>
            {{ task.title }}
          </span>
          <n-input v-else
                   size="tiny"
                   v-model:value="editExportTaskTitle"
                   @blur="finishEditExportTask(task)"
                   @keyup.enter="finishEditExportTask(task)"
                   @click.stop />
        </div>
        <n-popconfirm @positive-click="removeExportTask(task)">
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
import { ref, computed, nextTick } from 'vue'
import { NPopconfirm, NInput } from 'naive-ui'
import { useChatStore } from '../stores/chat'
import { useBatchStore } from '../stores/batch'
import { useEsExportStore } from '../stores/esExport'
import { useMySQLExportStore } from '../stores/mysqlExport'
import type { BatchTask, Conversation } from '../types'

defineProps<{
  view: string
}>()

const store = useChatStore()
const batchStore = useBatchStore()
const esExportStore = useEsExportStore()
const mysqlExportStore = useMySQLExportStore()

// ── Conversation rename ──────────────────────
const editingConvId = ref<string | null>(null)
const editConvTitle = ref('')

function handleConvClick(conv: Conversation) {
  if (editingConvId.value) return
  if (store.currentConversation?.id === conv.id) {
    editingConvId.value = conv.id
    editConvTitle.value = conv.title
    nextTick(() => {
      const inp = document.querySelector<HTMLInputElement>('.session-item.active input')
      inp?.focus()
      inp?.select()
    })
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
    nextTick(() => {
      const inp = document.querySelector<HTMLInputElement>('.session-item.active input')
      inp?.focus()
      inp?.select()
    })
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

// ── Export tasks (ES + MySQL combined) ────────
interface ExportTaskItem {
  _type: 'es' | 'mysql'
  id: string
  title: string
  created_at?: string | null
}

const editingExportTaskId = ref<string | null>(null)
const editExportTaskTitle = ref('')

const exportTasks = computed<ExportTaskItem[]>(() => {
  const items: ExportTaskItem[] = [
    ...esExportStore.tasks.map(t => ({ _type: 'es' as const, id: t.id, title: t.title, created_at: t.created_at })),
    ...mysqlExportStore.tasks.map(t => ({ _type: 'mysql' as const, id: t.id, title: t.title, created_at: t.created_at })),
  ]
  items.sort((a, b) => {
    const da = a.created_at || ''
    const db = b.created_at || ''
    return db.localeCompare(da) // newest first
  })
  return items
})

function isExportTaskActive(task: ExportTaskItem): boolean {
  if (task._type === 'es') return esExportStore.currentTask?.id === task.id
  return mysqlExportStore.currentTask?.id === task.id
}

function handleExportTaskClick(task: ExportTaskItem) {
  if (editingExportTaskId.value) return
  const store = task._type === 'es' ? esExportStore : mysqlExportStore
  if (store.currentTask?.id === task.id) {
    editingExportTaskId.value = task._type + task.id
    editExportTaskTitle.value = task.title
    nextTick(() => {
      const inp = document.querySelector<HTMLInputElement>('.session-item.active input')
      inp?.focus()
      inp?.select()
    })
  } else {
    if (task._type === 'es') {
      esExportStore.selectTask(task.id)
    } else {
      mysqlExportStore.selectTask(task.id)
    }
  }
}

async function finishEditExportTask(task: ExportTaskItem) {
  const newTitle = editExportTaskTitle.value.trim()
  if (newTitle) {
    if (task._type === 'es') {
      await esExportStore.renameTask(task.id, newTitle)
    } else {
      await mysqlExportStore.renameTask(task.id, newTitle)
    }
  }
  editingExportTaskId.value = null
}

function removeExportTask(task: ExportTaskItem) {
  if (task._type === 'es') {
    esExportStore.removeTask(task.id)
  } else {
    mysqlExportStore.removeTask(task.id)
  }
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

.task-type-tag {
  display: inline-block;
  font-size: 10px;
  font-weight: 600;
  padding: 0 4px;
  border-radius: 3px;
  margin-right: 4px;
  background: rgba(99, 102, 241, 0.15);
  color: #818cf8;
  vertical-align: middle;
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