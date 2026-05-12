<template>
  <div class="cp-page">
    <div class="cp-card">
      <h2>修改密码</h2>
      <n-form :model="form" label-placement="top">
        <n-form-item label="原密码">
          <n-input v-model:value="form.oldPassword" type="password" show-password-on="click" placeholder="输入原密码" />
        </n-form-item>
        <n-form-item label="新密码">
          <n-input v-model:value="form.newPassword" type="password" show-password-on="click" placeholder="至少 4 个字符" />
        </n-form-item>
        <div class="cp-actions">
          <n-button type="primary" :loading="loading" @click="handleSubmit">保存</n-button>
          <n-button @click="$router.push('/chat')">取消</n-button>
        </div>
      </n-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { NForm, NFormItem, NInput, NButton, useMessage } from 'naive-ui'
import { changePassword } from '../api/auth'

const router = useRouter()
const message = useMessage()
const loading = ref(false)
const form = reactive({ oldPassword: '', newPassword: '' })

async function handleSubmit() {
  if (!form.oldPassword || !form.newPassword) {
    message.warning('请填写完整')
    return
  }
  loading.value = true
  try {
    await changePassword(form.oldPassword, form.newPassword)
    message.success('密码已修改')
    router.push('/chat')
  } catch (e: any) {
    message.error(e.message || '修改失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.cp-page { display: flex; align-items: center; justify-content: center; height: 100%; }
.cp-card { width: 380px; background: #fff; border-radius: 16px; padding: 32px; box-shadow: 0 2px 12px rgba(0,0,0,0.05); }
.cp-card h2 { font-size: 18px; font-weight: 700; margin-bottom: 20px; }
.cp-actions { display: flex; gap: 8px; margin-top: 8px; }
</style>
