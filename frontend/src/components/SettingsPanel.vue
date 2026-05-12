<template>
  <n-drawer v-model:show="store.showSettings" :width="480" placement="right">
    <n-drawer-content>
      <template #header>
        <div class="drawer-title">API Key 设置</div>
      </template>

      <div class="settings-body">
        <div class="section">
          <div class="section-label">
            <span v-if="editingId" class="edit-label">
              编辑 Key
              <span class="edit-name">「{{ editingName }}」</span>
            </span>
            <span v-else>添加 Key</span>
            <span v-if="!editingId && auth.isAdmin" class="admin-note">管理员创建的 Key 默认为全员共享</span>
            <span v-if="!editingId && !auth.isAdmin" class="admin-note">创建私有 Key</span>
          </div>
          <div class="form-card" :class="{ 'form-card-editing': editingId }" ref="formCardRef">
            <n-form :model="form" label-placement="top" size="medium">
              <n-form-item label="名称" :show-feedback="false">
                <n-input v-model:value="form.name" placeholder="如：我的 OpenAI Key" />
              </n-form-item>
              <n-form-item label="协议类型" :show-feedback="false">
                <n-select v-model:value="form.provider" :options="providerOptions" @update:value="onProviderChange" />
              </n-form-item>
              <n-form-item label="Base URL" :show-feedback="false">
                <n-input v-model:value="form.base_url" placeholder="API 地址" />
              </n-form-item>
              <n-form-item label="API Key" :show-feedback="false">
                <n-input v-model:value="form.api_key" type="password" show-password-on="click"
                  :placeholder="editingId ? '留空则不修改' : '输入 API Key'" />
              </n-form-item>
              <n-form-item label="模型" :show-feedback="false">
                <n-input v-model:value="form.model" placeholder="如 gpt-4o 或 claude-sonnet-4-20250514" />
              </n-form-item>
              <n-form-item label="最大上下文 Token" :show-feedback="false">
                <n-input-number v-model:value="form.max_context_tokens" :min="1000" :step="10000" style="width: 100%" />
              </n-form-item>
              <n-form-item label="思考模式" :show-feedback="false">
                <n-switch v-model:value="form.enable_thinking">
                  <template #checked>开启</template>
                  <template #unchecked>关闭</template>
                </n-switch>
              </n-form-item>
              <n-form-item label="模型类型" :show-feedback="false">
                <n-select v-model:value="form.model_type" :options="modelTypeOptions" placeholder="选择模型类型" clearable />
              </n-form-item>
              <div class="form-btns">
                <n-button type="primary" :loading="saving" @click="handleSubmit" class="submit-btn">
                  {{ editingId ? '保存修改' : '添加并验证' }}
                </n-button>
                <n-button v-if="editingId" @click="cancelEdit">取消</n-button>
              </div>
            </n-form>
          </div>
        </div>

        <!-- Shared Keys -->
        <div class="section" v-if="sharedKeys.length > 0">
          <div class="section-label">共享 Key ({{ sharedKeys.length }})</div>
          <div v-for="key in sharedKeys" :key="'s'+key.id" class="key-card" :class="{ 'key-card-editing': key.id === editingId }">
            <div class="key-main">
              <div class="key-top">
                <span class="key-name">{{ key.name }}</span>
                <n-tag :type="key.is_valid ? 'success' : 'error'" size="small" :bordered="false">
                  {{ key.is_valid ? '已连接' : '未验证' }}
                </n-tag>
                <n-tag v-if="key.is_active" type="info" size="small" :bordered="false">使用中</n-tag>
                <n-tag type="warning" size="small" :bordered="false">共享</n-tag>
              </div>
              <div class="key-detail">{{ key.provider }} · {{ key.model }}</div>
              <div class="key-detail" v-if="key.base_url">{{ key.base_url }}</div>
              <!-- Override controls for non-admin on shared keys -->
              <div v-if="!auth.isAdmin" class="override-row">
                <div class="override-item">
                  <span class="override-label">思考</span>
                  <n-switch :value="key.enable_thinking" size="small" @update:value="(val: boolean) => handleOverride(key.id, { enable_thinking: val })" />
                </div>
                <div class="override-item">
                  <span class="override-label">Token</span>
                  <n-input-number :value="key.max_context_tokens" size="tiny" :min="1000" :step="10000" style="width:100px" @update:value="(val: number | null) => { if (val) handleOverride(key.id, { max_context_tokens: val }) }" />
                </div>
              </div>
            </div>
            <div class="key-actions" v-if="auth.isAdmin">
              <n-button text size="tiny" @click="startEdit(key)">编辑</n-button>
              <n-button text size="tiny" @click="store.setActiveKey(key.id)" :disabled="key.is_active">激活</n-button>
              <n-button text size="tiny" @click="handleVerify(key.id)" :loading="verifyingId === key.id">验证</n-button>
              <n-popconfirm @positive-click="store.removeKey(key.id)">
                <template #trigger>
                  <n-button text size="tiny" type="error">删除</n-button>
                </template>
                确认删除此 Key？
              </n-popconfirm>
            </div>
            <div class="key-actions" v-else>
              <n-button text size="tiny" @click="store.setActiveKey(key.id)" :disabled="key.is_active">激活</n-button>
              <n-button text size="tiny" @click="handleVerify(key.id)" :loading="verifyingId === key.id">验证</n-button>
            </div>
          </div>
        </div>

        <!-- My Keys -->
        <div class="section" v-if="myKeys.length > 0">
          <div class="section-label">我的 Key ({{ myKeys.length }})</div>
          <div v-for="key in myKeys" :key="'m'+key.id" class="key-card" :class="{ 'key-card-editing': key.id === editingId }">
            <div class="key-main">
              <div class="key-top">
                <span class="key-name">{{ key.name }}</span>
                <n-tag :type="key.is_valid ? 'success' : 'error'" size="small" :bordered="false">
                  {{ key.is_valid ? '已连接' : '未验证' }}
                </n-tag>
                <n-tag v-if="key.is_active" type="info" size="small" :bordered="false">使用中</n-tag>
              </div>
              <div class="key-detail">{{ key.provider }} · {{ key.model }}</div>
              <div class="key-detail" v-if="key.base_url">{{ key.base_url }}</div>
            </div>
            <div class="key-actions">
              <n-button text size="tiny" @click="startEdit(key)">编辑</n-button>
              <n-button text size="tiny" @click="store.setActiveKey(key.id)" :disabled="key.is_active">激活</n-button>
              <n-button text size="tiny" @click="handleVerify(key.id)" :loading="verifyingId === key.id">验证</n-button>
              <n-popconfirm @positive-click="store.removeKey(key.id)">
                <template #trigger>
                  <n-button text size="tiny" type="error">删除</n-button>
                </template>
                确认删除此 Key？
              </n-popconfirm>
            </div>
          </div>
        </div>

        <div v-if="store.apiKeys.length === 0" class="empty-keys">
          暂无配置，请添加一个 API Key
        </div>
      </div>
    </n-drawer-content>
  </n-drawer>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import {
  NDrawer, NDrawerContent, NForm, NFormItem,
  NInput, NInputNumber, NSelect, NButton, NTag, NPopconfirm, NSwitch,
  useMessage,
} from 'naive-ui'
import { useChatStore } from '../stores/chat'
import { useAuthStore } from '../stores/auth'
import { verifyKey, setKeyOverride } from '../api/keys'
import type { ApiKeyConfig } from '../types'

const store = useChatStore()
const auth = useAuthStore()
const message = useMessage()
const saving = ref(false)
const verifyingId = ref<number | null>(null)
const editingId = ref<number | null>(null)
const editingName = ref('')
const formCardRef = ref<HTMLElement | null>(null)

const sharedKeys = computed(() => store.apiKeys.filter(k => k.user_id === null || k.user_id === undefined))
const myKeys = computed(() => store.apiKeys.filter(k => k.user_id !== null && k.user_id !== undefined))

const modelTypeOptions = [
  { label: 'X1 (星火)', value: 'x1' },
  { label: 'DeepSeek', value: 'deepseek' },
  { label: 'Qwen (通义千问)', value: 'qwen' },
  { label: 'Others', value: 'others' },
]

const providerOptions = [
  { label: 'OpenAI', value: 'openai' },
  { label: 'Anthropic', value: 'anthropic' },
]

const defaultUrls: Record<string, string> = {
  openai: 'https://api.openai.com/v1',
  anthropic: 'https://api.anthropic.com',
}

const form = reactive({
  name: '',
  provider: 'openai' as 'openai' | 'anthropic',
  base_url: defaultUrls.openai,
  api_key: '',
  model: '',
  max_context_tokens: 200000,
  enable_thinking: true,
  model_type: null as string | null,
})

function onProviderChange(val: string) {
  if (!editingId.value) {
    form.base_url = defaultUrls[val] || ''
  }
}

function resetForm() {
  form.name = ''
  form.provider = 'openai'
  form.base_url = defaultUrls.openai
  form.api_key = ''
  form.model = ''
  form.max_context_tokens = 200000
  form.enable_thinking = true
  form.model_type = null
  editingId.value = null
  editingName.value = ''
}

function startEdit(key: ApiKeyConfig) {
  editingId.value = key.id
  editingName.value = key.name
  form.name = key.name
  form.provider = key.provider
  form.base_url = key.base_url
  form.api_key = ''
  form.model = key.model
  form.max_context_tokens = key.max_context_tokens
  form.enable_thinking = key.enable_thinking
  form.model_type = key.model_type || null
  formCardRef.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function cancelEdit() {
  resetForm()
}

async function handleSubmit() {
  if (!form.name || !form.model) {
    message.warning('请填写名称和模型')
    return
  }
  if (!editingId.value && !form.api_key) {
    message.warning('请填写 API Key')
    return
  }

  saving.value = true
  try {
    if (editingId.value) {
      const updateData: Record<string, unknown> = {
        name: form.name,
        provider: form.provider,
        base_url: form.base_url,
        model: form.model,
        max_context_tokens: form.max_context_tokens,
        enable_thinking: form.enable_thinking,
        model_type: form.model_type,
      }
      if (form.api_key) {
        updateData.api_key = form.api_key
      }
      await store.updateKey(editingId.value, updateData)
      message.success('修改已保存')
      resetForm()
    } else {
      const key = await store.addKey({ ...form })
      if (key.is_valid) {
        message.success('添加成功，验证通过')
      } else {
        message.warning('已添加，但验证未通过，请检查配置')
      }
      resetForm()
    }
  } catch {
    message.error(editingId.value ? '修改失败' : '添加失败')
  } finally {
    saving.value = false
  }
}

async function handleVerify(id: number) {
  verifyingId.value = id
  try {
    const result = await verifyKey(id)
    await store.loadKeys()
    if (result.is_valid) {
      message.success(result.message)
    } else {
      message.error(result.message)
    }
  } finally {
    verifyingId.value = null
  }
}

async function handleOverride(keyId: number, data: { enable_thinking?: boolean | null; max_context_tokens?: number | null }) {
  try {
    await setKeyOverride(keyId, data)
    // Optimistically update the local key state
    const key = store.apiKeys.find(k => k.id === keyId)
    if (key) {
      if (data.enable_thinking !== undefined && data.enable_thinking !== null) {
        key.enable_thinking = data.enable_thinking
      }
      if (data.max_context_tokens !== undefined && data.max_context_tokens !== null) {
        key.max_context_tokens = data.max_context_tokens
      }
    }
  } catch (e: any) {
    // Reload keys to revert optimistic update
    await store.loadKeys()
  }
}
</script>

<style scoped>
.drawer-title {
  font-size: 16px;
  font-weight: 700;
}

.settings-body {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.section {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.section-label {
  font-size: 13px;
  font-weight: 600;
  color: #8e8e9a;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}

.admin-note {
  font-size: 11px;
  font-weight: 400;
  color: #b0b0b8;
  text-transform: none;
  letter-spacing: 0;
}

.edit-label {
  color: #5b7cfa;
}

.edit-name {
  font-weight: 600;
  color: #3c5de6;
}

.form-card {
  background: #f9f9fb;
  border: 1px solid #eeeef2;
  border-radius: 12px;
  padding: 12px 20px 10px;
  transition: border-color 0.25s, background 0.25s, box-shadow 0.25s;
}

.form-card-editing {
  background: #f0f4ff;
  border-color: #5b7cfa;
  box-shadow: 0 0 0 1px rgba(91, 124, 250, 0.15);
}

.form-card :deep(.n-form-item) {
  margin-bottom: 10px;
}

.form-card :deep(.n-form-item:last-of-type) {
  margin-bottom: 0;
}

.form-card :deep(.n-form-item-label) {
  margin-bottom: 2px;
}

.form-btns {
  display: flex;
  gap: 8px;
  margin-top: 4px;
}

.think-hint {
  font-size: 11px;
  color: #b0b0b8;
}

.submit-btn {
  flex: 1;
}

.empty-keys {
  text-align: center;
  color: #b0b0b8;
  padding: 20px;
  font-size: 13px;
}

.key-card {
  background: #f9f9fb;
  border: 1px solid #eeeef2;
  border-radius: 12px;
  padding: 14px 16px;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  transition: border-color 0.25s, background 0.25s, box-shadow 0.25s;
}

.key-card-editing {
  background: #f0f4ff;
  border-color: #5b7cfa;
  box-shadow: 0 0 0 2px rgba(91, 124, 250, 0.12);
}

.key-main {
  flex: 1;
  min-width: 0;
}

.key-top {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.key-name {
  font-weight: 600;
  font-size: 14px;
}

.key-detail {
  font-size: 12px;
  color: #8e8e9a;
  line-height: 1.6;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.key-actions {
  display: flex;
  gap: 6px;
  flex-shrink: 0;
  margin-left: 14px;
  align-items: center;
}

.override-row {
  display: flex;
  gap: 16px;
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid #eeeef2;
}

.override-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.override-label {
  font-size: 12px;
  color: #8e8e9a;
}
</style>
