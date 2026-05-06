<template>
  <div class="batch-panel">
    <div class="batch-header">
      <h2>批量跑批</h2>
    </div>

    <div class="batch-body">
      <!-- Step 1: Upload -->
      <div class="step">
        <div class="step-title">1. 上传文件</div>
        <div class="upload-area" v-if="!uploadResult">
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
          <span class="upload-hint">支持 .xlsx / .xls / .json / .txt 格式</span>
          <div class="format-tips">
            <div class="format-tip">
              <span class="format-label">Excel</span>
              .xlsx / .xls，首行为列名，后续行为数据行。
            </div>
            <div class="format-tip">
              <span class="format-label">JSON Lines</span>
              .json / .txt 均可，每行一个 JSON 对象，键名自动作为列名。<br/>
              <code>{"name": "张三", "age": 25}</code>
            </div>
            <div class="format-tip">
              <span class="format-label">纯文本</span>
              .json / .txt 均可，每行一条数据，自动归入 <code>input</code> 列。
            </div>
          </div>
          <p v-if="uploadError" class="upload-error">{{ uploadError }}</p>
        </div>
        <div v-else class="upload-info">
          <div class="file-tag">
            {{ uploadResult.filename }}
            <span class="file-meta">({{ uploadResult.total_rows }} 行, {{ uploadResult.columns.length }} 列)</span>
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
          <div class="table-scroll">
          <n-data-table
            v-if="uploadResult.preview.length"
            :columns="previewColumns"
            :data="uploadResult.preview"
            :bordered="true"
            :single-line="false"
            size="small"
            :max-height="320"
            :scroll-x="600"
          />
          </div>
        </div>
      </div>

      <!-- Step 2: Config -->
      <div class="step" v-if="uploadResult">
        <div class="step-title">2. 配置参数</div>
        <div class="config-grid">
          <div class="config-item">
            <label>输入列</label>
            <n-select v-model:value="config.input_columns" :options="columnOptions" multiple />
          </div>
          <div class="config-item">
            <label>模型</label>
            <n-select v-model:value="config.api_key_id" :options="keyOptions" />
          </div>
          <div class="config-item">
            <label>并发数</label>
            <n-input-number v-model:value="config.concurrency" :min="1" :max="20" />
          </div>
          <div class="config-item">
            <label>输出列名</label>
            <n-input v-model:value="config.output_column_name" placeholder="AI结果" />
          </div>
        </div>
        <div class="config-options">
          <n-checkbox v-model:checked="config.strip_thinking">
            去除思考过程
            <span class="option-hint">（去掉 &lt;/think&gt; 或 &lt;/unused7&gt; 之前的思考内容）</span>
          </n-checkbox>
          <n-checkbox v-model:checked="config.parse_json">
            JSON格式解析
            <span class="option-hint">（自动解析JSON字段并保存为独立列）</span>
          </n-checkbox>
        </div>
        <div class="config-prompt">
          <label>
            Prompt
            <span class="hint" v-if="config.input_columns.length">
              可用变量：
              <code v-for="c in config.input_columns" :key="c" class="var-tag">{{ varLabel(c) }}</code>
            </span>
            <span class="hint" v-else>请先选择输入列</span>
          </label>
          <n-input
            v-model:value="config.prompt"
            type="textarea"
            :autosize="{ minRows: 3, maxRows: 8 }"
            placeholder="请根据以下内容回答：&#10;{{input}}"
          />
        </div>
        <n-button
          type="primary"
          size="large"
          :loading="running"
          :disabled="!canStart"
          @click="startBatch"
          class="run-btn"
        >
          {{ running ? '跑批中...' : '开始跑批' }}
        </n-button>
        <n-button v-if="running" @click="stopBatch" style="margin-left: 10px">停止</n-button>
      </div>

      <!-- Step 3: Progress + Results -->
      <div class="step" v-if="progress.total > 0">
        <div class="step-title">3. 进度与结果</div>
        <n-progress
          type="line"
          :percentage="Math.round((progress.completed / progress.total) * 100)"
          :indicator-text="`${progress.completed} / ${progress.total}`"
          :height="24"
        />
        <div class="table-scroll">
        <n-data-table
          v-if="results.length"
          :columns="resultColumns"
          :data="results"
          :bordered="true"
          :single-line="false"
          size="small"
          :max-height="400"
          :scroll-x="600"
          :row-props="rowProps"
        />
        </div>
        <div v-if="done" class="download-area">
          <n-button type="success" size="large" @click="download">
            下载结果文件
          </n-button>
        </div>
        <p v-if="batchError" class="batch-error">{{ batchError }}</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, h, watch } from 'vue'
import {
  NButton, NUpload, NSelect, NInput, NInputNumber,
  NDataTable, NProgress, NTag, NCheckbox,
} from 'naive-ui'
import { useChatStore } from '../stores/chat'
import { useBatchStore } from '../stores/batch'
import * as batchApi from '../api/batch'
import * as batchTasksApi from '../api/batchTasks'
import type { PreviewRow } from '../types'

interface ResultRow {
  row: number
  input: string
  output: string
  status: 'success' | 'error'
  error?: string
  parsed?: Record<string, string>
}

const store = useChatStore()
const batchStore = useBatchStore()
const uploading = ref(false)
const running = ref(false)
const done = ref(false)
const uploadError = ref('')
const batchError = ref('')
const results = ref<ResultRow[]>([])
const reuploadKey = ref(0)
const runningTaskId = ref<string | null>(null)
const runningResultsSnapshot = ref<ResultRow[]>([])
const progress = reactive({ completed: 0, total: 0 })
let abortController: AbortController | null = null

const uploadResult = computed(() => batchStore.uploadResult)

const config = reactive({
  input_columns: [] as string[],
  api_key_id: null as number | null,
  concurrency: 3,
  output_column_name: 'AI结果',
  prompt: '',
  strip_thinking: false,
  parse_json: false,
})

function varLabel(col: string) {
  return '{{' + col + '}}'
}

const columnOptions = computed(() =>
  (uploadResult.value?.columns || []).map((c) => ({ label: c, value: c })),
)
const keyOptions = computed(() =>
  store.apiKeys
    .filter((k) => k.is_valid || k.is_active)
    .map((k) => ({ label: `${k.name} (${k.model})`, value: k.id })),
)
const canStart = computed(
  () => config.input_columns.length > 0 && config.api_key_id && config.prompt.trim(),
)

const previewColumns = computed(() => {
  if (!uploadResult.value) return []
  return [
    { title: '#', key: 'row', width: 50 },
    ...uploadResult.value.columns.map((c) => ({
      title: c,
      key: `cells.${c}`,
      width: 180,
      ellipsis: { tooltip: true },
      render(row: PreviewRow) {
        return row.cells[c] || ''
      },
    })),
  ]
})

const resultColumns = computed(() => {
  // Collect all unique parsed field names across all results
  const parsedKeys: string[] = []
  if (config.parse_json) {
    const seen = new Set<string>()
    for (const r of results.value) {
      if (r.parsed) {
        for (const k of Object.keys(r.parsed)) {
          if (!seen.has(k)) {
            seen.add(k)
            parsedKeys.push(k)
          }
        }
      }
    }
  }

  return [
    { title: '#', key: 'row', width: 50 },
    { title: '输入', key: 'input', width: 200, ellipsis: { tooltip: true } },
    {
      title: '输出',
      key: 'output',
      width: 240,
      ellipsis: { tooltip: true },
      render(row: ResultRow) {
        if (row.status === 'error') {
          return h('span', { style: { color: '#ef4444' } }, row.error || '错误')
        }
        return row.output
      },
    },
    ...parsedKeys.map((k) => ({
      title: k,
      key: `parsed.${k}`,
      width: 160,
      ellipsis: { tooltip: true },
      render(row: ResultRow) {
        return row.parsed?.[k] ?? ''
      },
    })),
    {
      title: '状态',
      key: 'status',
      width: 70,
      render(row: ResultRow) {
        return h(NTag, { type: row.status === 'success' ? 'success' : 'error', size: 'small', bordered: false }, () =>
          row.status === 'success' ? '完成' : '失败',
        )
      },
    },
  ]
})

function rowProps(row: ResultRow) {
  return row.status === 'error' ? { style: 'background: #fef2f2' } : {}
}

// Load saved config when a task is selected from sidebar
watch(() => batchStore.currentTask, (task) => {
  if (!task) {
    done.value = false
    running.value = false
    results.value = []
    progress.completed = 0
    progress.total = 0
    batchError.value = ''
    config.input_columns = []
    config.api_key_id = null
    config.concurrency = 3
    config.output_column_name = 'AI结果'
    config.prompt = ''
    config.strip_thinking = false
    config.parse_json = false
    return
  }
  if (task.config_json) {
    try {
      const saved = JSON.parse(task.config_json)
      if (saved.input_columns) {
        config.input_columns = saved.input_columns
      } else if (saved.input_column) {
        config.input_columns = [saved.input_column]
      }
      if (saved.output_column_name) config.output_column_name = saved.output_column_name
      if (saved.prompt) config.prompt = saved.prompt
      if (saved.api_key_id) config.api_key_id = saved.api_key_id
      if (saved.concurrency) config.concurrency = saved.concurrency
      if (typeof saved.strip_thinking === 'boolean') config.strip_thinking = saved.strip_thinking
      if (typeof saved.parse_json === 'boolean') config.parse_json = saved.parse_json
    } catch { /* ignore parse errors */ }
  }
  if (task.status === 'running') {
    if (runningTaskId.value === task.id) {
      // Returning to the currently running task — restore state
      running.value = true
      done.value = false
      results.value = [...runningResultsSnapshot.value]
      progress.completed = task.progress_completed
      progress.total = task.progress_total
    } else {
      // A different task that happens to be running (e.g. from another client)
      running.value = false
      done.value = false
      results.value = []
      progress.completed = task.progress_completed
      progress.total = task.progress_total
    }
  } else if (task.status === 'completed' || task.status === 'failed') {
    running.value = false
    done.value = true
    progress.completed = task.progress_completed
    progress.total = task.progress_total
    // Load results from the generated Excel
    batchTasksApi.getTaskResults(task.id).then((rows) => {
      results.value = rows.map((r: any) => ({
        row: r.row,
        input: r.input,
        output: r.output,
        status: r.status as 'success' | 'error',
        parsed: r.parsed,
      }))
    }).catch(() => { /* file may be gone */ })
  } else {
    running.value = false
    done.value = false
    results.value = []
    progress.completed = 0
    progress.total = 0
  }
}, { immediate: true })

async function handleReupload(opts: { file: any; fileList: any[] }) {
  uploadError.value = ''
  uploading.value = true
  try {
    const rawFile = opts.file.file as File
    const result = await batchApi.uploadExcel(rawFile, batchStore.currentTask?.id)
    batchStore.setUploadResult(result)
    // Reset progress and results for the new file
    done.value = false
    results.value = []
    progress.completed = 0
    progress.total = 0
    batchError.value = ''
    // Auto-select first column and active key
    if (config.input_columns.length === 0 && result.columns.length > 0) {
      config.input_columns = [result.columns[0]]
    }
    if (!config.api_key_id) {
      const active = store.activeKey()
      if (active) config.api_key_id = active.id
    }
  } catch (e: any) {
    uploadError.value = e.message || '上传失败'
  } finally {
    uploading.value = false
    reuploadKey.value++
  }
}

async function handleUpload(opts: { file: any; fileList: any[] }) {
  uploadError.value = ''
  uploading.value = true
  try {
    const rawFile = opts.file.file as File
    const result = await batchApi.uploadExcel(rawFile)
    batchStore.setUploadResult(result)
    await batchStore.loadBatchTasks()
    batchStore.currentTask = batchStore.batchTasks.find((t) => t.id === result.task_id) || null
    if (config.input_columns.length === 0 && result.columns.length > 0) {
      config.input_columns = [result.columns[0]]
    }
    if (!config.api_key_id) {
      const active = store.activeKey()
      if (active) config.api_key_id = active.id
    }
  } catch (e: any) {
    uploadError.value = e.message || '上传失败'
  } finally {
    uploading.value = false
  }
}

async function startBatch() {
  if (!config.api_key_id || !batchStore.currentTask) return
  done.value = false
  batchError.value = ''
  results.value = []
  progress.completed = 0
  progress.total = 0
  running.value = true
  runningTaskId.value = batchStore.currentTask!.id

  await batchStore.saveBatchTaskConfig(batchStore.currentTask.id, { ...config })

  runningResultsSnapshot.value = []
  abortController = batchApi.runBatch(
    { ...config, api_key_id: config.api_key_id, file_id: uploadResult.value!.file_id, task_id: batchStore.currentTask.id },
    (completed, total) => {
      if (batchStore.currentTask?.id === runningTaskId.value) {
        progress.completed = completed
        progress.total = total
      }
    },
    (row, input, output, parsed) => {
      const entry = { row, input, output, status: 'success' as const, parsed }
      runningResultsSnapshot.value.unshift(entry)
      if (batchStore.currentTask?.id === runningTaskId.value) {
        results.value.unshift(entry)
      }
    },
    (row, input, error) => {
      const entry = { row, input, output: '', status: 'error' as const, error }
      runningResultsSnapshot.value.unshift(entry)
      if (batchStore.currentTask?.id === runningTaskId.value) {
        results.value.unshift(entry)
      }
    },
    () => {
      const wasMyTask = batchStore.currentTask?.id === runningTaskId.value
      runningTaskId.value = null
      runningResultsSnapshot.value = []
      if (wasMyTask) {
        done.value = true
        running.value = false
      }
    },
    (msg) => {
      batchError.value = msg
      running.value = false
    },
  )
}

function stopBatch() {
  if (abortController) {
    abortController.abort()
    abortController = null
    running.value = false
  }
}

function download() {
  if (!uploadResult.value) return
  const url = batchApi.downloadUrl(uploadResult.value.task_id)
  const a = document.createElement('a')
  a.href = url
  a.download = ''
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
}
</script>

<style scoped>
.batch-panel {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f5f5f7;
  overflow: hidden;
}

.batch-header {
  padding: 0 24px;
  height: 52px;
  display: flex;
  align-items: center;
  background: rgba(255,255,255,0.7);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(0,0,0,0.06);
  flex-shrink: 0;
}

.batch-header h2 {
  font-size: 16px;
  font-weight: 700;
  color: #1a1a2e;
}

.batch-body {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  max-width: 960px;
  margin: 0 auto;
  width: 100%;
}

.step {
  margin-bottom: 28px;
}

.step-title {
  font-size: 14px;
  font-weight: 600;
  color: #1a1a2e;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #e5e5ea;
}

.upload-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 40px;
  border: 2px dashed #d9d9de;
  border-radius: 12px;
  background: #fff;
}

.upload-hint {
  font-size: 12px;
  color: #b0b0b8;
}

.format-tips {
  width: 100%;
  max-width: 480px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  text-align: left;
}

.format-tip {
  font-size: 12px;
  color: #6b6b78;
  padding: 8px 12px;
  background: #f8f8fa;
  border-radius: 6px;
  border: 1px solid #eeeef2;
  line-height: 1.6;
}

.format-label {
  font-weight: 600;
  color: #6366f1;
  margin-right: 6px;
  font-size: 12px;
}

.format-tip code {
  background: rgba(99, 102, 241, 0.08);
  color: #6366f1;
  padding: 1px 5px;
  border-radius: 3px;
  font-size: 11px;
}

.upload-error {
  font-size: 13px;
  color: #ef4444;
}

.upload-info {
  background: #fff;
  border-radius: 12px;
  border: 1px solid #e5e5ea;
  padding: 16px;
  position: relative;
}

.file-tag {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 12px;
}

.reupload-btn {
  position: absolute;
  top: 12px;
  right: 12px;
}

.file-meta {
  font-weight: 400;
  color: #8e8e9a;
  font-size: 12px;
}

.table-scroll {
  overflow-x: auto;
  margin-top: 8px;
}

.config-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
  margin-bottom: 14px;
}

.config-options {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 14px;
  padding: 10px 14px;
  background: #fff;
  border-radius: 8px;
  border: 1px solid #e5e5ea;
}

.option-hint {
  font-size: 11px;
  color: #8e8e9a;
  margin-left: 4px;
}

.var-tag {
  background: rgba(99, 102, 241, 0.08);
  color: #6366f1;
  padding: 1px 5px;
  border-radius: 4px;
  font-size: 11px;
  margin-left: 3px;
}

.config-item label,
.config-prompt label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: #4b4b60;
  margin-bottom: 4px;
}

.config-prompt {
  margin-bottom: 14px;
}

.hint {
  font-weight: 400;
  color: #8e8e9a;
  font-size: 12px;
}
.hint code {
  background: rgba(99, 102, 241, 0.08);
  color: #6366f1;
  padding: 1px 4px;
  border-radius: 3px;
  font-size: 12px;
}

.run-btn {
  margin-top: 4px;
}

.download-area {
  margin-top: 16px;
}

.batch-error {
  margin-top: 12px;
  color: #ef4444;
  font-size: 13px;
}
</style>
