<template>
  <div class="auth-page">
    <div class="auth-card">
      <div class="auth-header">
        <div class="auth-icon">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
            <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </div>
        <h1>登录 LLM Chat</h1>
      </div>
      <n-form :model="form" label-placement="top">
        <n-form-item label="用户名">
          <n-input v-model:value="form.username" placeholder="输入用户名" size="large" />
        </n-form-item>
        <n-form-item label="密码">
          <n-input v-model:value="form.password" type="password" show-password-on="click" placeholder="输入密码" size="large" @keyup.enter="handleLogin" />
        </n-form-item>
        <n-button type="primary" block size="large" :loading="loading" @click="handleLogin">登录</n-button>
      </n-form>
      <div class="auth-switch">
        还没有账号？<router-link to="/register">注册</router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { NForm, NFormItem, NInput, NButton, useMessage } from 'naive-ui'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()
const message = useMessage()
const loading = ref(false)

const form = reactive({ username: '', password: '' })

async function handleLogin() {
  if (!form.username || !form.password) {
    message.warning('请填写用户名和密码')
    return
  }
  loading.value = true
  try {
    await auth.login(form.username, form.password)
    router.push('/chat')
  } catch (e: any) {
    message.error(e.message || '登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-page {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100vh;
  background: #f5f5f7;
}
.auth-card {
  width: 380px;
  background: #fff;
  border-radius: 16px;
  padding: 36px 32px 28px;
  box-shadow: 0 2px 16px rgba(0, 0, 0, 0.06);
}
.auth-header {
  text-align: center;
  margin-bottom: 28px;
}
.auth-icon {
  width: 48px;
  height: 48px;
  border-radius: 14px;
  background: linear-gradient(135deg, #6366f1, #5558e6);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  margin-bottom: 12px;
}
.auth-header h1 {
  font-size: 20px;
  font-weight: 700;
  color: #1a1b23;
}
.auth-switch {
  text-align: center;
  margin-top: 18px;
  font-size: 13px;
  color: #8e8e9a;
}
.auth-switch a {
  color: #6366f1;
  text-decoration: none;
  font-weight: 600;
}
</style>
