<template>
  <div class="admin-page">
    <div class="admin-header">
      <h2>用户管理</h2>
      <n-button type="primary" @click="showCreate = true">
        <template #icon>
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M7 3v8M3 7h8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
          </svg>
        </template>
        添加用户
      </n-button>
    </div>

    <n-data-table :columns="columns" :data="users" :bordered="false" />

    <!-- Create User Modal -->
    <n-modal v-model:show="showCreate" title="添加用户">
      <n-card style="width: 400px" title="添加用户" :bordered="false" size="small">
        <n-form :model="createForm" label-placement="top">
          <n-form-item label="用户名">
            <n-input v-model:value="createForm.username" placeholder="2-50 个字符" />
          </n-form-item>
          <n-form-item label="密码">
            <n-input v-model:value="createForm.password" type="password" placeholder="至少 4 个字符" />
          </n-form-item>
          <n-form-item label="角色">
            <n-select v-model:value="createForm.role" :options="roleOptions" />
          </n-form-item>
          <n-button type="primary" block :loading="creating" @click="handleCreate">创建</n-button>
        </n-form>
      </n-card>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, h } from 'vue'
import { NButton, NDataTable, NModal, NCard, NForm, NFormItem, NInput, NSelect, NTag, NPopconfirm, useMessage } from 'naive-ui'
import type { DataTableColumns } from 'naive-ui'
import * as usersApi from '../api/users'
import type { UserInfo } from '../types'

const message = useMessage()
const users = ref<UserInfo[]>([])
const showCreate = ref(false)
const creating = ref(false)

const createForm = ref({ username: '', password: '', role: 'user' })
const roleOptions = [
  { label: '普通用户', value: 'user' },
  { label: '管理员', value: 'admin' },
]

const columns: DataTableColumns<UserInfo> = [
  { title: 'ID', key: 'id', width: 60 },
  { title: '用户名', key: 'username' },
  {
    title: '角色', key: 'role', width: 100,
    render(row) {
      return h(NTag, { type: row.role === 'admin' ? 'info' : 'default', size: 'small', bordered: false }, { default: () => row.role === 'admin' ? '管理员' : '用户' })
    },
  },
  {
    title: '状态', key: 'is_active', width: 80,
    render(row) {
      return h(NTag, { type: row.is_active ? 'success' : 'error', size: 'small', bordered: false }, { default: () => row.is_active ? '正常' : '禁用' })
    },
  },
  { title: '创建时间', key: 'created_at', width: 170 },
  {
    title: '操作', key: 'actions', width: 220,
    render(row) {
      return h('div', { style: 'display:flex;gap:6px;' }, [
        h(NButton, { text: true, size: 'tiny', onClick: () => handleToggleActive(row) }, { default: () => row.is_active ? '禁用' : '启用' }),
        h(NButton, { text: true, size: 'tiny', onClick: () => handleResetPassword(row) }, { default: () => '重置密码' }),
        h(NPopconfirm, { onPositiveClick: () => handleDelete(row.id) }, {
          trigger: () => h(NButton, { text: true, size: 'tiny', type: 'error' }, { default: () => '删除' }),
          default: () => '确认删除此用户？',
        }),
      ])
    },
  },
]

async function loadUsers() { users.value = await usersApi.fetchUsers() }

async function handleCreate() {
  if (!createForm.value.username || !createForm.value.password) {
    message.warning('请填写用户名和密码')
    return
  }
  creating.value = true
  try {
    await usersApi.createUser(createForm.value)
    message.success('用户已创建')
    showCreate.value = false
    createForm.value = { username: '', password: '', role: 'user' }
    await loadUsers()
  } catch (e: any) {
    message.error(e.message || '创建失败')
  } finally {
    creating.value = false
  }
}

async function handleToggleActive(row: UserInfo) {
  try {
    await usersApi.updateUser(row.id, { is_active: !row.is_active })
    await loadUsers()
  } catch (e: any) {
    message.error(e.message || '操作失败')
  }
}

async function handleResetPassword(row: UserInfo) {
  try {
    const newPwd = await usersApi.resetUserPassword(row.id)
    message.success(`密码已重置为: ${newPwd}`)
  } catch (e: any) {
    message.error(e.message || '重置失败')
  }
}

async function handleDelete(id: number) {
  try {
    await usersApi.deleteUser(id)
    message.success('用户已删除')
    await loadUsers()
  } catch (e: any) {
    message.error(e.message || '删除失败')
  }
}

onMounted(() => loadUsers())
</script>

<style scoped>
.admin-page { padding: 32px; max-width: 900px; margin: 0 auto; }
.admin-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.admin-header h2 { font-size: 20px; font-weight: 700; color: #1a1b23; }
</style>
