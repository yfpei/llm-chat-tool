<template>
  <div class="eval-panel">
    <div class="step-title">5. 评测</div>

    <!-- Only show if done OR this is standalone (no batch dependency) -->
    <div v-if="!hasResultFile && !classResult && !llmScoringDone">
      <p class="eval-hint">跑批完成后可进行评测</p>
    </div>

    <!-- Tab switcher -->
    <div class="eval-tabs" v-if="showTabs">
      <div
        v-for="tab in tabs"
        :key="tab.key"
        :class="['eval-tab', { active: activeTab === tab.key }]"
        @click="activeTab = tab.key"
      >{{ tab.label }}</div>
    </div>

    <!-- Classification Tab -->
    <div v-if="activeTab === 'classification'" class="eval-tab-content">
      <!-- Config -->
      <div v-if="!classResult" class="eval-config">
        <div class="eval-config-grid">
          <div class="eval-config-item">
            <label>标签列（答案）</label>
            <n-select v-model:value="classConfig.label_column" :options="columnOptions" placeholder="选择标签列" />
          </div>
          <div class="eval-config-item">
            <label>模型结果列</label>
            <n-auto-complete v-model:value="classConfig.predict_column" :options="columnOptions" placeholder="输入或选择结果列" />
          </div>
        </div>

        <div class="mapping-section">
          <div class="mapping-header">
            <label>值映射（模型输出 ��� 标签值）</label>
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
      <div v-if="!llmScoringDone" class="eval-config">
        <div class="eval-config-grid">
          <div class="eval-config-item">
            <label>评分模型（独立选择）</label>
            <n-select v-model:value="llmConfig.api_key_id" :options="keyOptions" placeholder="选择模型" />
          </div>
          <div class="eval-config-item">
            <label>评分列</label>
            <n-auto-complete v-model:value="llmConfig.score_column" :options="columnOptions" placeholder="输入或选择要评分的列" />
          </div>
        </div>
        <div class="eval-config-grid">
          <div class="eval-config-item">
            <label>输出列名</label>
            <n-input v-model:value="llmConfig.output_column_name" placeholder="评分" />
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
            tag
            placeholder="选择或输入列名"
          />
        </div>
        <div class="eval-prompt">
          <label>
            评分 Prompt
            <span class="hint" v-if="llmConfig.input_columns.length">
              可用变量：
              <code v-for="c in llmConfig.input_columns" :key="c" class="var-tag">{{ varLabel(c) }}</code>
            </span>
          </label>
          <n-input v-model:value="llmConfig.prompt" type="textarea" :rows="8" placeholder="请根据以下标准对回答进行评分..." />
        </div>
        <n-button type="primary" :loading="llmRunning" @click="runLLMScoring" :disabled="!llmConfig.api_key_id || !llmConfig.score_column || !llmConfig.prompt.trim()">
          {{ llmRunning ? '评分中...' : '开始主观评测' }}
        </n-button>
        <p v-if="llmError" class="eval-error">{{ llmError }}</p>
      </div>

      <!-- Progress -->
      <div v-if="llmRunning || llmScoringDone">
        <n-progress
          type="line"
          :percentage="llmProgress.total > 0 ? Math.round((llmProgress.completed / llmProgress.total) * 100) : 0"
          :indicator-text="`${llmProgress.completed} / ${llmProgress.total}`"
          :height="24"
        />
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
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, h, watch } from 'vue'
import {
  NButton, NSelect, NInput, NInputNumber, NDataTable, NProgress, NTag,
  NAutoComplete, useMessage,
} from 'naive-ui'
import { useChatStore } from '../stores/chat'
import * as evalApi from '../api/eval'
import { authFetch } from '../api/client'
import type {
  ClassificationEvalConfig,
  ClassificationEvalResult,
  LLMScoringEvalConfig,
  MappingRule,
} from '../types'

interface LLMScoreRow {
  row: number
  score: string
  status: 'success' | 'error'
  error?: string
}

const props = defineProps<{
  taskId: string
  columns: string[]
  fileId: string
  standalone?: boolean
  savedEvalConfig?: string | null
}>()

const emit = defineEmits<{
  (e: 'eval-config-saved', config: Record<string, any>): void
}>()

const store = useChatStore()
const message = useMessage()

const activeTab = ref<'classification' | 'llm_scoring'>('classification')
const showTabs = ref(true)

const tabs = [
  { key: 'classification' as const, label: '客观评测' },
  { key: 'llm_scoring' as const, label: '主观评测' },
]

const columnOptions = computed(() => props.columns.map((c) => ({ label: c, value: c })))
const keyOptions = computed(() =>
  store.apiKeys
    .filter((k) => k.is_valid || k.is_active)
    .map((k) => ({ label: `${k.name} (${k.model})`, value: k.id })),
)

// ── Classification state ──
const classRunning = ref(false)
const classError = ref('')
const classResult = ref<ClassificationEvalResult | null>(null)
const classConfig = reactive<ClassificationEvalConfig>({
  label_column: '',
  predict_column: '',
  mappings: [],
})

// ── LLM scoring state ──
const llmRunning = ref(false)
const llmError = ref('')
const llmScoringDone = ref(false)
const llmAvgScore = ref(0)
const llmScores = ref<LLMScoreRow[]>([])
const llmProgress = reactive({ completed: 0, total: 0 })
const llmConfig = reactive<LLMScoringEvalConfig>({
  api_key_id: 0,
  prompt: '',
  input_columns: [],
  score_column: '',
  output_column_name: '评分',
  concurrency: 3,
})
let llmAbortController: AbortController | null = null

const hasResultFile = ref(false)

// ── Methods ──

function varLabel(col: string) {
  return '{{' + col + '}}'
}

function addMapping() {
  classConfig.mappings.push({ model_output: '', label_value: '' })
}

async function runClassification() {
  classRunning.value = true
  classError.value = ''
  try {
    classResult.value = await evalApi.runClassificationEval(props.taskId, classConfig)
    message.success('客观评测完成')
  } catch (e: any) {
    classError.value = e.message || '评测失败'
  } finally {
    classRunning.value = false
  }
}

function runLLMScoring() {
  llmError.value = ''
  llmRunning.value = true
  llmScoringDone.value = false
  llmScores.value = []
  llmProgress.completed = 0
  llmProgress.total = 0
  llmAvgScore.value = 0

  llmAbortController = evalApi.runLLMScoringEval(
    props.taskId,
    { ...llmConfig },
    (completed, total) => {
      llmProgress.completed = completed
      llmProgress.total = total
    },
    (row, score) => {
      llmScores.value.push({ row, score, status: 'success' })
    },
    (row, error) => {
      llmScores.value.push({ row, score: '', status: 'error', error })
    },
    (total, avgScore) => {
      llmRunning.value = false
      llmScoringDone.value = true
      llmAvgScore.value = avgScore
    },
    (msg) => {
      llmError.value = msg
      llmRunning.value = false
    },
  )
}

function resetLLMScoring() {
  llmScoringDone.value = false
  llmScores.value = []
  llmProgress.completed = 0
  llmProgress.total = 0
  llmAvgScore.value = 0
}

async function downloadClassification() {
  const url = evalApi.classificationDownloadUrl(props.taskId)
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

async function downloadLLMScoring() {
  const url = evalApi.llmScoringDownloadUrl(props.taskId)
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

let autoRunDone = false

// ── Load saved eval config ──
watch(() => props.savedEvalConfig, (json) => {
  if (!json || autoRunDone) return
  try {
    const cfg = JSON.parse(json)
    if (cfg.enabled) {
      if (cfg.classification && cfg.classification.label_column) {
        classConfig.label_column = cfg.classification.label_column || ''
        classConfig.predict_column = cfg.classification.predict_column || ''
        classConfig.mappings = cfg.classification.mappings || []
      }
      if (cfg.llm_scoring && cfg.llm_scoring.api_key_id) {
        llmConfig.api_key_id = cfg.llm_scoring.api_key_id || 0
        llmConfig.prompt = cfg.llm_scoring.prompt || ''
        llmConfig.input_columns = cfg.llm_scoring.input_columns || []
        llmConfig.score_column = cfg.llm_scoring.score_column || ''
        llmConfig.output_column_name = cfg.llm_scoring.output_column_name || '评分'
        llmConfig.concurrency = cfg.llm_scoring.concurrency || 3
      }
      if (cfg.method) {
        if (cfg.method === 'both') activeTab.value = 'classification'
        else activeTab.value = cfg.method
      }

      // Auto-run if embedded (not standalone) and has valid config
      if (!props.standalone) {
        autoRunDone = true
        const runAuto = async () => {
          if (cfg.classification && cfg.classification.label_column && cfg.classification.predict_column) {
            await runClassification()
          }
          if (cfg.llm_scoring && cfg.llm_scoring.api_key_id && cfg.llm_scoring.score_column) {
            activeTab.value = 'llm_scoring'
            runLLMScoring()
          }
        }
        runAuto()
      }
    }
  } catch { /* ignore */ }
}, { immediate: true })

// ── Reset state on taskId change ──
watch(() => props.taskId, async (tid) => {
  // Reset all state when switching tasks
  classResult.value = null
  classError.value = ''
  classRunning.value = false
  llmScores.value = []
  llmScoringDone.value = false
  llmRunning.value = false
  llmError.value = ''
  llmAvgScore.value = 0
  llmProgress.completed = 0
  llmProgress.total = 0
  hasResultFile.value = false

  if (!tid) return
  const has = await evalApi.checkClassificationResult(tid)
  hasResultFile.value = has
}, { immediate: true })
</script>

<style scoped>
.eval-panel {
  padding-bottom: 16px;
}

.step-title {
  font-size: 16px;
  font-weight: 600;
  color: #4b4b60;
  margin-bottom: 12px;
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
  padding: 6px 14px;
  background: #f0f0f4;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  transition: background 0.2s;
}

.eval-tab.active {
  background: #6366f1;
  color: #fff;
}

.eval-tab-content {
  /* spacing handled by children */
}

.eval-config {
  border: 1px solid #e0e0e6;
  border-radius: 8px;
  padding: 16px;
}

.eval-config-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 12px;
}

.eval-config-item label {
  display: block;
  font-size: 12px;
  color: #666;
  margin-bottom: 4px;
}

.mapping-section {
  margin-bottom: 12px;
}

.mapping-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.mapping-header label {
  font-size: 12px;
  color: #666;
}

.mapping-table {
  border: 1px solid #e0e0e6;
  border-radius: 6px;
  overflow: hidden;
  margin-bottom: 4px;
}

.mapping-row {
  display: grid;
  grid-template-columns: 1fr 1fr 36px;
  gap: 8px;
  padding: 4px 8px;
  align-items: center;
}

.mapping-row.head {
  background: #f8f8fa;
  font-size: 11px;
  color: #666;
  padding: 6px 8px;
}

.eval-prompt {
  margin-bottom: 12px;
}

.eval-prompt label {
  display: block;
  font-size: 12px;
  color: #666;
  margin-bottom: 4px;
}

.eval-prompt label code {
  font-size: 11px;
  color: #6366f1;
  background: rgba(99, 102, 241, 0.08);
  padding: 1px 4px;
  border-radius: 3px;
}

.eval-prompt label .hint {
  font-size: 11px;
  color: #8e8e9a;
  margin-left: 4px;
}

.var-tag {
  font-size: 11px;
  color: #6366f1;
  background: rgba(99, 102, 241, 0.08);
  padding: 1px 5px;
  border-radius: 3px;
  margin-right: 4px;
}

.eval-error {
  margin-top: 8px;
  color: #ef4444;
  font-size: 13px;
}

.eval-summary {
  display: flex;
  gap: 12px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}

.eval-summary-item {
  padding: 8px 14px;
  background: #f0f4ff;
  border-radius: 6px;
  border-left: 3px solid #6366f1;
}

.eval-summary-item:nth-child(2) {
  background: #f4fcf0;
  border-left-color: #22c55e;
}

.eval-summary-item:nth-child(3) {
  background: #fff8f0;
  border-left-color: #f59e0b;
}

.eval-summary-label {
  display: block;
  font-size: 11px;
  color: #666;
}

.eval-summary-value {
  font-size: 18px;
  font-weight: 700;
  color: #6366f1;
}

.eval-summary-item:nth-child(2) .eval-summary-value {
  color: #22c55e;
}

.eval-summary-item:nth-child(3) .eval-summary-value {
  color: #f59e0b;
}

h4 {
  font-size: 14px;
  margin: 0 0 8px 0;
  color: #4b4b60;
}

/* Confusion Matrix */
.cm-table-wrap {
  border: 1px solid #e0e0e6;
  border-radius: 6px;
  overflow: hidden;
  margin-bottom: 14px;
}

.cm-table {
  width: auto;
  min-width: 200px;
  border-collapse: collapse;
  font-size: 13px;
}

.cm-table th, .cm-table td {
  padding: 8px 12px;
  text-align: center;
  border-bottom: 1px solid #f0f0f4;
}

.cm-corner {
  border-bottom: 2px solid #d0d0d6 !important;
  border-right: 2px solid #d0d0d6 !important;
  width: 60px;
}

.cm-diag {
  position: relative;
  height: 32px;
}

.cm-actual {
  position: absolute;
  bottom: 0;
  left: 0;
  font-size: 10px;
  color: #666;
}

.cm-predict {
  position: absolute;
  top: 0;
  right: 0;
  font-size: 10px;
  color: #6366f1;
}

.cm-col-h {
  border-bottom: 2px solid #d0d0d6 !important;
  font-size: 12px;
  background: #f8f8fa;
}

.cm-col-sum {
  border-bottom: 2px solid #d0d0d6 !important;
  border-left: 2px solid #d0d0d6 !important;
  font-size: 11px;
  color: #666;
}

.cm-row-h {
  border-right: 2px solid #d0d0d6 !important;
  font-size: 12px;
  background: #fafafc;
  text-align: left !important;
}

.cm-diag-cell {
  font-weight: 700;
  color: #22c55e;
  background: #f6fff0;
}

.cm-off-cell {
  color: #ef4444;
}

.cm-row-sum {
  border-left: 2px solid #d0d0d6 !important;
  font-weight: 600;
  background: #fafafc;
}

.cm-col-sum-row {
  background: #f8f8fa;
  border-top: 2px solid #d0d0d6;
}

.cm-col-sum-row td {
  font-weight: 600;
}

.eval-actions {
  margin-top: 14px;
}

.table-scroll {
  max-height: 400px;
  overflow-y: auto;
  margin: 12px 0;
}
</style>
