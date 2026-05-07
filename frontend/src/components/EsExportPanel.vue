<template>
  <div class="es-panel">
    <div class="es-header">
      <h2>ES 数据导出</h2>
    </div>

    <div class="es-body">
      <!-- Step 1: Connection -->
      <div class="step">
        <div class="step-title">1. ES 连接</div>
        <div class="conn-section" v-if="!connected">
          <div class="conn-grid">
            <div class="conn-item conn-full">
              <label>Host</label>
              <n-input v-model:value="conn.host" placeholder="http://localhost:9200" />
            </div>
            <div class="conn-item">
              <label>用户名</label>
              <n-input v-model:value="conn.username" placeholder="可选" />
            </div>
            <div class="conn-item">
              <label>密码</label>
              <n-input v-model:value="conn.password" type="password" show-password-on="click" placeholder="可选" />
            </div>
          </div>
          <n-button type="primary" :loading="testing" @click="handleTestConnection" :disabled="!conn.host.trim()">
            测试连接
          </n-button>
          <p v-if="connError" class="conn-error">{{ connError }}</p>
        </div>
        <div v-else class="conn-info">
          <div class="conn-tag">
            <span class="conn-host">{{ conn.host }}</span>
            <span class="conn-version">ES {{ esVersion }}</span>
            <n-button size="tiny" type="primary" secondary @click="disconnect">断开</n-button>
          </div>
        </div>
      </div>

      <!-- Step 2: Index & Fields -->
      <div class="step" v-if="connected">
        <div class="step-title">2. 索引与字段</div>
        <div class="index-section">
          <div class="index-row">
            <label>索引</label>
            <n-select
              v-model:value="selectedIndex"
              :options="indexOptions"
              placeholder="选择索引"
              filterable
              :loading="loadingIndices"
              @update:value="handleIndexChange"
              style="flex: 1"
            />
          </div>
          <div v-if="fieldList.length > 0" class="field-section">
            <div class="field-header">
              <label>导出字段</label>
              <div class="field-actions">
                <n-button text size="tiny" type="primary" @click="selectAllFields">全选</n-button>
                <n-button text size="tiny" @click="deselectAllFields">清空</n-button>
              </div>
            </div>
            <div class="field-list">
              <n-checkbox
                v-for="f in fieldList"
                :key="f"
                :checked="selectedFields.includes(f)"
                @update:checked="(v: boolean) => toggleField(f, v)"
              >
                <span class="field-name">{{ f }}</span>
                <span class="field-type">{{ fieldMapping[f] }}</span>
              </n-checkbox>
            </div>
          </div>
        </div>
      </div>

      <!-- Step 3: Query -->
      <div class="step" v-if="connected && selectedIndex">
        <div class="step-title">3. 查询条件</div>
        <div class="query-section">
          <n-radio-group v-model:value="queryMode" size="small">
            <n-radio value="simple">简单模式</n-radio>
            <n-radio value="advanced">高级模式</n-radio>
          </n-radio-group>

          <!-- Simple mode -->
          <div v-if="queryMode === 'simple'" class="query-simple">
            <div v-for="(group, gi) in queryGroups" :key="gi" class="filter-group-card">
              <div class="filter-group-header">
                <span class="filter-group-title">条件组 {{ gi + 1 }}</span>
                <n-button v-if="queryGroups.length > 1" text size="tiny" type="error" @click="queryGroups.splice(gi, 1)">删除组</n-button>
              </div>
              <div class="filter-row filter-header-row">
                <span class="filter-col-field">字段</span>
                <span class="filter-col-op">条件</span>
                <span class="filter-col-val">值</span>
                <span class="filter-col-del"></span>
              </div>
              <div v-for="(cond, ci) in group.conditions" :key="ci" class="filter-row">
                <n-select v-model:value="cond.field" :options="fieldSelectOptions" placeholder="选择字段" class="filter-col-field" filterable />
                <n-select v-model:value="cond.operator" :options="esOperatorOptions" class="filter-col-op" />
                <n-input v-model:value="cond.value" placeholder="值" class="filter-col-val" :disabled="noValueOperators.includes(cond.operator)" />
                <n-button text size="tiny" type="error" @click="group.conditions.splice(ci, 1)" class="filter-col-del">✕</n-button>
              </div>
              <div class="filter-group-footer">
                <n-button text size="small" type="primary" @click="addQueryCondition(gi)">+ 添加条件</n-button>
                <n-radio-group v-if="group.conditions.length > 1" v-model:value="group.logic" size="small">
                  <n-radio value="and">AND</n-radio>
                  <n-radio value="or">OR</n-radio>
                </n-radio-group>
              </div>
            </div>
            <div v-if="queryGroups.filter(g => g.conditions.length > 0).length > 1" class="filter-group-logic">
              <label class="filter-label">组间逻辑</label>
              <n-radio-group v-model:value="groupLogic" size="small">
                <n-radio value="and">AND</n-radio>
                <n-radio value="or">OR</n-radio>
              </n-radio-group>
            </div>
            <n-button text size="small" @click="addQueryGroup">+ 添加条件组</n-button>
          </div>

          <!-- Advanced mode -->
          <div v-if="queryMode === 'advanced'" class="query-advanced">
            <textarea
              v-model="advancedQuery"
              class="query-textarea"
              rows="8"
              placeholder='{"match_all": {}}'
            />
          </div>

          <div class="query-options">
            <div class="query-option-item">
              <label class="query-option-label">最大记录数</label>
              <n-input-number v-model:value="maxRecords" :min="0" :max="100000" placeholder="不限制" style="width: 160px" />
            </div>
          </div>

          <p v-if="!hasConditions" class="inline-warning">
            未设置查询条件，将匹配索引中的全部数据
          </p>

          <n-button
            type="primary"
            secondary
            :loading="previewLoading"
            @click="handlePreview"
            :disabled="!selectedIndex"
          >
            查询预览
          </n-button>
        </div>
      </div>

      <!-- Step 4: Preview -->
      <div class="step" v-if="previewData.rows.length > 0">
        <div class="step-title">4. 数据预览</div>
        <div class="preview-info">
          匹配 <strong>{{ previewData.total }}</strong> 条记录
        </div>
        <div class="table-scroll">
          <n-data-table
            :columns="previewColumns"
            :data="previewData.rows"
            :bordered="true"
            :single-line="false"
            size="small"
            :max-height="360"
            :scroll-x="800"
          />
        </div>
      </div>

      <!-- Step 5: Download -->
      <div class="step" v-if="previewData.total > 0">
        <div class="step-title">5. 下载</div>
        <n-button
          type="primary"
          size="large"
          :loading="downloading"
          :disabled="downloading"
          @click="handleDownload"
        >
          {{ downloading && downloadProgress.total > 0 ? `导出中 ${Math.round((downloadProgress.completed / downloadProgress.total) * 100)}%` : '下载 Excel' }}
        </n-button>
        <n-button v-if="downloading" @click="stopDownload" style="margin-left: 10px">停止</n-button>

        <div v-if="downloadProgress.total > 0" class="export-progress">
          <n-progress
            type="line"
            :percentage="Math.round((downloadProgress.completed / downloadProgress.total) * 100)"
            :indicator-text="`${downloadProgress.completed} / ${downloadProgress.total}`"
            :height="24"
          />
        </div>
        <p v-if="downloadError" class="export-error">{{ downloadError }}</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue'
import {
  NButton, NInput, NInputNumber, NSelect, NDataTable, NProgress, NCheckbox,
  NRadioGroup, NRadio, useMessage,
} from 'naive-ui'
import { useEsExportStore } from '../stores/esExport'
import * as esExportApi from '../api/esExport'

const store = useEsExportStore()
const message = useMessage()

// ── Connection ──────────────────────────────
const conn = reactive({ host: '', username: '', password: '' })
const connected = ref(false)
const testing = ref(false)
const connError = ref('')
const esVersion = ref('')

// ── Index & Fields ──────────────────────────
const selectedIndex = ref<string | null>(null)
const indices = ref<string[]>([])
const loadingIndices = ref(false)
const fieldMapping = ref<Record<string, string>>({})
const selectedFields = ref<string[]>([])

// ── Query ───────────────────────────────────
const queryMode = ref<'simple' | 'advanced'>('simple')

interface QueryCondition {
  field: string
  operator: string
  value: string
}
interface QueryGroup {
  logic: 'and' | 'or'
  conditions: QueryCondition[]
}

const queryGroups = ref<QueryGroup[]>([{ logic: 'and', conditions: [] }])
const groupLogic = ref<'and' | 'or'>('and')
const advancedQuery = ref('{"match_all": {}}')
const maxRecords = ref<number | null>(10000)

const hasConditions = computed(() =>
  queryMode.value === 'advanced'
    ? advancedQuery.value.trim() && advancedQuery.value.trim() !== '{"match_all": {}}'
    : queryGroups.value.some((g) => g.conditions.some((c) => c.field && (c.value || noValueOperators.includes(c.operator)))),
)

// ── Preview ─────────────────────────────────
const previewLoading = ref(false)
const previewData = reactive({ total: 0, rows: [] as Record<string, unknown>[], fields: [] as string[] })

// ── Download ─────────────────────────────────
const downloading = ref(false)
const downloadError = ref('')
const downloadProgress = reactive({ completed: 0, total: 0 })
let abortController: AbortController | null = null

// ── Computed ────────────────────────────────
const indexOptions = computed(() => indices.value.map((i) => ({ label: i, value: i })))
const fieldList = computed(() => Object.keys(fieldMapping.value))

const fieldSelectOptions = computed(() =>
  fieldList.value.map((f) => ({ label: `${f} (${fieldMapping.value[f]})`, value: f })),
)

const noValueOperators = ['not_empty', 'is_empty']

const esOperatorOptions = [
  { label: '等于', value: 'eq' },
  { label: '包含', value: 'contains' },
  { label: '大于', value: 'gt' },
  { label: '小于', value: 'lt' },
  { label: '大于等于', value: 'gte' },
  { label: '小于等于', value: 'lte' },
  { label: '不为空', value: 'not_empty' },
  { label: '为空', value: 'is_empty' },
]

const previewColumns = computed(() => {
  const cols = previewData.fields.length > 0 ? previewData.fields : (previewData.rows.length > 0 ? Object.keys(previewData.rows[0]) : [])
  return cols.map((c) => ({
    title: c,
    key: c,
    width: 180,
    ellipsis: { tooltip: true },
    render(row: Record<string, unknown>) {
      const val = row[c]
      return val != null ? String(val) : ''
    },
  }))
})

// ── Build ES DSL from simple mode ──────────
function makeBoolClause(logic: 'and' | 'or', clauses: Record<string, unknown>[]): Record<string, unknown> {
  if (logic === 'or') {
    return { bool: { should: clauses, minimum_should_match: 1 } }
  }
  return { bool: { must: clauses } }
}

function buildQueryDsl(): Record<string, unknown> | null {
  if (queryMode.value === 'advanced') {
    try {
      return JSON.parse(advancedQuery.value)
    } catch {
      return null
    }
  }

  const validGroups = queryGroups.value.filter((g) =>
    g.conditions.some((c) => c.field && (c.value || noValueOperators.includes(c.operator))),
  )
  if (validGroups.length === 0) return null

  const groupQueries: Record<string, unknown>[] = []

  for (const group of validGroups) {
    const condQueries: Record<string, unknown>[] = []
    for (const c of group.conditions) {
      if (!c.field) continue
      if (!noValueOperators.includes(c.operator) && !c.value) continue
      switch (c.operator) {
        case 'eq':
          condQueries.push({ term: { [c.field]: c.value } })
          break
        case 'contains':
          condQueries.push({ match: { [c.field]: c.value } })
          break
        case 'gt':
          condQueries.push({ range: { [c.field]: { gt: parseFloat(c.value) || c.value } } })
          break
        case 'lt':
          condQueries.push({ range: { [c.field]: { lt: parseFloat(c.value) || c.value } } })
          break
        case 'gte':
          condQueries.push({ range: { [c.field]: { gte: parseFloat(c.value) || c.value } } })
          break
        case 'lte':
          condQueries.push({ range: { [c.field]: { lte: parseFloat(c.value) || c.value } } })
          break
        case 'not_empty':
          condQueries.push({ exists: { field: c.field } })
          break
        case 'is_empty':
          condQueries.push({ bool: { must_not: { exists: { field: c.field } } } })
          break
      }
    }
    if (condQueries.length === 0) continue
    if (condQueries.length === 1) {
      groupQueries.push(condQueries[0])
    } else {
      groupQueries.push(makeBoolClause(group.logic, condQueries))
    }
  }

  if (groupQueries.length === 0) return null
  if (groupQueries.length === 1) return groupQueries[0]
  return makeBoolClause(groupLogic.value, groupQueries)
}

// ── Connection handlers ─────────────────────
async function handleTestConnection() {
  if (!conn.host.trim()) return
  testing.value = true
  connError.value = ''
  try {
    // Create or update task
    if (!store.currentTask) {
      await store.createTask({
        title: conn.host.replace(/^https?:\/\//, ''),
        es_host: conn.host.trim(),
        es_username: conn.username || undefined,
        es_password: conn.password || undefined,
      })
    } else {
      await store.updateTask(store.currentTask.id, {
        es_host: conn.host.trim(),
        es_username: conn.username || undefined,
        es_password: conn.password || undefined,
      })
    }

    const result = await esExportApi.testConnection(store.currentTask!.id)
    esVersion.value = result.info.version
    connected.value = true

    // Load indices
    loadingIndices.value = true
    const idxResult = await esExportApi.listIndices(store.currentTask!.id)
    indices.value = idxResult.indices
    loadingIndices.value = false
  } catch (e: any) {
    connError.value = e.message || '连接失败'
  } finally {
    testing.value = false
  }
}

function disconnect() {
  connected.value = false
  selectedIndex.value = null
  fieldMapping.value = {}
  selectedFields.value = []
  previewData.total = 0
  previewData.rows = []
  previewData.fields = []
  downloadProgress.completed = 0
  downloadProgress.total = 0
  downloadError.value = ''
}

// ── Index & field handlers ──────────────────
async function handleIndexChange(index: string) {
  if (!store.currentTask) return
  fieldMapping.value = {}
  selectedFields.value = []

  await store.updateTask(store.currentTask.id, { index_name: index })

  try {
    const result = await esExportApi.getMapping(store.currentTask.id, index)
    fieldMapping.value = result.fields
    selectedFields.value = Object.keys(result.fields)
  } catch (e: any) {
    message.warning(e.message || '获取映射失败')
  }
}

function selectAllFields() {
  selectedFields.value = [...fieldList.value]
}

function deselectAllFields() {
  selectedFields.value = []
}

function toggleField(field: string, checked: boolean) {
  if (checked) {
    if (!selectedFields.value.includes(field)) selectedFields.value.push(field)
  } else {
    selectedFields.value = selectedFields.value.filter((f) => f !== field)
  }
}

// ── Query handlers ──────────────────────────
function addQueryCondition(groupIdx: number) {
  queryGroups.value[groupIdx].conditions.push({
    field: fieldList.value[0] || '',
    operator: 'eq',
    value: '',
  })
}

function addQueryGroup() {
  queryGroups.value.push({ logic: 'and', conditions: [] })
}

// ── Preview handler ─────────────────────────
async function handlePreview() {
  if (!store.currentTask || !selectedIndex.value) return

  const queryDsl = buildQueryDsl()

  previewLoading.value = true
  try {
    const result = await esExportApi.previewQuery(store.currentTask.id, {
      query_dsl: queryDsl || undefined,
      output_fields: selectedFields.value.length > 0 ? selectedFields.value : undefined,
      page: 1,
      page_size: 50,
      top_n: maxRecords.value || undefined,
    })
    previewData.total = result.total
    previewData.rows = result.rows
    previewData.fields = result.fields

    if (result.total === 0) {
      message.warning('查询结果为空')
    }

    // Save config to task
    const configObj = {
      queryMode: queryMode.value,
      queryGroups: queryGroups.value,
      groupLogic: groupLogic.value,
      advancedQuery: advancedQuery.value,
      selectedFields: selectedFields.value,
    }
    await store.updateTask(store.currentTask.id, {
      query_dsl: queryDsl ? JSON.stringify(queryDsl) : undefined,
      output_fields: JSON.stringify(selectedFields.value),
      config_json: JSON.stringify(configObj),
    })
  } catch (e: any) {
    message.warning(e.message || '查询失败')
  } finally {
    previewLoading.value = false
  }
}

// ── Download handler (export + auto-download) ─
async function handleDownload() {
  if (!store.currentTask) return

  const queryDsl = buildQueryDsl()

  downloadError.value = ''
  downloadProgress.completed = 0
  downloadProgress.total = 0
  downloading.value = true

  const body = {
    query_dsl: queryDsl || undefined,
    output_fields: selectedFields.value.length > 0 ? selectedFields.value : undefined,
    top_n: maxRecords.value || undefined,
  }

  abortController = new AbortController()

  try {
    const response = await fetch(esExportApi.getExportUrl(store.currentTask.id), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal: abortController.signal,
    })

    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: '导出失败' }))
      throw new Error(err.detail || '导出失败')
    }

    const reader = response.body!.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const event = JSON.parse(line.slice(6))
            if (event.type === 'progress') {
              downloadProgress.completed = event.completed || 0
              downloadProgress.total = event.total || 0
            } else if (event.type === 'done') {
              downloadProgress.completed = event.count || downloadProgress.completed
              // Auto-download the file using the direct file_id endpoint
              await triggerFileDownload(event.file_id)
              downloading.value = false
            } else if (event.type === 'error') {
              downloadError.value = event.content || '导出失败'
              downloading.value = false
            }
          } catch { /* skip */ }
        }
      }
    }
  } catch (err: any) {
    if (err.name !== 'AbortError') {
      downloadError.value = err.message || '下载失败'
    }
    downloading.value = false
  }
}

function stopDownload() {
  if (abortController) {
    abortController.abort()
    abortController = null
    downloading.value = false
  }
}

async function triggerFileDownload(fileId: string) {
  const url = esExportApi.getFileDownloadUrl(fileId)
  const response = await fetch(url)
  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: '下载失败' }))
    throw new Error(err.detail || '下载失败')
  }
  const blob = await response.blob()
  const disposition = response.headers.get('Content-Disposition') || ''
  const match = disposition.match(/filename\*?=(?:UTF-8''|"?)?"?([^";]+)"?/)
  const filename = match ? decodeURIComponent(match[1]) : `export.xlsx`

  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(a.href)
}

// ── Restore task state ──────────────────────
watch(() => store.currentTask, (task) => {
  if (!task) {
    connected.value = false
    conn.host = ''
    conn.username = ''
    conn.password = ''
    selectedIndex.value = null
    fieldMapping.value = {}
    selectedFields.value = []
    previewData.total = 0
    previewData.rows = []
    previewData.fields = []
    downloading.value = false
    downloadProgress.completed = 0
    downloadProgress.total = 0
    downloadError.value = ''
    queryGroups.value = [{ logic: 'and', conditions: [] }]
    groupLogic.value = 'and'
    advancedQuery.value = '{"match_all": {}}'
    return
  }

  // Restore connection info
  conn.host = task.es_host
  conn.username = task.es_username || ''
  conn.password = '' // Don't restore password

  // Restore index
  selectedIndex.value = task.index_name || null

  // Restore config
  if (task.config_json) {
    try {
      const saved = JSON.parse(task.config_json)
      if (saved.queryMode) queryMode.value = saved.queryMode
      if (saved.queryGroups) queryGroups.value = saved.queryGroups
      if (saved.groupLogic) groupLogic.value = saved.groupLogic
      if (saved.advancedQuery) advancedQuery.value = saved.advancedQuery
      if (saved.selectedFields) selectedFields.value = saved.selectedFields
    } catch { /* ignore */ }
  }

  // Restore output_fields
  if (task.output_fields) {
    try {
      selectedFields.value = JSON.parse(task.output_fields)
    } catch { /* ignore */ }
  }

  // If task has a host, try to reconnect silently
  if (task.es_host) {
    connected.value = true
    // Load indices in background
    esExportApi.listIndices(task.id).then((r) => {
      indices.value = r.indices
    }).catch(() => {})
    // Load mapping if index selected
    if (task.index_name) {
      esExportApi.getMapping(task.id, task.index_name).then((r) => {
        fieldMapping.value = r.fields
      }).catch(() => {})
    }
  }
}, { immediate: true })
</script>

<style scoped>
.es-panel {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f5f5f7;
  overflow: hidden;
}

.es-header {
  padding: 0 24px;
  height: 52px;
  display: flex;
  align-items: center;
  background: rgba(255,255,255,0.7);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(0,0,0,0.06);
  flex-shrink: 0;
}

.es-header h2 {
  font-size: 16px;
  font-weight: 700;
  color: #1a1a2e;
}

.es-body {
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

/* ── Connection ──────────────────────────── */
.conn-section {
  background: #fff;
  border-radius: 12px;
  border: 1px solid #e5e5ea;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.conn-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

.conn-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.conn-item label {
  font-size: 13px;
  font-weight: 500;
  color: #4b4b60;
}

.conn-full {
  grid-column: 1 / -1;
}

.conn-error {
  font-size: 13px;
  color: #ef4444;
}

.conn-info {
  background: #fff;
  border-radius: 12px;
  border: 1px solid #e5e5ea;
  padding: 16px;
}

.conn-tag {
  display: flex;
  align-items: center;
  gap: 10px;
}

.conn-host {
  font-size: 14px;
  font-weight: 600;
}

.conn-version {
  font-size: 12px;
  color: #10a37f;
  background: rgba(16, 163, 127, 0.08);
  padding: 2px 8px;
  border-radius: 4px;
}

/* ── Index & Fields ──────────────────────── */
.index-section {
  background: #fff;
  border-radius: 10px;
  border: 1px solid #e5e5ea;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.index-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.index-row label {
  font-size: 13px;
  font-weight: 500;
  color: #4b4b60;
  flex-shrink: 0;
}

.field-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.field-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.field-header label {
  font-size: 13px;
  font-weight: 500;
  color: #4b4b60;
}

.field-actions {
  display: flex;
  gap: 8px;
}

.field-list {
  max-height: 240px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 8px;
  background: #f8f8fa;
  border-radius: 6px;
  border: 1px solid #eeeef2;
}

.field-name {
  font-size: 13px;
}

.field-type {
  font-size: 11px;
  color: #8e8e9a;
  margin-left: 6px;
}

/* ── Query ───────────────────────────────── */
.query-section {
  background: #fff;
  border-radius: 10px;
  border: 1px solid #e5e5ea;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.query-simple {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.query-advanced {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.query-textarea {
  width: 100%;
  padding: 8px 12px;
  font-family: 'Menlo', 'Consolas', monospace;
  font-size: 13px;
  line-height: 1.6;
  border: 1px solid rgb(224, 224, 230);
  border-radius: 6px;
  resize: vertical;
  outline: none;
  box-sizing: border-box;
}

.query-textarea:focus {
  border-color: #6366f1;
  box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2);
}

/* ── Filter groups (reuse batch pattern) ── */
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

.filter-label {
  font-size: 13px;
  font-weight: 500;
  color: #4b4b60;
  min-width: 70px;
  flex-shrink: 0;
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
  width: 160px;
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

.filter-col-del {
  flex-shrink: 0;
}

/* ── Query options ─────────────────────────── */
.query-options {
  display: flex;
  gap: 16px;
  align-items: center;
}

.query-option-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.query-option-label {
  font-size: 13px;
  font-weight: 500;
  color: #4b4b60;
  white-space: nowrap;
}

.inline-warning {
  font-size: 13px;
  color: #b45309;
  background: rgba(245, 158, 11, 0.08);
  padding: 8px 12px;
  border-radius: 6px;
  border: 1px solid rgba(245, 158, 11, 0.2);
  margin: 0;
}

/* ── Preview ─────────────────────────────── */
.preview-info {
  font-size: 13px;
  color: #2e7d32;
  background: rgba(46, 125, 50, 0.06);
  padding: 8px 12px;
  border-radius: 6px;
  border: 1px solid rgba(46, 125, 50, 0.15);
  margin-bottom: 12px;
}

.table-scroll {
  overflow-x: auto;
}

/* ── Export ──────────────────────────────── */
.export-progress {
  margin-top: 12px;
}

.download-area {
  margin-top: 16px;
}

.export-error {
  margin-top: 12px;
  color: #ef4444;
  font-size: 13px;
}
</style>
