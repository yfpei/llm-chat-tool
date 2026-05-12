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
            v-if="currentPreview.length"
            :columns="currentPreviewColumns"
            :data="currentPreview"
            :bordered="true"
            :single-line="false"
            size="small"
            :max-height="320"
            :scroll-x="600"
          />
          </div>
        </div>
      </div>

      <!-- Step 2: Filter -->
      <div class="step" v-if="uploadResult">
        <div class="step-title">2. 筛选条件</div>
        <div class="filter-section">
          <div class="filter-row">
            <label class="filter-label">前 N 行</label>
            <n-input-number v-model:value="filter.top_n" :min="0" :max="uploadResult.total_rows" placeholder="全部行" style="width: 160px" />
            <span class="filter-desc">{{ filter.top_n ? `仅处理前 ${filter.top_n} 行` : '处理全部行' }}</span>
            <n-button size="small" type="primary" secondary :loading="filterPreviewLoading" @click="applyFilterPreview" :disabled="!uploadResult">
              筛选预览
            </n-button>
          </div>

          <div v-if="filterPreviewResult" class="filter-preview-result" :class="{ 'filter-empty': filterPreviewResult.total_after === 0 }">
            <span v-if="filterPreviewResult.total_after > 0">
              筛选后匹配 <strong>{{ filterPreviewResult.total_after }}</strong> 行（共 {{ filterPreviewResult.total_before }} 行）
              <n-button size="tiny" type="primary" secondary :loading="filterDownloadLoading" @click="downloadFiltered" style="margin-left: 10px">
                下载筛选结果
              </n-button>
            </span>
            <span v-else class="filter-empty-text">
              筛选结果为空！请调整筛选条件
            </span>
          </div>

          <div class="filter-groups">
            <div v-for="(group, gi) in filter.groups" :key="gi" class="filter-group-card">
              <div class="filter-group-header">
                <span class="filter-group-title">条件组 {{ gi + 1 }}</span>
                <n-button v-if="filter.groups.length > 1" text size="tiny" type="error" @click="removeFilterGroup(gi)">删除组</n-button>
              </div>
              <div class="filter-row filter-header-row">
                <span class="filter-col-field">字段</span>
                <span class="filter-col-op">条件</span>
                <span class="filter-col-val">值</span>
                <span class="filter-col-del"></span>
              </div>
              <div v-for="(cond, ci) in group.conditions" :key="ci" class="filter-row">
                <n-select v-model:value="cond.field" :options="filterFieldOptions" placeholder="选择列" class="filter-col-field" />
                <n-select v-model:value="cond.operator" :options="operatorOptions" class="filter-col-op" />
                <n-input v-model:value="cond.value" placeholder="值" class="filter-col-val" :disabled="noValueOperators.includes(cond.operator)" />
                <n-button text size="tiny" type="error" @click="group.conditions.splice(ci, 1)" class="filter-col-del">✕</n-button>
              </div>
              <div class="filter-group-footer">
                <n-button text size="small" type="primary" @click="addFilterCondition(gi)" :disabled="!uploadResult?.columns.length">
                  + 添加条件
                </n-button>
                <n-radio-group v-if="group.conditions.length > 1" v-model:value="group.logic" size="small">
                  <n-radio value="and">AND</n-radio>
                  <n-radio value="or">OR</n-radio>
                </n-radio-group>
              </div>
            </div>
            <div v-if="filter.groups.filter(g => g.conditions.length > 0).length > 1" class="filter-group-logic">
              <label class="filter-label">组间逻辑</label>
              <n-radio-group v-model:value="filter.logic" size="small">
                <n-radio value="and">AND（全部满足）</n-radio>
                <n-radio value="or">OR（任一满足）</n-radio>
              </n-radio-group>
            </div>
            <n-button text size="small" @click="addFilterGroup">
              + 添加条件组
            </n-button>
          </div>

          <div class="filter-summary" v-if="hasAnyFilterCondition() || filter.top_n">
            <span v-if="hasAnyFilterCondition()">
              条件：{{ conditionSummary }}
            </span>
            <span v-if="filter.top_n"> · 前 {{ filter.top_n }} 行</span>
          </div>
        </div>
      </div>

      <!-- Step 3: Config -->
      <div class="step" v-if="uploadResult">
        <div class="step-title">3. 配置参数</div>
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
              <span class="hint-slash"> · 输入 <code>/</code> 快速选择</span>
            </span>
            <span class="hint" v-else>请先选择输入列</span>
          </label>
          <div class="prompt-textarea-wrapper" ref="promptTextareaRef">
            <pre class="prompt-backdrop" v-html="promptHighlighted" />
            <textarea
              ref="textareaRef"
              v-model="config.prompt"
              class="prompt-textarea"
              :class="{ 'is-composing': isComposing }"
              rows="15"
              placeholder="请根据以下内容回答：&#10;{{input}}"
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

      <!-- Step 4: Progress + Results -->
      <div class="step" v-if="progress.total > 0">
        <div class="step-title">4. 进度与结果</div>
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
          virtual-scroll
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
import { ref, reactive, computed, h, watch, nextTick } from 'vue'
import {
  NButton, NUpload, NSelect, NInput, NInputNumber,
  NDataTable, NProgress, NTag, NCheckbox, NRadioGroup, NRadio,
  useMessage,
} from 'naive-ui'
import { useChatStore } from '../stores/chat'
import { useBatchStore } from '../stores/batch'
import * as batchApi from '../api/batch'
import * as batchTasksApi from '../api/batchTasks'
import type { PreviewRow, FilterConfig, FilterCondition } from '../types'

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
const message = useMessage()
const uploading = ref(false)
const running = ref(false)
const done = ref(false)
const uploadError = ref('')
const batchError = ref('')
const results = ref<ResultRow[]>([])
const reuploadKey = ref(0)
const runningTaskId = ref<string | null>(null)
const progress = reactive({ completed: 0, total: 0 })
let abortController: AbortController | null = null
const runningResults = new Map<string, ResultRow[]>()

// Batch result updates to avoid re-rendering on every single row
let batchTimer: ReturnType<typeof setTimeout> | null = null
let pendingResults: ResultRow[] = []
const parsedKeysSet = ref<Set<string>>(new Set())

function flushResults() {
  if (pendingResults.length === 0) return
  results.value.push(...pendingResults)
  pendingResults = []
}

function addResult(entry: ResultRow) {
  if (entry.parsed) {
    for (const k of Object.keys(entry.parsed)) {
      parsedKeysSet.value.add(k)
    }
  }
  pendingResults.push(entry)

  if (!batchTimer) {
    batchTimer = setTimeout(() => {
      batchTimer = null
      flushResults()
    }, 80)
  }
}

function clearResults() {
  if (batchTimer) {
    clearTimeout(batchTimer)
    batchTimer = null
  }
  pendingResults = []
  results.value = []
  parsedKeysSet.value = new Set()
}

const uploadResult = computed(() => batchStore.uploadResult)
const filterPreviewLoading = ref(false)
const filterPreviewResult = ref<{ total_before: number; total_after: number; preview: any[]; columns: string[] } | null>(null)
const filterDownloadLoading = ref(false)

const currentPreview = computed(() => {
  if (filterPreviewResult.value) {
    return filterPreviewResult.value.preview
  }
  return uploadResult.value?.preview || []
})

const currentPreviewColumns = computed(() => {
  const cols = filterPreviewResult.value?.columns || uploadResult.value?.columns || []
  if (!cols.length) return []
  return [
    { title: '#', key: 'row', width: 50 },
    ...cols.map((c) => ({
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

const config = reactive({
  input_columns: [] as string[],
  api_key_id: null as number | null,
  concurrency: 3,
  output_column_name: 'AI结果',
  prompt: '',
  strip_thinking: false,
  parse_json: false,
})

const filter = reactive<FilterConfig>({
  top_n: null,
  groups: [{ logic: 'and', conditions: [] }],
  logic: 'and',
})

const noValueOperators = ['not_empty', 'is_empty']

const operatorOptions = [
  { label: '等于', value: 'equals' },
  { label: '包含', value: 'contains' },
  { label: '大于', value: 'gt' },
  { label: '小于', value: 'lt' },
  { label: '大于等于', value: 'gte' },
  { label: '小于等于', value: 'lte' },
  { label: '不为空', value: 'not_empty' },
  { label: '为空', value: 'is_empty' },
]

const operatorLabels: Record<string, string> = {
  contains: '包含',
  equals: '=',
  gt: '>',
  lt: '<',
  gte: '>=',
  lte: '<=',
  not_empty: '不为空',
  is_empty: '为空',
}

function condLabel(c: FilterCondition) {
  if (noValueOperators.includes(c.operator)) {
    return `${c.field || '--'} ${operatorLabels[c.operator] || c.operator}`
  }
  return `${c.field || '--'} ${operatorLabels[c.operator] || c.operator} "${c.value}"`
}

const conditionSummary = computed(() => {
  const groups = filter.groups.filter((g) => g.conditions.length > 0)
  if (groups.length === 0) return ''
  const parts = groups.map((g) => {
    if (g.conditions.length === 1) return condLabel(g.conditions[0])
    return '(' + g.conditions.map(condLabel).join(` ${g.logic.toUpperCase()} `) + ')'
  })
  if (parts.length === 1) return parts[0]
  return parts.join(` ${filter.logic.toUpperCase()} `)
})

const filterFieldOptions = computed(() =>
  (uploadResult.value?.columns || []).map((c) => ({ label: c, value: c })),
)

function addFilterCondition(groupIdx: number) {
  filter.groups[groupIdx].conditions.push({
    field: uploadResult.value?.columns[0] || '',
    operator: 'contains',
    value: '',
  })
}

function addFilterGroup() {
  filter.groups.push({ logic: 'and', conditions: [] })
}

function removeFilterGroup(idx: number) {
  filter.groups.splice(idx, 1)
  if (filter.groups.length === 0) {
    filter.groups.push({ logic: 'and', conditions: [] })
  }
}

function resetConfig() {
  config.input_columns = []
  config.api_key_id = null
  config.concurrency = 3
  config.output_column_name = 'AI结果'
  config.prompt = ''
  config.strip_thinking = false
  config.parse_json = false
}

function resetFilter() {
  filter.top_n = null
  filter.groups = [{ logic: 'and', conditions: [] }]
  filter.logic = 'and'
  filterPreviewResult.value = null
}

function hasAnyFilterCondition() {
  return filter.groups.some((g) => g.conditions.some((c) => c.field && (c.value || noValueOperators.includes(c.operator))))
}

async function applyFilterPreview() {
  if (!batchStore.currentTask) return
  filterPreviewLoading.value = true
  try {
    const payload = { ...filter }
    const result = await batchApi.filterPreview(batchStore.currentTask.id, payload)
    filterPreviewResult.value = result
  } catch (e: any) {
    message.warning(e.message || '筛选预览失败')
  } finally {
    filterPreviewLoading.value = false
  }
}

async function downloadFiltered() {
  if (!batchStore.currentTask || !uploadResult.value) return
  filterDownloadLoading.value = true
  try {
    const name = uploadResult.value.filename.replace(/\.(xlsx|xls|json|txt)$/i, '')
    await batchApi.filterDownload(batchStore.currentTask.id, { ...filter }, `${name}_筛选结果.xlsx`)
    message.success('下载完成')
  } catch (e: any) {
    message.warning(e.message || '下载失败')
  } finally {
    filterDownloadLoading.value = false
  }
}

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
// Overlay backdrop: renders the prompt with highlighted {{var}} references.
// The textarea has transparent text; this backdrop shows through it.
const promptHighlighted = computed(() => {
  const text = config.prompt
  if (!text) return ''
  const cols = new Set(config.input_columns)
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

const canStart = computed(
  () => config.input_columns.length > 0 && config.api_key_id && config.prompt.trim(),
)

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
  if (!q) return config.input_columns
  return config.input_columns.filter((c) => c.toLowerCase().includes(q))
})

function onPromptFocus() {
  // Re-check slash state on focus in case the text changed externally
  detectSlash()
}

function onPromptInput() {
  detectSlash()
}

function detectSlash() {
  const ta = textareaRef.value
  if (!ta) return
  const cursorPos = ta.selectionStart
  const textBefore = config.prompt.slice(0, cursorPos)

  const slashIdx = textBefore.lastIndexOf('/')
  if (slashIdx !== -1 && config.input_columns.length > 0) {
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

function selectSlashColumn(col: string) {
  if (slashStartPos.value === -1) return
  const before = config.prompt.slice(0, slashStartPos.value)
  const after = config.prompt.slice(slashStartPos.value + 1 + slashQuery.value.length)
  config.prompt = before + '{{' + col + '}}' + after
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

function onPromptScroll(e: Event) {
  const ta = e.target as HTMLTextAreaElement
  const backdrop = promptTextareaRef.value?.querySelector('.prompt-backdrop') as HTMLElement | null
  if (backdrop) {
    backdrop.scrollTop = ta.scrollTop
    backdrop.scrollLeft = ta.scrollLeft
  }
}

const resultColumns = computed(() => {
  const parsedKeys: string[] = config.parse_json ? [...parsedKeysSet.value] : []

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

// Auto-save config + filter when changed (debounced 800ms)
let autoSaveTimer: ReturnType<typeof setTimeout> | null = null
watch([() => ({ ...config }), () => ({ ...filter })], () => {
  if (!batchStore.currentTask || !uploadResult.value) return
  if (autoSaveTimer) clearTimeout(autoSaveTimer)
  autoSaveTimer = setTimeout(() => {
    batchStore.saveBatchTaskConfig(batchStore.currentTask!.id, {
      ...config,
      filter: { ...filter },
    })
  }, 800)
}, { deep: true })

// Load saved config when a task is selected from sidebar
watch(() => batchStore.currentTask, (task) => {
  if (!task) {
    done.value = false
    running.value = false
    clearResults()
    progress.completed = 0
    progress.total = 0
    batchError.value = ''
    resetConfig()
    resetFilter()
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
      if (saved.filter) {
        resetFilter()
        filter.top_n = saved.filter.top_n ?? null
        filter.logic = saved.filter.logic || 'and'
        // Restore groups (new format) or convert old conditions+connector format
        if (saved.filter.groups && saved.filter.groups.length > 0) {
          filter.groups = saved.filter.groups
        } else if (saved.filter.conditions && saved.filter.conditions.length > 0) {
          // Convert old per-condition-connector format to groups
          const groups: typeof filter.groups = []
          let current: typeof filter.groups[0] = { logic: 'and', conditions: [] }
          for (let i = 0; i < saved.filter.conditions.length; i++) {
            const c = saved.filter.conditions[i]
            current.conditions.push({ field: c.field, operator: c.operator, value: c.value })
            if (c.connector === 'or' && i < saved.filter.conditions.length - 1) {
              groups.push(current)
              current = { logic: 'and', conditions: [] }
            }
          }
          groups.push(current)
          filter.groups = groups
          filter.logic = 'or'
        }
        if (hasAnyFilterCondition() || filter.top_n) {
          batchApi.filterPreview(task.id, { ...filter }).then((r) => {
            filterPreviewResult.value = r
          }).catch(() => {})
        }
      } else {
        resetFilter()
      }
    } catch { /* ignore parse errors */ }
  } else {
    resetConfig()
    resetFilter()
  }
  if (task.status === 'running') {
    if (runningTaskId.value === task.id) {
      // Returning to the currently running task — restore state
      running.value = true
      done.value = false
      const saved = runningResults.get(task.id)
      if (saved) {
        clearResults()
        results.value = [...saved]
        // Rebuild parsedKeysSet from restored results
        const keys = new Set<string>()
        for (const r of saved) {
          if (r.parsed) {
            for (const k of Object.keys(r.parsed)) {
              keys.add(k)
            }
          }
        }
        parsedKeysSet.value = keys
      }
      progress.completed = task.progress_completed
      progress.total = task.progress_total
    } else {
      // A different task that happens to be running (e.g. from another client)
      running.value = false
      done.value = false
      clearResults()
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
    clearResults()
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
    filterPreviewResult.value = null
    // Reset progress and results for the new file
    done.value = false
    clearResults()
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
    filterPreviewResult.value = null
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

  // 有筛选条件时，自动检查筛选结果
  const hasFilter = filter.top_n || hasAnyFilterCondition()
  if (hasFilter) {
    try {
      filterPreviewResult.value = await batchApi.filterPreview(batchStore.currentTask.id, { ...filter })
    } catch { /* 预览失败不阻止，让后端兜底 */ }
    if (filterPreviewResult.value && filterPreviewResult.value.total_after === 0) {
      message.warning('筛选结果为空，请调整筛选条件后再执行')
      return
    }
  }

  clearResults()
  progress.completed = 0
  progress.total = 0
  done.value = false
  batchError.value = ''
  running.value = true
  runningTaskId.value = batchStore.currentTask!.id

  await batchStore.saveBatchTaskConfig(batchStore.currentTask.id, {
    ...config,
    filter: { ...filter },
  })

  // Track results per running task for restoration when switching back
  const taskResults: ResultRow[] = []
  runningResults.set(batchStore.currentTask.id, taskResults)

  abortController = batchApi.runBatch(
    {
      ...config,
      api_key_id: config.api_key_id,
      file_id: uploadResult.value!.file_id,
      task_id: batchStore.currentTask.id,
      filter: hasAnyFilterCondition() || filter.top_n ? { ...filter } : undefined,
    },
    (completed, total) => {
      if (batchStore.currentTask?.id === runningTaskId.value) {
        progress.completed = completed
        progress.total = total
      }
    },
    (row, input, output, parsed) => {
      const entry = { row, input, output, status: 'success' as const, parsed }
      taskResults.push(entry)
      if (batchStore.currentTask?.id === runningTaskId.value) {
        addResult(entry)
      }
    },
    (row, input, error) => {
      const entry = { row, input, output: '', status: 'error' as const, error }
      taskResults.push(entry)
      if (batchStore.currentTask?.id === runningTaskId.value) {
        addResult(entry)
      }
    },
    () => {
      const wasMyTask = batchStore.currentTask?.id === runningTaskId.value
      // Flush any remaining buffered results
      flushResults()
      runningResults.delete(runningTaskId.value!)
      runningTaskId.value = null
      if (wasMyTask) {
        done.value = true
        running.value = false
      }
    },
    (msg) => {
      flushResults()
      runningResults.delete(runningTaskId.value!)
      batchError.value = msg
      running.value = false
    },
  )
}

function stopBatch() {
  if (abortController) {
    abortController.abort()
    abortController = null
    flushResults()
    runningResults.delete(runningTaskId.value!)
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

.filter-section {
  background: #fff;
  border-radius: 10px;
  border: 1px solid #e5e5ea;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.filter-label {
  font-size: 13px;
  font-weight: 500;
  color: #4b4b60;
  min-width: 70px;
  flex-shrink: 0;
}

.filter-desc {
  font-size: 12px;
  color: #9a9aa8;
}

.filter-groups {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.filter-group-card {
  background: #f8f8fa;
  border: 1px solid #eeeef2;
  border-radius: 8px;
  padding: 10px 12px 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.filter-group-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.filter-group-title {
  font-size: 12px;
  font-weight: 600;
  color: #8e8e9a;
}

.filter-group-logic {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 4px 0;
}

.filter-group-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 2px;
}

.filter-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.filter-header-row {
  font-size: 12px;
  font-weight: 600;
  color: #8e8e9a;
  padding-bottom: 2px;
}

.filter-col-field {
  width: 140px;
  flex-shrink: 0;
}

.filter-col-op {
  width: 100px;
  flex-shrink: 0;
}

.filter-col-val {
  flex: 1;
  min-width: 120px;
}

.filter-col-conn {
  width: 72px;
  flex-shrink: 0;
}

.filter-col-del {
  flex-shrink: 0;
}

.filter-summary {
  font-size: 12px;
  color: #6366f1;
  background: rgba(99, 102, 241, 0.06);
  padding: 6px 10px;
  border-radius: 6px;
}

.filter-preview-result {
  font-size: 13px;
  color: #2e7d32;
  background: rgba(46, 125, 50, 0.06);
  padding: 8px 12px;
  border-radius: 6px;
  border: 1px solid rgba(46, 125, 50, 0.15);
}

.filter-preview-result.filter-empty {
  color: #c62828;
  background: rgba(198, 40, 40, 0.06);
  border-color: rgba(198, 40, 40, 0.2);
}

.filter-empty-text {
  font-weight: 500;
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

/* Show real text during IME composition (拼音输入) */
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

.batch-error {
  margin-top: 12px;
  color: #ef4444;
  font-size: 13px;
}
</style>
