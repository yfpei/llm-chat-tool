<template>
  <div class="eval-page">
    <div class="eval-page-header">
      <h2>评测</h2>
    </div>
    <div class="eval-page-body">
      <!-- Upload area -->
      <div v-if="!currentTask" class="upload-area">
        <n-upload
          :max="1"
          accept=".xlsx,.xls,.json,.txt"
          @change="handleUpload"
          :show-file-list="false"
        >
          <n-button :loading="uploading" size="large">
            {{ uploading ? '解析中...' : '上传文件' }}
          </n-button>
        </n-upload>
        <span class="upload-hint">上传文件创建独立评测任务</span>
        <p v-if="uploadError" class="upload-error">{{ uploadError }}</p>
      </div>

      <!-- Current task info -->
      <div v-else>
        <div class="upload-info">
          <div class="file-tag">
            {{ currentTask.filename }}
            <span class="file-meta">({{ currentTask.total_rows }} 行, {{ columns.length }} 列)</span>
          </div>
          <div class="reupload-btn">
            <n-upload
              :key="reuploadKey"
              :max="1"
              accept=".xlsx,.xls,.json,.txt"
              :show-file-list="false"
              @change="handleReupload"
            >
              <n-button size="small" :loading="uploading" type="primary" secondary>重新上传</n-button>
            </n-upload>
          </div>
        </div>

        <!-- Eval panel -->
        <EvalPanel
          :task-id="currentTask.id"
          :columns="columns"
          :file-id="currentTask.file_id"
          :standalone="true"
        />
      </div>

      <!-- Select existing batch task result -->
      <div v-if="batchTasks.length > 0 && !currentTask" class="existing-tasks">
        <h3>或从跑批结果创建评测任务</h3>
        <div v-for="t in batchTasks.filter(t => t.status === 'completed' && t.source === 'batch')" :key="t.id" class="task-item">
          <span>{{ t.title }} ({{ t.filename }})</span>
          <n-button size="small" :loading="copyingTaskId === t.id" @click="createFromBatchTask(t.id)">创建评测</n-button>
        </div>
      </div>

      <!-- Existing eval tasks -->
      <div v-if="evalTasks.length > 0 && !currentTask" class="existing-tasks">
        <h3>已有评测任务</h3>
        <div v-for="t in evalTasks" :key="t.id" class="task-item">
          <span>{{ t.title }} ({{ t.filename }})</span>
          <n-button size="small" @click="selectEvalTask(t.id)">打开</n-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { NButton, NUpload, useMessage } from 'naive-ui'
import { useBatchStore } from '../stores/batch'
import * as batchApi from '../api/batch'
import * as batchTasksApi from '../api/batchTasks'
import EvalPanel from '../components/EvalPanel.vue'
import type { BatchTask } from '../types'

const batchStore = useBatchStore()
const message = useMessage()
const uploading = ref(false)
const uploadError = ref('')
const reuploadKey = ref(0)
const copyingTaskId = ref<string | null>(null)

// Current eval task
const currentTask = ref<BatchTask | null>(null)
const columns = ref<string[]>([])

// Task lists
const batchTasks = computed(() => batchStore.batchTasks.filter(t => t.source === 'batch'))
const evalTasks = computed(() => batchStore.batchTasks.filter(t => t.source === 'eval'))

// Watch store changes
watch(() => batchStore.currentTask, (task) => {
  if (task && task.source === 'eval') {
    currentTask.value = task
    columns.value = JSON.parse(task.columns)
  } else {
    currentTask.value = null
    columns.value = []
  }
}, { immediate: true })

onMounted(() => {
  batchStore.loadBatchTasks()
})

async function handleUpload(opts: { file: any; fileList: any[] }) {
  uploadError.value = ''
  uploading.value = true
  try {
    const rawFile = opts.file.file as File
    const result = await batchApi.uploadExcel(rawFile, undefined, 'eval')

    // Reload tasks and select the new one
    await batchStore.loadBatchTasks()
    const newTask = batchStore.batchTasks.find(t => t.id === result.task_id)
    if (newTask) {
      batchStore.currentTask = newTask
      currentTask.value = newTask
      columns.value = result.columns
    }
  } catch (e: any) {
    uploadError.value = e.message || '上传失败'
  } finally {
    uploading.value = false
  }
}

async function handleReupload(opts: { file: any; fileList: any[] }) {
  if (!currentTask.value) return
  uploadError.value = ''
  uploading.value = true
  try {
    const rawFile = opts.file.file as File
    const result = await batchApi.uploadExcel(rawFile, currentTask.value.id, 'eval')
    columns.value = result.columns
    reuploadKey.value++
    // Reload task info
    await batchStore.loadBatchTasks()
    const updatedTask = batchStore.batchTasks.find(t => t.id === currentTask.value?.id)
    if (updatedTask) {
      currentTask.value = updatedTask
    }
  } catch (e: any) {
    uploadError.value = e.message || '重新上传失败'
  } finally {
    uploading.value = false
  }
}

async function createFromBatchTask(taskId: string) {
  copyingTaskId.value = taskId
  try {
    // Create a new eval task by copying the batch task's file
    const result = await batchTasksApi.createEvalFromBatch(taskId)

    // Reload and select the new eval task
    await batchStore.loadBatchTasks()
    const newTask = batchStore.batchTasks.find(t => t.id === result.id)
    if (newTask) {
      batchStore.currentTask = newTask
      currentTask.value = newTask
      columns.value = JSON.parse(newTask.columns)
    }
  } catch (e: any) {
    message.error(e.message || '创建评测任务失败')
  } finally {
    copyingTaskId.value = null
  }
}

async function selectEvalTask(taskId: string) {
  const task = batchStore.batchTasks.find(t => t.id === taskId)
  if (task) {
    batchStore.currentTask = task
    currentTask.value = task
    columns.value = JSON.parse(task.columns)
  }
}
</script>

<style scoped>
.eval-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f5f5f7;
  overflow: hidden;
}

.eval-page-header {
  padding: 0 24px;
  height: 52px;
  display: flex;
  align-items: center;
  background: rgba(255,255,255,0.7);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(0,0,0,0.06);
  flex-shrink: 0;
}

.eval-page-header h2 {
  font-size: 18px;
  font-weight: 600;
  color: #4b4b60;
  margin: 0;
}

.eval-page-body {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  max-width: 960px;
  margin: 0 auto;
  width: 100%;
}

.upload-area {
  text-align: center;
  padding: 40px;
}

.upload-hint {
  display: block;
  margin-top: 12px;
  font-size: 13px;
  color: #999;
}

.upload-error {
  margin-top: 12px;
  color: #ef4444;
  font-size: 13px;
}

.upload-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.file-tag {
  font-size: 14px;
  font-weight: 500;
  color: #4b4b60;
}

.file-meta {
  font-size: 12px;
  color: #999;
  margin-left: 8px;
}

.reupload-btn {
  flex-shrink: 0;
}

.existing-tasks {
  margin-top: 32px;
  border-top: 1px solid #e0e0e6;
  padding-top: 24px;
}

.existing-tasks h3 {
  font-size: 14px;
  color: #666;
  margin-bottom: 12px;
}

.task-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  border: 1px solid #e0e0e6;
  border-radius: 6px;
  margin-bottom: 8px;
  font-size: 13px;
}
</style>