<template>
  <div class="export-panel">
    <div class="export-body">
      <!-- Step 1: Connection -->
      <div class="step">
        <div class="step-title">1. 连接</div>

        <!-- Type selector (locked after connect) -->
        <div class="conn-section" v-if="!connected">
          <div class="conn-type-row">
            <label>数据源</label>
            <n-select v-model:value="connType" :options="typeOptions" :disabled="connected" style="width: 200px" />
          </div>
          <div class="conn-grid">
            <div class="conn-item">
              <label>Host</label>
              <n-input v-model:value="conn.host" :placeholder="connType === 'es' ? 'http://localhost:9200' : '127.0.0.1'" />
            </div>
            <div class="conn-item">
              <label>端口</label>
              <n-input-number v-model:value="conn.port" :min="1" :max="65535" />
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
          <n-button type="primary" :loading="testing" @click="handleTestConnection" :disabled="!canConnect">
            测试连接
          </n-button>
          <p v-if="connError" class="conn-error">{{ connError }}</p>
        </div>

        <div v-else class="conn-info">
          <div class="conn-tag">
            <span class="conn-host">{{ conn.host }}:{{ conn.port }}</span>
            <span :class="['conn-type-badge', connType]">{{ connType === 'es' ? 'Elasticsearch' : 'MySQL' }}</span>
            <span class="conn-version">{{ version }}</span>
            <n-button size="tiny" type="primary" secondary @click="disconnect">断开</n-button>
          </div>
        </div>
      </div>

      <!-- Step 2: Resource Selection -->
      <div class="step" v-if="connected">
        <div class="step-title">2. {{ connType === 'es' ? '索引与字段' : '数据库与表' }}</div>
        <div class="index-section">
          <!-- ES: index selector -->
          <template v-if="connType === 'es'">
            <div class="index-row">
              <label>索引</label>
              <n-select
                v-model:value="selectedIndex"
                :options="esIndexOptions"
                placeholder="选择索引"
                filterable
                :loading="loadingResources"
                @update:value="handleEsIndexChange"
                style="flex: 1"
              />
            </div>
          </template>

          <!-- MySQL: database → table -->
          <template v-else>
            <div class="index-row">
              <label>数据库</label>
              <n-select
                v-model:value="selectedDatabase"
                :options="mysqlDbOptions"
                placeholder="选择数据库"
                filterable
                :loading="loadingResources"
                @update:value="handleMysqlDbChange"
                style="flex: 1"
              />
            </div>
            <div class="index-row" v-if="selectedDatabase">
              <label>表</label>
              <n-select
                v-model:value="selectedTable"
                :options="mysqlTableOptions"
                placeholder="选择表"
                filterable
                :loading="loadingTables"
                @update:value="handleMysqlTableChange"
                style="flex: 1"
              />
            </div>
          </template>

          <!-- Field/Column list -->
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
                <span class="field-type">{{ fieldsMap[f] }}</span>
              </n-checkbox>
            </div>
          </div>
        </div>
      </div>

      <!-- Step 3: Query -->
      <div class="step" v-if="connected && resourceReady">
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
                <n-select v-model:value="cond.operator" :options="operatorOptions" class="filter-col-op" />
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
              :placeholder="advancedPlaceholder"
            />
          </div>

          <div class="query-options">
            <div class="query-option-item">
              <label class="query-option-label">最大记录数</label>
              <n-input-number v-model:value="maxRecords" :min="0" :max="100000" placeholder="不限制" style="width: 160px" />
            </div>
          </div>

          <p v-if="!hasConditions" class="inline-warning">
            未设置查询条件，将{{ connType === 'es' ? '匹配索引中' : '导出表中' }}的全部数据
          </p>

          <n-button type="primary" secondary :loading="previewLoading" @click="handlePreview">
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
        <n-button type="primary" size="large" :loading="downloading" :disabled="downloading" @click="handleDownload">
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
        <div v-if="exportDone" class="elapsed-info">
          <span>导出完成</span>
          <span :class="['elapsed-time', connType]">{{ exportElapsedText }}</span>
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
import { useMySQLExportStore } from '../stores/mysqlExport'
import * as esExportApi from '../api/esExport'
import * as mysqlExportApi from '../api/mysqlExport'
import { authFetch } from '../api/client'

const esStore = useEsExportStore()
const mysqlStore = useMySQLExportStore()
const message = useMessage()

// ── Type ─────────────────────────────────────
const connType = ref<'es' | 'mysql'>('es')
const typeOptions = [
  { label: 'Elasticsearch', value: 'es' },
  { label: 'MySQL', value: 'mysql' },
]

// ── Connection ──────────────────────────────
const conn = reactive({ host: '', port: 9200, username: '', password: '' })
const connected = ref(false)
const testing = ref(false)
const connError = ref('')
const version = ref('')

const canConnect = computed(() => conn.host.trim().length > 0)

watch(connType, (val) => {
  conn.port = val === 'es' ? 9200 : 3306
  connError.value = ''
  // Reset downstream state
  resetResources()
})

// ── Current store helper ────────────────────
function activeTaskId(): string | null {
  if (connType.value === 'es') return esStore.currentTask?.id ?? null
  return mysqlStore.currentTask?.id ?? null
}

function fullEsHost(): string {
  const host = conn.host.trim().replace(/:\d+$/, '')
  return `${host}:${conn.port}`
}

async function activeCreateTask() {
  if (connType.value === 'es') {
    return esStore.createTask({
      title: fullEsHost().replace(/^https?:\/\//, ''),
      es_host: fullEsHost(),
      es_username: conn.username || undefined,
      es_password: conn.password || undefined,
    })
  } else {
    return mysqlStore.createTask({
      title: `${conn.host}:${conn.port}`,
      mysql_host: conn.host.trim(),
      mysql_port: conn.port,
      mysql_username: conn.username || undefined,
      mysql_password: conn.password || undefined,
    })
  }
}

async function activeUpdateTask(data: Record<string, unknown>) {
  const id = activeTaskId()
  if (!id) return
  if (connType.value === 'es') {
    await esStore.updateTask(id, data as any)
  } else {
    await mysqlStore.updateTask(id, data as any)
  }
}

function activeGetExportUrl(): string {
  const id = activeTaskId()!
  if (connType.value === 'es') return esExportApi.getExportUrl(id)
  return mysqlExportApi.getExportUrl(id)
}

function activeGetFileDownloadUrl(fileId: string): string {
  if (connType.value === 'es') return esExportApi.getFileDownloadUrl(fileId)
  return mysqlExportApi.getFileDownloadUrl(fileId)
}

// ── Resource Selection ──────────────────────
const selectedIndex = ref<string | null>(null)
const selectedDatabase = ref<string | null>(null)
const selectedTable = ref<string | null>(null)
const indices = ref<string[]>([])
const databases = ref<string[]>([])
const tables = ref<string[]>([])
const fieldsMap = ref<Record<string, string>>({})
const selectedFields = ref<string[]>([])
const loadingResources = ref(false)
const loadingTables = ref(false)

const esIndexOptions = computed(() => indices.value.map(i => ({ label: i, value: i })))
const mysqlDbOptions = computed(() => databases.value.map(d => ({ label: d, value: d })))
const mysqlTableOptions = computed(() => tables.value.map(t => ({ label: t, value: t })))
const fieldList = computed(() => Object.keys(fieldsMap.value))
const fieldSelectOptions = computed(() =>
  fieldList.value.map(f => ({ label: `${f} (${fieldsMap.value[f]})`, value: f }))
)

const resourceReady = computed(() => {
  if (connType.value === 'es') return !!selectedIndex.value
  return !!(selectedDatabase.value && selectedTable.value)
})

function resetResources() {
  selectedIndex.value = null
  selectedDatabase.value = null
  selectedTable.value = null
  indices.value = []
  databases.value = []
  tables.value = []
  fieldsMap.value = {}
  selectedFields.value = []
  previewData.total = 0
  previewData.rows = []
  previewData.fields = []
}

// ── Query ───────────────────────────────────
const queryMode = ref<'simple' | 'advanced'>('simple')

interface QueryCondition { field: string; operator: string; value: string }
interface QueryGroup { logic: 'and' | 'or'; conditions: QueryCondition[] }

const queryGroups = ref<QueryGroup[]>([{ logic: 'and', conditions: [] }])
const groupLogic = ref<'and' | 'or'>('and')
const advancedQuery = ref('')
const maxRecords = ref<number | null>(10000)

const esOperators = [
  { label: '等于', value: 'eq' }, { label: '包含', value: 'contains' },
  { label: '大于', value: 'gt' }, { label: '小于', value: 'lt' },
  { label: '大于等于', value: 'gte' }, { label: '小于等于', value: 'lte' },
  { label: '不为空', value: 'not_empty' }, { label: '为空', value: 'is_empty' },
]
const sqlOperators = [
  { label: '等于', value: 'eq' }, { label: '不等于', value: 'neq' },
  { label: '包含', value: 'like' },
  { label: '大于', value: 'gt' }, { label: '小于', value: 'lt' },
  { label: '大于等于', value: 'gte' }, { label: '小于等于', value: 'lte' },
  { label: '为空', value: 'is_null' }, { label: '不为空', value: 'is_not_null' },
]

const operatorOptions = computed(() => connType.value === 'es' ? esOperators : sqlOperators)
const noValueOperators = computed(() => connType.value === 'es' ? ['not_empty', 'is_empty'] : ['is_null', 'is_not_null'])

const advancedPlaceholder = computed(() =>
  connType.value === 'es'
    ? '{"match_all": {}}'
    : 'SELECT * FROM table WHERE ...')

const hasConditions = computed(() =>
  queryMode.value === 'advanced'
    ? advancedQuery.value.trim().length > 0
    : queryGroups.value.some(g => g.conditions.some(c => c.field && (c.value || noValueOperators.value.includes(c.operator)))),
)

// ── Preview ─────────────────────────────────
const previewLoading = ref(false)
const previewData = reactive({ total: 0, rows: [] as Record<string, unknown>[], fields: [] as string[] })

const previewColumns = computed(() => {
  const cols = previewData.fields.length > 0 ? previewData.fields
    : (previewData.rows.length > 0 ? Object.keys(previewData.rows[0]) : [])
  return cols.map(c => ({
    title: c, key: c, width: 180, ellipsis: { tooltip: true },
    render(row: Record<string, unknown>) { return row[c] != null ? String(row[c]) : '' },
  }))
})

// ── Download ─────────────────────────────────
const downloading = ref(false)
const downloadError = ref('')
const downloadProgress = reactive({ completed: 0, total: 0 })
const exportStartTime = ref(0)
const exportDone = ref(false)
let abortController: AbortController | null = null

const exportElapsedText = computed(() => {
  if (!exportDone.value || !exportStartTime.value) return ''
  const sec = Math.round((Date.now() - exportStartTime.value) / 1000)
  if (sec < 60) return `${sec} 秒`
  return `${Math.floor(sec / 60)} 分 ${sec % 60} 秒`
})

// ── ES query DSL builder ────────────────────
function buildEsQueryDsl(): Record<string, unknown> | null {
  if (queryMode.value === 'advanced') {
    try { return JSON.parse(advancedQuery.value) } catch { return null }
  }
  const validGroups = queryGroups.value.filter(g =>
    g.conditions.some(c => c.field && (c.value || noValueOperators.value.includes(c.operator)))
  )
  if (validGroups.length === 0) return null

  const groupQueries: Record<string, unknown>[] = []
  for (const group of validGroups) {
    const condQueries: Record<string, unknown>[] = []
    for (const c of group.conditions) {
      if (!c.field) continue
      if (!noValueOperators.value.includes(c.operator) && !c.value) continue
      switch (c.operator) {
        case 'eq': condQueries.push({ term: { [c.field]: c.value } }); break
        case 'contains': condQueries.push({ match: { [c.field]: c.value } }); break
        case 'gt': condQueries.push({ range: { [c.field]: { gt: parseFloat(c.value) || c.value } } }); break
        case 'lt': condQueries.push({ range: { [c.field]: { lt: parseFloat(c.value) || c.value } } }); break
        case 'gte': condQueries.push({ range: { [c.field]: { gte: parseFloat(c.value) || c.value } } }); break
        case 'lte': condQueries.push({ range: { [c.field]: { lte: parseFloat(c.value) || c.value } } }); break
        case 'not_empty': condQueries.push({ exists: { field: c.field } }); break
        case 'is_empty': condQueries.push({ bool: { must_not: { exists: { field: c.field } } } }); break
      }
    }
    if (condQueries.length === 0) continue
    if (condQueries.length === 1) {
      groupQueries.push(condQueries[0])
    } else {
      groupQueries.push(group.logic === 'or'
        ? { bool: { should: condQueries, minimum_should_match: 1 } }
        : { bool: { must: condQueries } })
    }
  }
  if (groupQueries.length === 0) return null
  if (groupQueries.length === 1) return groupQueries[0]
  return groupLogic.value === 'or'
    ? { bool: { should: groupQueries, minimum_should_match: 1 } }
    : { bool: { must: groupQueries } }
}

// ── MySQL WHERE clause builder ──────────────
function buildWhereClause(): string {
  if (queryMode.value === 'advanced') return ''
  const validGroups = queryGroups.value.filter(g =>
    g.conditions.some(c => c.field && (c.value || noValueOperators.value.includes(c.operator)))
  )
  if (validGroups.length === 0) return ''

  const groupParts: string[] = []
  for (const group of validGroups) {
    const condParts: string[] = []
    for (const c of group.conditions) {
      if (!c.field) continue
      if (!noValueOperators.value.includes(c.operator) && !c.value) continue
      const esc = c.value.replace(/'/g, "''")
      switch (c.operator) {
        case 'eq': condParts.push(`\`${c.field}\` = '${esc}'`); break
        case 'neq': condParts.push(`\`${c.field}\` != '${esc}'`); break
        case 'like': condParts.push(`\`${c.field}\` LIKE '%${esc}%'`); break
        case 'gt': condParts.push(`\`${c.field}\` > '${esc}'`); break
        case 'lt': condParts.push(`\`${c.field}\` < '${esc}'`); break
        case 'gte': condParts.push(`\`${c.field}\` >= '${esc}'`); break
        case 'lte': condParts.push(`\`${c.field}\` <= '${esc}'`); break
        case 'is_null': condParts.push(`\`${c.field}\` IS NULL`); break
        case 'is_not_null': condParts.push(`\`${c.field}\` IS NOT NULL`); break
      }
    }
    if (condParts.length === 0) continue
    groupParts.push(`(${condParts.join(group.logic === 'or' ? ' OR ' : ' AND ')})`)
  }
  return groupParts.join(groupLogic.value === 'or' ? ' OR ' : ' AND ')
}

// ── Connection guard to prevent watchers from restoring state mid-connection
const isConnecting = ref(false)

// ── Connection handlers ─────────────────────
async function handleTestConnection() {
  if (!canConnect.value) return
  testing.value = true
  connError.value = ''
  isConnecting.value = true
  try {
    if (!activeTaskId()) {
      await activeCreateTask()
    } else {
      if (connType.value === 'es') {
        await activeUpdateTask({ es_host: fullEsHost(), es_username: conn.username || undefined, es_password: conn.password || undefined })
      } else {
        await activeUpdateTask({ mysql_host: conn.host.trim(), mysql_port: conn.port, mysql_username: conn.username || undefined, mysql_password: conn.password || undefined })
      }
    }

    const taskId = activeTaskId()!
    let result: { info: { version: string } }
    if (connType.value === 'es') {
      result = await esExportApi.testConnection(taskId)
    } else {
      result = await mysqlExportApi.testConnection(taskId)
    }
    version.value = result.info.version
    connected.value = true

    // Load resources
    loadingResources.value = true
    if (connType.value === 'es') {
      const r = await esExportApi.listIndices(taskId)
      indices.value = r.indices
    } else {
      const r = await mysqlExportApi.listDatabases(taskId)
      databases.value = r.databases
    }
    loadingResources.value = false
  } catch (e: any) {
    connError.value = e.message || '连接失败'
    connected.value = false
    version.value = ''
  } finally {
    testing.value = false
    isConnecting.value = false
  }
}

function disconnect() {
  connected.value = false
  version.value = ''
  resetResources()
  queryGroups.value = [{ logic: 'and', conditions: [] }]
  groupLogic.value = 'and'
  advancedQuery.value = ''
  downloadProgress.completed = 0
  downloadProgress.total = 0
  downloadError.value = ''
  exportDone.value = false
}

// ── Resource handlers ───────────────────────
async function handleEsIndexChange(index: string) {
  const taskId = activeTaskId()
  if (!taskId) return
  fieldsMap.value = {}
  selectedFields.value = []
  await activeUpdateTask({ index_name: index })
  try {
    const r = await esExportApi.getMapping(taskId, index)
    fieldsMap.value = r.fields
    selectedFields.value = Object.keys(r.fields)
  } catch (e: any) { message.warning(e.message || '获取映射失败') }
}

async function handleMysqlDbChange(db: string) {
  const taskId = activeTaskId()
  if (!taskId) return
  selectedTable.value = null
  tables.value = []
  fieldsMap.value = {}
  selectedFields.value = []
  await activeUpdateTask({ database_name: db })
  loadingTables.value = true
  try {
    const r = await mysqlExportApi.listTables(taskId, db)
    tables.value = r.tables
  } catch (e: any) { message.warning(e.message || '获取表列表失败') }
  finally { loadingTables.value = false }
}

async function handleMysqlTableChange(table: string) {
  const taskId = activeTaskId()
  if (!taskId || !selectedDatabase.value) return
  fieldsMap.value = {}
  selectedFields.value = []
  await activeUpdateTask({ table_name: table })
  try {
    const r = await mysqlExportApi.getColumns(taskId, selectedDatabase.value, table)
    fieldsMap.value = r.fields
    selectedFields.value = Object.keys(r.fields)
  } catch (e: any) { message.warning(e.message || '获取列信息失败') }
}

function selectAllFields() { selectedFields.value = [...fieldList.value] }
function deselectAllFields() { selectedFields.value = [] }
function toggleField(field: string, checked: boolean) {
  if (checked) { if (!selectedFields.value.includes(field)) selectedFields.value.push(field) }
  else { selectedFields.value = selectedFields.value.filter(f => f !== field) }
}

// ── Query handlers ──────────────────────────
function addQueryCondition(gi: number) {
  queryGroups.value[gi].conditions.push({ field: fieldList.value[0] || '', operator: 'eq', value: '' })
}
function addQueryGroup() { queryGroups.value.push({ logic: 'and', conditions: [] }) }

// ── Preview handler ─────────────────────────
async function handlePreview() {
  const taskId = activeTaskId()
  if (!taskId || !resourceReady.value) return

  previewLoading.value = true
  try {
    let total = 0
    if (connType.value === 'es') {
      const dsl = buildEsQueryDsl()
      const r = await esExportApi.previewQuery(taskId, {
        query_dsl: dsl || undefined,
        output_fields: selectedFields.value.length > 0 ? selectedFields.value : undefined,
        page: 1, page_size: 50, top_n: maxRecords.value || undefined,
      })
      total = r.total
      previewData.total = total
      previewData.rows = r.rows
      previewData.fields = r.fields

      const configObj = { queryMode: queryMode.value, queryGroups: queryGroups.value, groupLogic: groupLogic.value, advancedQuery: advancedQuery.value, selectedFields: selectedFields.value }
      await activeUpdateTask({
        query_dsl: dsl ? JSON.stringify(dsl) : undefined,
        output_fields: JSON.stringify(selectedFields.value),
        config_json: JSON.stringify(configObj),
      })
    } else {
      const whereClause = buildWhereClause()
      const r = await mysqlExportApi.previewQuery(taskId, {
        database_name: selectedDatabase.value || undefined,
        table_name: selectedTable.value || undefined,
        where_clause: queryMode.value === 'simple' ? whereClause : undefined,
        custom_sql: (queryMode.value === 'advanced' && advancedQuery.value.trim()) ? advancedQuery.value : undefined,
        output_columns: selectedFields.value.length > 0 ? selectedFields.value : undefined,
        page: 1, page_size: 50, top_n: maxRecords.value || undefined,
      })
      total = r.total
      previewData.total = total
      previewData.rows = r.rows
      previewData.fields = r.fields

      const configObj = { queryMode: queryMode.value, queryGroups: queryGroups.value, groupLogic: groupLogic.value, advancedQuery: advancedQuery.value, selectedFields: selectedFields.value }
      await activeUpdateTask({
        where_clause: whereClause || undefined,
        custom_sql: (queryMode.value === 'advanced' && advancedQuery.value.trim()) ? advancedQuery.value : undefined,
        output_columns: JSON.stringify(selectedFields.value),
        config_json: JSON.stringify(configObj),
      })
    }

    if (total === 0) message.warning('查询结果为空')
  } catch (e: any) {
    message.warning(e.message || '查询失败')
  } finally {
    previewLoading.value = false
  }
}

// ── Download handler ────────────────────────
async function handleDownload() {
  const taskId = activeTaskId()
  if (!taskId) return

  downloadError.value = ''
  downloadProgress.completed = 0
  downloadProgress.total = 0
  exportDone.value = false
  exportStartTime.value = Date.now()
  downloading.value = true

  let body: Record<string, unknown>
  if (connType.value === 'es') {
    const dsl = buildEsQueryDsl()
    body = {
      query_dsl: dsl || undefined,
      output_fields: selectedFields.value.length > 0 ? selectedFields.value : undefined,
      top_n: maxRecords.value || undefined,
    }
  } else {
    const whereClause = buildWhereClause()
    body = {
      database_name: selectedDatabase.value || undefined,
      table_name: selectedTable.value || undefined,
      where_clause: queryMode.value === 'simple' ? whereClause : undefined,
      custom_sql: (queryMode.value === 'advanced' && advancedQuery.value.trim()) ? advancedQuery.value : undefined,
      output_columns: selectedFields.value.length > 0 ? selectedFields.value : undefined,
      top_n: maxRecords.value || undefined,
    }
  }

  abortController = new AbortController()
  try {
    const response = await authFetch(activeGetExportUrl(), {
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
              await triggerFileDownload(event.file_id)
              downloading.value = false
              exportDone.value = true
            } else if (event.type === 'error') {
              downloadError.value = event.content || '导出失败'
              downloadProgress.completed = 0
              downloadProgress.total = 0
              downloading.value = false
            }
          } catch { /* skip */ }
        }
      }
    }
  } catch (err: any) {
    if (err.name !== 'AbortError') downloadError.value = err.message || '下载失败'
    downloading.value = false
  }
}

function stopDownload() {
  if (abortController) { abortController.abort(); abortController = null; downloading.value = false }
}

async function triggerFileDownload(fileId: string) {
  const response = await authFetch(activeGetFileDownloadUrl(fileId))
  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: '下载失败' }))
    throw new Error(err.detail || '下载失败')
  }
  const blob = await response.blob()
  const disposition = response.headers.get('Content-Disposition') || ''
  const match = disposition.match(/filename\*?=(?:UTF-8''|"?)?"?([^";]+)"?/)
  const filename = match ? decodeURIComponent(match[1]) : 'export.xlsx'
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(a.href)
}

// ── Restore task state ──────────────────────
function restoreEsTask(task: any) {
  connType.value = 'es'
  const urlMatch = (task.es_host || '').match(/^(.+):(\d+)$/)
  conn.host = urlMatch ? urlMatch[1] : (task.es_host || '')
  conn.port = urlMatch ? parseInt(urlMatch[2]) : 9200
  conn.username = task.es_username || ''
  conn.password = ''
  connected.value = true
  selectedIndex.value = task.index_name || null
  resetResources()
  selectedIndex.value = task.index_name || null
  if (task.index_name) {
    esExportApi.listIndices(task.id).then(r => { indices.value = r.indices }).catch(() => {})
    esExportApi.getMapping(task.id, task.index_name).then(r => {
      fieldsMap.value = r.fields
    }).catch(() => {})
  } else {
    esExportApi.listIndices(task.id).then(r => { indices.value = r.indices }).catch(() => {})
  }
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
  if (task.output_fields) {
    try { selectedFields.value = JSON.parse(task.output_fields) } catch { /* ignore */ }
  }
  downloadProgress.completed = 0
  downloadProgress.total = 0
  downloadError.value = ''
  exportDone.value = false
}

function restoreMysqlTask(task: any) {
  connType.value = 'mysql'
  conn.host = task.mysql_host
  conn.port = task.mysql_port || 3306
  conn.username = task.mysql_username || ''
  conn.password = ''
  connected.value = true
  selectedDatabase.value = task.database_name || null
  selectedTable.value = task.table_name || null
  resetResources()
  selectedDatabase.value = task.database_name || null
  selectedTable.value = task.table_name || null
  mysqlExportApi.listDatabases(task.id).then(r => { databases.value = r.databases }).catch(() => {})
  if (task.database_name) {
    mysqlExportApi.listTables(task.id, task.database_name).then(r => { tables.value = r.tables }).catch(() => {})
    if (task.table_name) {
      mysqlExportApi.getColumns(task.id, task.database_name, task.table_name).then(r => {
        fieldsMap.value = r.fields
      }).catch(() => {})
    }
  }
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
  if (task.output_columns) {
    try { selectedFields.value = JSON.parse(task.output_columns) } catch { /* ignore */ }
  }
  downloadProgress.completed = 0
  downloadProgress.total = 0
  downloadError.value = ''
  exportDone.value = false
}

function resetAll() {
  connected.value = false
  version.value = ''
  conn.host = ''
  conn.port = connType.value === 'es' ? 9200 : 3306
  conn.username = ''
  conn.password = ''
  resetResources()
  queryGroups.value = [{ logic: 'and', conditions: [] }]
  groupLogic.value = 'and'
  advancedQuery.value = ''
  downloadProgress.completed = 0
  downloadProgress.total = 0
  downloadError.value = ''
  exportDone.value = false
}

watch(() => esStore.currentTask, (task, oldTask) => {
  if (isConnecting.value) return
  if (!task) {
    if (!mysqlStore.currentTask) resetAll()
    return
  }
  if (mysqlStore.currentTask) mysqlStore.newTask()
  if (task.id === oldTask?.id) return
  restoreEsTask(task)
})

watch(() => mysqlStore.currentTask, (task, oldTask) => {
  if (isConnecting.value) return
  if (!task) {
    if (!esStore.currentTask) resetAll()
    return
  }
  if (esStore.currentTask) esStore.newTask()
  if (task.id === oldTask?.id) return
  restoreMysqlTask(task)
}, { immediate: true })
</script>

<style scoped>
.export-panel {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  background: #f5f5f7;
  overflow: hidden;
}

.export-body {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  max-width: 960px;
  margin: 0 auto;
  width: 100%;
}

.step { margin-bottom: 28px; }

.step-title {
  font-size: 14px; font-weight: 600; color: #1a1a2e;
  margin-bottom: 12px; padding-bottom: 8px;
  border-bottom: 1px solid #e5e5ea;
}

/* Connection */
.conn-section {
  background: #fff; border-radius: 12px; border: 1px solid #e5e5ea;
  padding: 16px; display: flex; flex-direction: column; gap: 12px;
}
.conn-type-row { display: flex; align-items: center; gap: 10px; }
.conn-type-row label { font-size: 13px; font-weight: 500; color: #4b4b60; }
.conn-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.conn-item { display: flex; flex-direction: column; gap: 4px; }
.conn-item label { font-size: 13px; font-weight: 500; color: #4b4b60; }
.conn-error { font-size: 13px; color: #ef4444; }
.conn-info {
  background: #fff; border-radius: 12px; border: 1px solid #e5e5ea; padding: 16px;
}
.conn-tag { display: flex; align-items: center; gap: 10px; }
.conn-host { font-size: 14px; font-weight: 600; }
.conn-type-badge {
  font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 4px;
}
.conn-type-badge.es { color: #10a37f; background: rgba(16,163,127,0.08); }
.conn-type-badge.mysql { color: #e67e22; background: rgba(230,126,34,0.08); }
.conn-version { font-size: 12px; color: #8e8e9a; }

/* Resource */
.index-section {
  background: #fff; border-radius: 10px; border: 1px solid #e5e5ea;
  padding: 16px; display: flex; flex-direction: column; gap: 12px;
}
.index-row { display: flex; align-items: center; gap: 10px; }
.index-row label { font-size: 13px; font-weight: 500; color: #4b4b60; flex-shrink: 0; min-width: 48px; }
.field-section { display: flex; flex-direction: column; gap: 8px; }
.field-header { display: flex; justify-content: space-between; align-items: center; }
.field-header label { font-size: 13px; font-weight: 500; color: #4b4b60; }
.field-actions { display: flex; gap: 8px; }
.field-list {
  max-height: 240px; overflow-y: auto; display: flex; flex-direction: column; gap: 4px;
  padding: 8px; background: #f8f8fa; border-radius: 6px; border: 1px solid #eeeef2;
}
.field-name { font-size: 13px; }
.field-type { font-size: 11px; color: #8e8e9a; margin-left: 6px; }

/* Query */
.query-section {
  background: #fff; border-radius: 10px; border: 1px solid #e5e5ea;
  padding: 16px; display: flex; flex-direction: column; gap: 12px;
}
.query-simple { display: flex; flex-direction: column; gap: 10px; }
.query-advanced { display: flex; flex-direction: column; gap: 8px; }
.query-textarea {
  width: 100%; padding: 8px 12px; font-family: 'Menlo', 'Consolas', monospace;
  font-size: 13px; line-height: 1.6; border: 1px solid rgb(224,224,230);
  border-radius: 6px; resize: vertical; outline: none; box-sizing: border-box;
}
.query-textarea:focus { border-color: #6366f1; box-shadow: 0 0 0 2px rgba(99,102,241,0.2); }
.query-options { display: flex; gap: 16px; align-items: center; }
.query-option-item { display: flex; align-items: center; gap: 8px; }
.query-option-label { font-size: 13px; font-weight: 500; color: #4b4b60; white-space: nowrap; }
.inline-warning {
  font-size: 13px; color: #b45309; background: rgba(245,158,11,0.08);
  padding: 8px 12px; border-radius: 6px; border: 1px solid rgba(245,158,11,0.2); margin: 0;
}

/* Filter groups */
.filter-group-card {
  background: #f8f8fa; border: 1px solid #eeeef2; border-radius: 8px;
  padding: 10px 12px 8px; display: flex; flex-direction: column; gap: 6px;
}
.filter-group-header { display: flex; justify-content: space-between; align-items: center; }
.filter-group-title { font-size: 12px; font-weight: 600; color: #8e8e9a; }
.filter-group-logic { display: flex; align-items: center; gap: 10px; padding: 4px 0; }
.filter-group-footer { display: flex; justify-content: space-between; align-items: center; margin-top: 2px; }
.filter-label { font-size: 13px; font-weight: 500; color: #4b4b60; min-width: 70px; flex-shrink: 0; }
.filter-row { display: flex; align-items: center; gap: 8px; }
.filter-header-row { font-size: 12px; font-weight: 600; color: #8e8e9a; padding-bottom: 2px; }
.filter-col-field { width: 160px; flex-shrink: 0; }
.filter-col-op { width: 100px; flex-shrink: 0; }
.filter-col-val { flex: 1; min-width: 120px; }
.filter-col-del { flex-shrink: 0; }

/* Preview */
.preview-info {
  font-size: 13px; color: #2e7d32; background: rgba(46,125,50,0.06);
  padding: 8px 12px; border-radius: 6px; border: 1px solid rgba(46,125,50,0.15); margin-bottom: 12px;
}
.table-scroll { overflow-x: auto; }

/* Export */
.export-progress { margin-top: 12px; }
.export-error { margin-top: 12px; color: #ef4444; font-size: 13px; }
.elapsed-info { display: flex; align-items: center; gap: 10px; font-size: 14px; color: #333; margin-top: 12px; }
.elapsed-time {
  padding: 2px 10px; border-radius: 10px; font-weight: 600; font-size: 13px;
  background: #f0f4ff; color: #3c5de6;
}
.elapsed-time.mysql { background: #fef3e2; color: #e67e22; }
</style>
