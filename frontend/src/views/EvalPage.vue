<template>
  <div class="eval-page">
    <div class="eval-page-header">
      <h2>评测</h2>
    </div>
    <div class="eval-page-body">
      <!-- Upload area -->
      <div v-if="!uploadResult" class="upload-area">
        <n-upload
          :max="1"
          accept=".xlsx,.xls,.json,.txt"
          @change="handleUpload"
          :show-file-list="false"
        >
          <n-button :loading="uploading" size="large">
            {{ uploading ? '解析中...' : '选择文件' }}
          </n-button>
        </n-upload>
        <span class="upload-hint">直接上传文件进行评测，无需跑批</span>
        <p v-if="uploadError" class="upload-error">{{ uploadError }}</p>
      </div>

      <!-- Eval panel -->
      <EvalPanel
        v-if="uploadResult"
        :task-id="taskId"
        :columns="uploadResult.columns"
        :file-id="uploadResult.file_id"
        :standalone="true"
      />

      <!-- Select existing batch task result -->
      <div v-if="batchTasks.length > 0" class="existing-tasks">
        <h3>或选择已有跑批结果评测</h3>
        <div v-for="t in batchTasks.filter(t => t.status === 'completed')" :key="t.id" class="task-item">
          <span>{{ t.title }} ({{ t.filename }})</span>
          <n-button size="small" @click="selectBatchTask(t.id)">评测</n-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { NButton, NUpload, useMessage } from 'naive-ui'
import { useBatchStore } from '../stores/batch'
import * as batchApi from '../api/batch'
import EvalPanel from '../components/EvalPanel.vue'
import type { UploadResponse } from '../types'

const batchStore = useBatchStore()
const message = useMessage()
const uploading = ref(false)
const uploadError = ref('')
const uploadResult = ref<UploadResponse | null>(null)
const taskId = ref('')
const batchTasks = ref<any[]>([])

// React to store changes (new task / select task from sidebar)
watch(() => batchStore.uploadResult, (val) => {
  if (!val) {
    uploadResult.value = null
    taskId.value = ''
  }
})

watch(() => batchStore.currentTask, (task) => {
  if (!task) {
    uploadResult.value = null
    taskId.value = ''
  }
})

async function handleUpload(opts: { file: any; fileList: any[] }) {
  uploadError.value = ''
  uploading.value = true
  try {
    const rawFile = opts.file.file as File
    const result = await batchApi.uploadExcel(rawFile)
    uploadResult.value = result
    taskId.value = result.task_id
    await batchStore.loadBatchTasks()
    batchTasks.value = batchStore.batchTasks
  } catch (e: any) {
    uploadError.value = e.message || '上传失败'
  } finally {
    uploading.value = false
  }
}

async function selectBatchTask(id: string) {
  await batchStore.selectBatchTask(id)
  if (batchStore.uploadResult) {
    uploadResult.value = batchStore.uploadResult
    taskId.value = id
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
