<template>
  <div class="eval-panel">
    <div class="step-title">评测</div>

    <!-- Task selector (standalone mode without taskId prop) -->
    <div v-if="standalone && !propsTaskId" class="eval-task-selector">
      <n-select
        v-model:value="selectedTaskId"
        :options="taskOptions"
        placeholder="选择跑批任务"
        @update:value="onTaskSelect"
      />
    </div>

    <!-- Loading state -->
    <div v-if="loadingTask">
      <p class="eval-hint">加载中...</p>
    </div>

    <!-- No task selected -->
    <div v-else-if="!taskId">
      <p class="eval-hint">请先选择跑批任务</p>
    </div>

    <!-- No result file yet -->
    <div v-else-if="!hasResultFile">
      <p class="eval-hint">跑批任务未完成或无结果文件</p>
    </div>

    <!-- Main content -->
    <template v-else>
      <!-- Data preview -->
      <div v-if="dataPreview.length > 0" class="eval-data-preview">
        <div class="step-title">数据预览</div>
        <div class="table-scroll">
          <n-data-table
            :columns="dataPreviewColumns"
            :data="dataPreview"
            :bordered="true"
            :single-line="false"
            size="small"
            :max-height="320"
            :scroll-x="600"
          />
        </div>
      </div>

      <!-- Tab switcher -->
      <div class="eval-tabs">
        <div
          :class="['eval-tab', { active: activeTab === 'classification' }]"
          @click="activeTab = 'classification'"
        >
          客观评测
          <span v-if="classResult" class="tab-status done">✓</span>
        </div>
        <div
          :class="['eval-tab', { active: activeTab === 'llm_scoring' }]"
          @click="activeTab = 'llm_scoring'"
        >
          主观测评
          <span v-if="llmScoringDone" class="tab-status done">✓</span>
        </div>
      </div>

      <!-- Classification Tab -->
      <div v-if="activeTab === 'classification'" class="eval-tab-content">
        <!-- Config (always visible) -->
        <div class="eval-config">
          <div class="eval-config-grid">
            <div class="eval-config-item">
              <label>标签列（答案）</label>
              <n-select v-model:value="classConfig.label_column" :options="columnOptions" placeholder="选择标签列" />
            </div>
            <div class="eval-config-item">
              <label>模型结果列</label>
              <n-select v-model:value="classConfig.predict_column" :options="columnOptions" placeholder="选择结果列" filterable />
            </div>
          </div>

          <div class="mapping-section">
            <div class="mapping-header">
              <label>值映射（模型输出 → 标签值）</label>
              <n-button text size="small" type="primary" @click="addMapping">+ 添加映射</n-button>
            </div>
            <div v-if="classConfig.mappings.length > 0" class="mapping-table">
              <div class="mapping-row head">
                <span>模型输出</span>
                <span>映射为 Label</span>
                <span></span>
              </div>
              <div v-for="(m, i) in classConfig.mappings" :key="i" class="mapping-row">
                <n-input v-model:value="m.model_output" size="small" placeholder="如：正面" />
                <n-input v-model:value="m.label_value" size="small" placeholder="如：1" />
                <n-button text size="tiny" type="error" @click="classConfig.mappings.splice(i, 1)">✕</n-button>
              </div>
            </div>
          </div>

          <n-button type="primary" :loading="classRunning" @click="runClassification" :disabled="!classConfig.label_column || !classConfig.predict_column">
            {{ classRunning ? '评测中...' : '开始客观评测' }}
          </n-button>
          <n-button v-if="classRunning" type="warning" size="small" @click="stopClassification" style="margin-left: 8px">停止</n-button>
          <p v-if="classError" class="eval-error">{{ classError }}</p>
        </div>

        <!-- Results -->
        <div v-if="classResult">
          <div class="eval-summary">
            <div class="eval-summary-item">
              <span class="eval-summary-label">总体准确率 (Accuracy)</span>
              <span class="eval-summary-value">{{ classResult.accuracy.toFixed(4) }}</span>
            </div>
            <div class="eval-summary-item">
              <span class="eval-summary-label">总样本数</span>
              <span class="eval-summary-value">{{ classResult.total_samples }}</span>
            </div>
            <div class="eval-summary-item">
              <span class="eval-summary-label">分类数量</span>
              <span class="eval-summary-value">{{ classResult.num_classes }}</span>
            </div>
          </div>

          <h4>混淆矩阵</h4>
          <div class="cm-table-wrap">
            <table class="cm-table">
              <thead>
                <tr>
                  <th class="cm-corner"><div class="cm-diag"><span class="cm-actual">实际值</span><span class="cm-predict">预测值</span></div></th>
                  <th v-for="l in classResult.labels" :key="l" class="cm-col-h">{{ l }}</th>
                  <th class="cm-col-sum">合计</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, i) in classResult.confusion_matrix" :key="i">
                  <td class="cm-row-h">{{ classResult.labels[i] }}</td>
                  <td v-for="(val, j) in row" :key="j" :class="{ 'cm-diag-cell': i === j, 'cm-off-cell': i !== j }">{{ val }}</td>
                  <td class="cm-row-sum">{{ row.reduce((a: number, b: number) => a + b, 0) }}</td>
                </tr>
                <tr class="cm-col-sum-row">
                  <td>合计</td>
                  <td v-for="j in classResult.labels.length" :key="j">
                    {{ classResult.confusion_matrix.reduce((s: number, r: number[]) => s + r[j - 1], 0) }}
                  </td>
                  <td>{{ classResult.total_samples }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <h4>各分类指标</h4>
          <n-data-table
            :columns="perClassColumns"
            :data="classResult.per_class"
            :bordered="true"
            size="small"
          />

          <h4>汇总指标</h4>
          <n-data-table
            :columns="avgColumns"
            :data="avgRows"
            :bordered="true"
            size="small"
          />

          <div class="eval-actions">
            <n-button type="success" @click="downloadClassification">下载评测结果 Excel</n-button>
            <n-button @click="classResult = null" style="margin-left: 8px;">重新评测</n-button>
          </div>
        </div>
      </div>

      <!-- LLM Scoring Tab -->
      <div v-if="activeTab === 'llm_scoring'" class="eval-tab-content">
        <!-- Config (always visible) -->
        <div class="eval-config">
          <div class="eval-config-grid">
            <div class="eval-config-item">
              <label>评分模型</label>
              <n-select v-model:value="llmConfig.api_key_id" :options="keyOptions" placeholder="选择模型" />
            </div>
            <div class="eval-config-item">
              <label>并发数</label>
              <n-input-number v-model:value="llmConfig.concurrency" :min="1" :max="20" />
            </div>
          </div>
          <div class="eval-config-item" style="margin-bottom: 12px;">
            <label>变量列（可多选或手动输入，用于 Prompt 中 <code v-pre>{{列名}}</code> 引用）</label>
            <n-select
              v-model:value="llmConfig.input_columns"
              :options="columnOptions"
              multiple
              filterable
              placeholder="选择变量列"
            />
          </div>
          <div class="eval-config-item" style="margin-bottom: 12px;">
            <label>输出列名</label>
            <n-input v-model:value="llmConfig.output_column_name" placeholder="评分" />
          </div>
          <div class="eval-prompt">
            <label>
              评分 Prompt
              <span class="hint" v-if="llmConfig.input_columns.length">
                可用变量：
                <code v-for="c in llmConfig.input_columns" :key="c" class="var-tag">{{ varLabel(c) }}</code>
                <span class="hint-slash"> · 输入 <code>/</code> 快速选择</span>
              </span>
            </label>
            <div class="prompt-textarea-wrapper" ref="promptTextareaRef">
              <pre class="prompt-backdrop" v-html="promptHighlighted" />
              <textarea
                ref="textareaRef"
                v-model="llmConfig.prompt"
                class="prompt-textarea"
                :class="{ 'is-composing': isComposing }"
                rows="8"
                placeholder="请根据以下标准对回答进行评分..."
                @scroll="onPromptScroll"
                @input="onPromptInput"
                @keydown="onPromptKeydown"
                @focus="onPromptFocus"
                @compositionstart="isComposing = true"
                @compositionend="isComposing = false"
              />
              <div v-if="showSlashPicker" class="slash-picker">
                <div
                  v-for="(col, idx) in filteredSlashColumns"
                  :key="col"
                  :class="['slash-picker-item', { active: idx === slashHighlightIdx }]"
                  @mousedown.prevent="selectSlashColumn(col)"
                >
                  <code>{{ varLabel(col) }}</code>
                  <span>{{ col }}</span>
                </div>
                <div v-if="filteredSlashColumns.length === 0" class="slash-picker-empty">无匹配列</div>
              </div>
            </div>
          </div>
          <n-button type="primary" :loading="llmRunning" @click="runLLMScoring" :disabled="!llmConfig.api_key_id || !llmConfig.input_columns.length || !llmConfig.prompt.trim()">
            {{ llmRunning ? '评分中...' : '开始主观评测' }}
          </n-button>
          <p v-if="llmError" class="eval-error">{{ llmError }}</p>
        </div>

        <!-- Progress -->
        <div v-if="llmRunning || llmScoringDone">
          <n-progress
            type="line"
            :percentage="llmProgress.total > 0 ? Math.round((llmProgress.completed / llmProgress.total) * 100) : 0"
            :indicator-text="llmProgress.total > 0 ? `${llmProgress.completed} / ${llmProgress.total}` : '准备中...'"
            :height="24"
          />
          <n-button v-if="llmRunning" type="warning" size="small" @click="stopLLMScoring" style="margin-top: 8px">停止评分</n-button>
        </div>

        <!-- Results table -->
        <div v-if="llmScores.length > 0" class="table-scroll">
          <n-data-table
            :columns="llmScoreColumns"
            :data="llmScores"
            :bordered="true"
            :single-line="false"
            size="small"
            :max-height="400"
            virtual-scroll
          />
        </div>

        <div v-if="llmScoringDone" class="eval-actions">
          <p>
            <span>评分完成 · 平均分：<strong>{{ llmAvgScore }}</strong></span>
            <span style="margin-left: 12px; color: #666;">{{ llmScores.length }} 条</span>
          </p>
          <n-button type="success" @click="downloadLLMScoring">下载评分结果 Excel</n-button>
          <n-button @click="resetLLMScoring" style="margin-left: 8px;">重新评分</n-button>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, h, watch, onMounted, nextTick } from 'vue'
import {
  NButton, NSelect, NInput, NInputNumber, NDataTable, NProgress, NTag,
  useMessage,
} from 'naive-ui'
import { useChatStore } from '../stores/chat'
import { useBatchStore } from '../stores/batch'
import * as evalApi from '../api/eval'
import * as batchTasksApi from '../api/batchTasks'
import { authFetch } from '../api/client'
import type {
  BatchTask,
  ClassificationEvalResult,
  LLMScoringEvalConfig,
} from '../types'

interface LLMScoreRow {
  row: number
  score: string
  status: 'success' | 'error'
  error?: string
}

const props = defineProps<{
  taskId?: string
  columns?: string[]
  fileId?: string
  standalone?: boolean
}>()

// Rename to avoid conflict with computed taskId
const propsTaskId = computed(() => props.taskId)

const store = useChatStore()
const batchStore = useBatchStore()
const message = useMessage()

// Task selection (standalone mode)
const selectedTaskId = ref<string | null>(null)
const loadingTask = ref(false)
const hasResultFile = ref(false)
const internalColumns = ref<string[]>([])

// Use props.columns if provided, otherwise internal
const columns = computed(() => props.columns || internalColumns.value)

// Computed taskId: prefer props, then selected
const taskId = computed(() => propsTaskId.value || selectedTaskId.value)

const taskOptions = computed(() =>
  batchStore.tasks
    .filter(t => t.status === 'completed')
    .map(t => ({ label: t.title, value: t.id }))
)

const activeTab = ref<'classification' | 'llm_scoring'>('classification')

// Classification state
const classConfig = reactive({
  label_column: '',
  predict_column: '',
  mappings: [] as { model_output: string; label_value: string }[],
})
const classResult = ref<ClassificationEvalResult | null>(null)
const classRunning = ref(false)
const classError = ref('')

// LLM scoring state
const llmConfig = reactive<LLMScoringEvalConfig>({
  api_key_id: 0,
  prompt: '',
  input_columns: [],
  output_column_name: '评分',
  concurrency: 3,
})
const llmScores = ref<LLMScoreRow[]>([])
const llmScoringDone = ref(false)
const llmRunning = ref(false)
const llmError = ref('')
const llmAvgScore = ref(0)
const llmProgress = reactive({ completed: 0, total: 0 })
let llmAbortController: AbortController | null = null
let classAbortController: AbortController | null = null

// Data preview
const dataPreview = ref<any[]>([])
const dataPreviewLoading = ref(false)
const dataPreviewHeaders = ref<string[]>([])
const resultFileColumns = ref<string[]>([])

async function loadDataPreview(tid: string) {
  dataPreviewLoading.value = true
  try {
    const result = await batchTasksApi.getTaskPreview(tid)
    dataPreviewHeaders.value = result.headers
    dataPreview.value = result.preview
    // Use result file headers for column options (includes AI output column)
    resultFileColumns.value = result.headers
  } catch {
    dataPreview.value = []
  } finally {
    dataPreviewLoading.value = false
  }
}

const dataPreviewColumns = computed(() =>
  dataPreviewHeaders.value.map(h => ({
    title: h,
    key: `cells.${h}`,
    width: 150,
    ellipsis: { tooltip: true },
    render(row: Record<string, unknown>) {
      return row.cells?.[h] != null ? String(row.cells[h]) : ''
    },
  }))
)

const columnOptions = computed(() => {
  const cols = resultFileColumns.value.length > 0 ? resultFileColumns.value : columns.value
  return cols.map((c) => ({ label: c, value: c }))
})

const keyOptions = computed(() =>
  store.apiKeys
    .filter(k => k.is_valid || k.is_active)
    .map(k => ({ label: `${k.name} (${k.model})`, value: k.id }))
)

function varLabel(col: string) {
  return `{{${col}}}`
}

const promptHighlighted = computed(() => {
  const text = llmConfig.prompt
  if (!text) return ''
  const cols = new Set(llmConfig.input_columns)
  let escaped = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
  escaped = escaped.replace(/\{\{(.+?)\}\}/g, (_match: string, name: string) => {
    const valid = cols.has(name.trim())
    const color = valid ? '#10a37f' : '#ef4444'
    return `<span style="color:${color}">{{${name}}}</span>`
  })
  return escaped
})

// ── Slash / variable picker ──────────────────────
const textareaRef = ref<HTMLTextAreaElement | null>(null)
const promptTextareaRef = ref<HTMLElement | null>(null)
const isComposing = ref(false)
const showSlashPicker = ref(false)
const slashStartPos = ref(-1)
const slashQuery = ref('')
const slashHighlightIdx = ref(0)

const filteredSlashColumns = computed(() => {
  const q = slashQuery.value.toLowerCase()
  if (!q) return llmConfig.input_columns
  return llmConfig.input_columns.filter((c) => c.toLowerCase().includes(q))
})

function detectSlash() {
  const ta = textareaRef.value
  if (!ta) return
  const cursorPos = ta.selectionStart
  const textBefore = llmConfig.prompt.slice(0, cursorPos)

  const slashIdx = textBefore.lastIndexOf('/')
  if (slashIdx !== -1 && llmConfig.input_columns.length > 0) {
    const charBefore = textBefore[slashIdx - 1]
    if (slashIdx === 0 || charBefore === ' ' || charBefore === '\n') {
      const query = textBefore.slice(slashIdx + 1)
      if (!query.includes(' ') && !query.includes('\n')) {
        slashStartPos.value = slashIdx
        slashQuery.value = query
        showSlashPicker.value = true
        slashHighlightIdx.value = 0
        return
      }
    }
  }
  showSlashPicker.value = false
}

function selectSlashColumn(col: string) {
  if (slashStartPos.value === -1) return
  const before = llmConfig.prompt.slice(0, slashStartPos.value)
  const after = llmConfig.prompt.slice(slashStartPos.value + 1 + slashQuery.value.length)
  llmConfig.prompt = before + '{{' + col + '}}' + after
  showSlashPicker.value = false
  nextTick(() => {
    const ta = textareaRef.value
    if (ta) {
      const newPos = before.length + col.length + 4
      ta.focus()
      ta.setSelectionRange(newPos, newPos)
    }
  })
}

function onPromptFocus() {
  detectSlash()
}

function onPromptInput() {
  detectSlash()
}

function onPromptKeydown(e: KeyboardEvent) {
  if (!showSlashPicker.value) return

  const items = filteredSlashColumns.value
  if (e.key === 'ArrowDown') {
    e.preventDefault()
    slashHighlightIdx.value = Math.min(slashHighlightIdx.value + 1, Math.max(items.length - 1, 0))
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    slashHighlightIdx.value = Math.max(slashHighlightIdx.value - 1, 0)
  } else if (e.key === 'Enter' || e.key === 'Tab') {
    e.preventDefault()
    const col = items[slashHighlightIdx.value]
    if (col) selectSlashColumn(col)
  } else if (e.key === 'Escape') {
    e.preventDefault()
    showSlashPicker.value = false
  }
}

function onPromptScroll(e: Event) {
  const ta = e.target as HTMLTextAreaElement
  const backdrop = promptTextareaRef.value?.querySelector('.prompt-backdrop') as HTMLElement | null
  if (backdrop) {
    backdrop.scrollTop = ta.scrollTop
    backdrop.scrollLeft = ta.scrollLeft
  }
}

function addMapping() {
  classConfig.mappings.push({ model_output: '', label_value: '' })
}

function restoreEvalConfig(task: BatchTask) {
  if (!task.eval_config_json) return
  try {
    const saved = JSON.parse(task.eval_config_json)
    if (saved.classification) {
      classConfig.label_column = saved.classification.label_column || ''
      classConfig.predict_column = saved.classification.predict_column || ''
      classConfig.mappings = saved.classification.mappings || []
    }
    if (saved.llm_scoring) {
      llmConfig.api_key_id = saved.llm_scoring.api_key_id || 0
      llmConfig.prompt = saved.llm_scoring.prompt || ''
      llmConfig.input_columns = saved.llm_scoring.input_columns || []
      llmConfig.output_column_name = saved.llm_scoring.output_column_name || '评分'
      llmConfig.concurrency = saved.llm_scoring.concurrency || 3
    }
    configRestored.value = true
  } catch { /* ignore */ }
}

let saveTimer: ReturnType<typeof setTimeout> | null = null
const configRestored = ref(false)

function saveEvalConfig() {
  if (!taskId.value) return
  if (saveTimer) clearTimeout(saveTimer)
  saveTimer = setTimeout(async () => {
    const config = JSON.stringify({
      enabled: true,
      method: activeTab.value === 'classification' ? 'classification' : 'llm_scoring',
      classification: {
        label_column: classConfig.label_column,
        predict_column: classConfig.predict_column,
        mappings: classConfig.mappings,
      },
      llm_scoring: {
        api_key_id: llmConfig.api_key_id,
        prompt: llmConfig.prompt,
        input_columns: llmConfig.input_columns,
        output_column_name: llmConfig.output_column_name,
        concurrency: llmConfig.concurrency,
      },
    })
    try {
      await batchTasksApi.updateBatchTask(taskId.value!, { eval_config_json: config })
    } catch { /* ignore */ }
  }, 600)
}

// Auto-save eval config on changes (debounced)
watch([classConfig, llmConfig], () => {
  if (configRestored.value) saveEvalConfig()
}, { deep: true })

// ── Task selection ──

async function onTaskSelect(tid: string) {
  loadingTask.value = true
  hasResultFile.value = false
  internalColumns.value = []
  classResult.value = null
  llmScoringDone.value = false
  llmScores.value = []
  dataPreview.value = []
  dataPreviewHeaders.value = []
  configRestored.value = false
  // Reset config to defaults
  classConfig.label_column = ''
  classConfig.predict_column = ''
  classConfig.mappings = []
  llmConfig.api_key_id = 0
  llmConfig.prompt = ''
  llmConfig.input_columns = []
  llmConfig.output_column_name = '评分'
  llmConfig.concurrency = 3

  try {
    // Get task info
    const task = await batchTasksApi.getBatchTask(tid)
    internalColumns.value = JSON.parse(task.columns)
    restoreEvalConfig(task)

    // Check if result file exists by trying to get preview
    hasResultFile.value = task.status === 'completed'

    // Load existing results and preview
    await loadExistingResults(tid)
    loadDataPreview(tid)
  } catch (e) {
    message.error('加载任务失败')
  } finally {
    loadingTask.value = false
    configRestored.value = true
  }

  // Set default API key (only if not restored)
  const active = store.activeKey()
  if (active && (active.is_valid || active.is_active) && !llmConfig.api_key_id) {
    llmConfig.api_key_id = active.id
  }
}

async function loadExistingResults(tid: string) {
  try {
    const classData = await evalApi.checkClassificationResult(tid)
    if (classData) {
      classResult.value = classData
    }

    const llmData = await evalApi.getLLMScoringResult(tid)
    if (llmData) {
      llmScores.value = llmData.scores
      llmAvgScore.value = llmData.avg_score
      llmProgress.completed = llmData.total
      llmProgress.total = llmData.total
      llmScoringDone.value = true
    }
  } catch { /* ignore */ }
}

// ── Classification ──

function runClassification() {
  if (!taskId.value) return
  classRunning.value = true
  classError.value = ''
  classResult.value = null

  classAbortController = evalApi.runClassificationEval(
    taskId.value,
    {
      label_column: classConfig.label_column,
      predict_column: classConfig.predict_column,
      mappings: classConfig.mappings,
    },
    (result) => {
      classResult.value = result
      classRunning.value = false
      classAbortController = null
    },
    (msg) => {
      classError.value = msg
      classRunning.value = false
      classAbortController = null
    },
  )
}

function stopClassification() {
  if (classAbortController) {
    classAbortController.abort()
    classAbortController = null
    classRunning.value = false
  }
}

async function downloadClassification() {
  if (!taskId.value) return
  const url = evalApi.classificationDownloadUrl(taskId.value)
  const resp = await authFetch(url)
  if (!resp.ok) { message.warning('下载失败'); return }
  const blob = await resp.blob()
  const objUrl = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = objUrl
  a.download = `评测结果.xlsx`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(objUrl)
}

// ── LLM Scoring ──

async function runLLMScoring() {
  if (!taskId.value) return
  llmRunning.value = true
  llmError.value = ''
  llmScores.value = []
  llmProgress.completed = 0
  llmProgress.total = 0

  llmAbortController = evalApi.runLLMScoringEval(
    taskId.value!,
    {
      api_key_id: llmConfig.api_key_id,
      prompt: llmConfig.prompt,
      input_columns: llmConfig.input_columns,
      output_column_name: llmConfig.output_column_name,
      concurrency: llmConfig.concurrency,
    },
    (completed, total) => {
      llmProgress.completed = completed
      llmProgress.total = total
    },
    (row, score) => {
      llmScores.value.push({
        row,
        score,
        status: 'success',
      })
    },
    (row, error) => {
      llmScores.value.push({
        row,
        score: '',
        status: 'error',
        error,
      })
    },
    (total, avgScore) => {
      llmScoringDone.value = true
      llmAvgScore.value = avgScore
      llmRunning.value = false
    },
    (msg) => {
      llmError.value = msg
      llmRunning.value = false
    },
  )
}

function stopLLMScoring() {
  if (llmAbortController) {
    llmAbortController.abort()
    llmAbortController = null
  }
}

function resetLLMScoring() {
  llmScoringDone.value = false
  llmScores.value = []
  llmAvgScore.value = 0
  llmProgress.completed = 0
  llmProgress.total = 0
}

async function downloadLLMScoring() {
  if (!taskId.value) return
  const url = evalApi.llmScoringDownloadUrl(taskId.value)
  const resp = await authFetch(url)
  if (!resp.ok) { message.warning('下载失败'); return }
  const blob = await resp.blob()
  const objUrl = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = objUrl
  a.download = `评分结果.xlsx`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(objUrl)
}

// ── Table columns ──

const perClassColumns = [
  { title: '分类', key: 'class_name' },
  { title: 'Precision', key: 'precision' },
  { title: 'Recall', key: 'recall' },
  { title: 'F1 Score', key: 'f1' },
]

const avgColumns = [
  { title: '类型', key: 'type' },
  { title: 'Precision', key: 'precision' },
  { title: 'Recall', key: 'recall' },
  { title: 'F1 Score', key: 'f1' },
]

const avgRows = computed(() => {
  if (!classResult.value) return []
  return [
    { type: 'Micro Avg', ...classResult.value.micro_avg },
    { type: 'Macro Avg', ...classResult.value.macro_avg },
  ]
})

const llmScoreColumns = [
  { title: '#', key: 'row', width: 50 },
  { title: '评分', key: 'score', width: 100,
    render(row: LLMScoreRow) {
      if (row.status === 'error') return h('span', { style: { color: '#ef4444' } }, row.error || '错误')
      return row.score
    }
  },
  {
    title: '状态', key: 'status', width: 70,
    render(row: LLMScoreRow) {
      return h(NTag, { type: row.status === 'success' ? 'success' : 'error', size: 'small', bordered: false }, () =>
        row.status === 'success' ? '完成' : '失败',
      )
    },
  },
]

// ── Init ──

onMounted(() => {
  // Set default API key (only if not restored from saved config)
  if (!llmConfig.api_key_id) {
    const active = store.activeKey()
    if (active && (active.is_valid || active.is_active)) {
      llmConfig.api_key_id = active.id
    }
  }

  // If columns and taskId provided via props, mark as ready and restore config
  if (props.columns && props.columns.length > 0 && propsTaskId.value) {
    hasResultFile.value = true
    loadExistingResults(propsTaskId.value)
    loadDataPreview(propsTaskId.value)
    // Fetch task to restore eval config
    batchTasksApi.getBatchTask(propsTaskId.value).then(task => {
      restoreEvalConfig(task)
    }).catch(() => {})
  }
})

// Watch taskId prop (for embedded mode)
watch([propsTaskId, () => props.columns], async ([tid, cols]) => {
  if (tid) {
    // If columns provided via props, use them directly
    if (cols && cols.length > 0) {
      hasResultFile.value = true
      await loadExistingResults(tid)
      loadDataPreview(tid)
      // Fetch task to restore eval config
      batchTasksApi.getBatchTask(tid).then(task => {
        restoreEvalConfig(task)
        configRestored.value = true
      }).catch(() => {
        configRestored.value = true
      })
    } else {
      // Otherwise fetch from task
      loadingTask.value = true
      try {
        const task = await batchTasksApi.getBatchTask(tid)
        internalColumns.value = JSON.parse(task.columns)
        restoreEvalConfig(task)
        hasResultFile.value = task.status === 'completed'
        await loadExistingResults(tid)
        loadDataPreview(tid)
      } catch { /* ignore */ }
      finally { loadingTask.value = false }
    }
  }
}, { immediate: true })
</script>

<style scoped>
.eval-panel {
  padding: 16px;
}

.step-title {
  font-size: 16px;
  font-weight: 600;
  color: #1a1a2e;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #e5e5ea;
}

.eval-data-preview {
  margin-bottom: 20px;
  background: #fff;
  border-radius: 10px;
  border: 1px solid #e8e8ec;
  padding: 16px;
}

.eval-task-selector {
  margin-bottom: 16px;
}

.eval-hint {
  color: #999;
  font-size: 13px;
  margin: 8px 0;
}

.eval-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}

.eval-tab {
  padding: 8px 18px;
  background: #f3f4f6;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 6px;
  border: 1px solid transparent;
  color: #6b7280;
}

.eval-tab:hover {
  background: #e5e7eb;
}

.eval-tab.active {
  border-color: #6366f1;
  background: #eef2ff;
  color: #4338ca;
}

.tab-status.done {
  color: #18a058;
  font-weight: bold;
}

.eval-tab-content {
  padding: 12px 0;
}

.eval-config-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 12px;
}

.eval-config-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.eval-config-item label {
  font-size: 13px;
  font-weight: 500;
  color: #4b4b60;
}

.mapping-section {
  margin-top: 12px;
}

.mapping-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.mapping-header label {
  font-size: 13px;
  font-weight: 500;
  color: #4b4b60;
}

.mapping-table {
  border: 1px solid #e0e0e6;
  border-radius: 6px;
  padding: 8px;
}

.mapping-row {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 4px;
}

.mapping-row.head {
  font-size: 11px;
  color: #888;
  margin-bottom: 8px;
  padding-bottom: 4px;
  border-bottom: 1px solid #e0e0e6;
}

.mapping-row.head span:first-child {
  flex: 1;
}
.mapping-row.head span:nth-child(2) {
  flex: 1;
}

.mapping-row:not(.head) .n-input {
  flex: 1;
}

.eval-prompt {
  margin-top: 12px;
}

.eval-prompt label {
  font-size: 13px;
  font-weight: 500;
  color: #4b4b60;
  display: block;
  margin-bottom: 4px;
}

.eval-prompt .hint {
  color: #999;
  font-size: 11px;
  margin-left: 8px;
}

.var-tag {
  background: #f0f0f4;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
  margin-right: 4px;
}

.eval-error {
  color: #ef4444;
  font-size: 13px;
  margin-top: 8px;
}

.eval-summary {
  display: flex;
  gap: 24px;
  margin-bottom: 16px;
  padding: 16px 20px;
  background: linear-gradient(135deg, #f8f9ff 0%, #f0f4ff 100%);
  border-radius: 12px;
  border: 1px solid rgba(99, 102, 241, 0.12);
}

.eval-summary-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.eval-summary-label {
  font-size: 12px;
  color: #6b7280;
}

.eval-summary-value {
  font-size: 20px;
  font-weight: 700;
  color: #4f46e5;
}

.eval-actions {
  margin-top: 20px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px;
  background: #fff;
  border-radius: 10px;
  border: 1px solid #e8e8ec;
}

.eval-actions p {
  font-size: 14px;
  color: #374151;
  flex: 1;
}

.cm-table-wrap {
  overflow-x: auto;
  margin-bottom: 16px;
}

.cm-table {
  border-collapse: collapse;
  font-size: 12px;
  width: 100%;
  border-radius: 8px;
  overflow: hidden;
}

.cm-table th, .cm-table td {
  border: 1px solid #e8e8ec;
  padding: 8px 12px;
  text-align: center;
}

.cm-corner {
  background: #f8f9fc;
  width: 80px;
}

.cm-diag {
  position: relative;
  height: 40px;
}

.cm-actual {
  position: absolute;
  top: 2px;
  left: 6px;
  font-size: 10px;
  color: #9ca3af;
}

.cm-predict {
  position: absolute;
  bottom: 2px;
  right: 6px;
  font-size: 10px;
  color: #9ca3af;
}

.cm-col-h, .cm-row-h {
  background: #f8f9fc;
  font-weight: 600;
  color: #4b5563;
}

.cm-diag-cell {
  background: #eef2ff;
  color: #4338ca;
  font-weight: 600;
}

.cm-off-cell {
  background: #fff;
  color: #6b7280;
}

.cm-off-cell:empty {
  background: #fafafa;
}

.cm-col-sum, .cm-row-sum {
  background: #f0f2f8;
  font-weight: 600;
  color: #374151;
}

.cm-col-sum-row td {
  background: #f0f2f8;
  font-weight: 600;
  color: #374151;
}

.cm-table-wrap {
  overflow-x: auto;
  margin-bottom: 20px;
  border-radius: 8px;
  border: 1px solid #e8e8ec;
}

.table-scroll {
  max-height: 400px;
  overflow: auto;
}

h4 {
  font-size: 14px;
  font-weight: 500;
  color: #333;
  margin: 16px 0 8px;
}

/* ── Prompt overlay textarea + slash picker ──── */
.prompt-textarea-wrapper {
  position: relative;
  min-height: 80px;
}

.prompt-backdrop {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  margin: 0;
  padding: 8px 12px;
  font-family: inherit;
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-wrap: break-word;
  overflow: hidden;
  pointer-events: none;
  color: #4b4b60;
  background: #fff;
  border: 1px solid transparent;
  border-radius: var(--n-border-radius, 6px);
  box-sizing: border-box;
}

.prompt-textarea {
  position: relative;
  display: block;
  width: 100%;
  min-height: 80px;
  padding: 8px 12px;
  font-family: inherit;
  font-size: 13px;
  line-height: 1.6;
  color: transparent;
  caret-color: #4b4b60;
  background: transparent;
  border: 1px solid rgb(224, 224, 230);
  border-radius: var(--n-border-radius, 6px);
  resize: vertical;
  outline: none;
  z-index: 1;
  box-sizing: border-box;
}

.prompt-textarea:focus {
  border-color: #6366f1;
  box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2);
}

.prompt-textarea.is-composing {
  color: #4b4b60;
}

.prompt-textarea::placeholder {
  color: #c0c0c8;
}

.hint-slash {
  color: #8e8e9a;
}

.hint-slash code {
  background: rgba(99, 102, 241, 0.08);
  color: #6366f1;
  padding: 1px 5px;
  border-radius: 3px;
  font-size: 11px;
}

.slash-picker {
  position: absolute;
  left: 0;
  bottom: 100%;
  margin-bottom: 4px;
  max-height: 200px;
  overflow-y: auto;
  background: #fff;
  border: 1px solid #e0e0e6;
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
  padding: 4px;
  z-index: 10;
  min-width: 220px;
}

.slash-picker-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  color: #4b4b60;
}

.slash-picker-item:hover,
.slash-picker-item.active {
  background: rgba(99, 102, 241, 0.08);
  color: #6366f1;
}

.slash-picker-item code {
  color: #6366f1;
  font-size: 12px;
  background: rgba(99, 102, 241, 0.08);
  padding: 1px 5px;
  border-radius: 3px;
  flex-shrink: 0;
}

.slash-picker-empty {
  padding: 8px 10px;
  font-size: 12px;
  color: #9a9aa8;
}
</style>