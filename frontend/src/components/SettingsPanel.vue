<template>
  <n-drawer v-model:show="store.showSettings" :width="500" placement="right">
    <n-drawer-content title="API Key 设置">
      <n-card title="添加 API Key" size="small" style="margin-bottom: 16px">
        <n-form :model="form" label-placement="top">
          <n-form-item label="名称">
            <n-input v-model:value="form.name" placeholder="如：我的 OpenAI" />
          </n-form-item>
          <n-form-item label="协议类型">
            <n-select v-model:value="form.provider" :options="providerOptions" @update:value="onProviderChange" />
          </n-form-item>
          <n-form-item label="Base URL">
            <n-input v-model:value="form.base_url" placeholder="API 地址" />
          </n-form-item>
          <n-form-item label="API Key">
            <n-input v-model:value="form.api_key" type="password" show-password-on="click" placeholder="输入 API Key" />
          </n-form-item>
          <n-form-item label="模型">
            <n-input v-model:value="form.model" placeholder="如 gpt-4o 或 claude-sonnet-4-20250514" />
          </n-form-item>
          <n-form-item label="最大上下文 Token">
            <n-input-number v-model:value="form.max_context_tokens" :min="1000" :step="10000" style="width: 100%" />
          </n-form-item>
          <n-button type="primary" block :loading="saving" @click="handleAdd">
            添加并验证
          </n-button>
        </n-form>
      </n-card>

      <n-card title="已配置的 Key" size="small">
        <div v-if="store.apiKeys.length === 0" style="color: #888; text-align: center; padding: 20px">
          暂无配置
        </div>
        <div v-for="key in store.apiKeys" :key="key.id" class="key-item">
          <div class="key-info">
            <div class="key-name">
              {{ key.name }}
              <n-tag :type="key.is_valid ? 'success' : 'error'" size="small">
                {{ key.is_valid ? '已验证' : '未验证' }}
              </n-tag>
              <n-tag v-if="key.is_active" type="info" size="small">当前使用</n-tag>
            </div>
            <div class="key-meta">{{ key.provider }} | {{ key.model }}</div>
          </div>
          <div class="key-actions">
            <n-button text size="small" @click="store.setActiveKey(key.id)" :disabled="key.is_active">
              激活
            </n-button>
            <n-button text size="small" @click="handleVerify(key.id)" :loading="verifyingId === key.id">
              验证
            </n-button>
            <n-popconfirm @positive-click="store.removeKey(key.id)">
              <template #trigger>
                <n-button text size="small" type="error">删除</n-button>
              </template>
              确认删除？
            </n-popconfirm>
          </div>
        </div>
      </n-card>
    </n-drawer-content>
  </n-drawer>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import {
  NDrawer, NDrawerContent, NCard, NForm, NFormItem,
  NInput, NInputNumber, NSelect, NButton, NTag, NPopconfirm,
  useMessage,
} from 'naive-ui'
import { useChatStore } from '../stores/chat'
import { verifyKey } from '../api/keys'

const store = useChatStore()
const message = useMessage()
const saving = ref(false)
const verifyingId = ref<number | null>(null)

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
})

function onProviderChange(val: string) {
  form.base_url = defaultUrls[val] || ''
}

async function handleAdd() {
  if (!form.name || !form.api_key || !form.model) {
    message.warning('请填写名称、API Key 和模型')
    return
  }
  saving.value = true
  try {
    const key = await store.addKey({ ...form })
    if (key.is_valid) {
      message.success('添加成功，验证通过')
    } else {
      message.warning('已添加，但验证未通过，请检查配置')
    }
    form.name = ''
    form.api_key = ''
    form.model = ''
  } catch {
    message.error('添加失败')
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
</script>

<style scoped>
.key-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid #f0f0f0;
}

.key-item:last-child {
  border-bottom: none;
}

.key-name {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 500;
}

.key-meta {
  font-size: 12px;
  color: #888;
  margin-top: 2px;
}

.key-actions {
  display: flex;
  gap: 8px;
}
</style>
