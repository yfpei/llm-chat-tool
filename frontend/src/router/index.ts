import { createRouter, createWebHistory } from 'vue-router'

function getToken(): string | null {
  return localStorage.getItem('token')
}

function getUser(): { role: string } | null {
  const raw = localStorage.getItem('user')
  if (!raw) return null
  try {
    return JSON.parse(raw)
  } catch {
    return null
  }
}

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/LoginPage.vue'),
      meta: { guest: true },
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('../views/RegisterPage.vue'),
      meta: { guest: true },
    },
    {
      path: '/',
      redirect: '/chat',
    },
    {
      path: '/chat',
      name: 'chat',
      component: () => import('../views/ChatPage.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/batch',
      name: 'batch',
      component: () => import('../views/BatchPage.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/es-export',
      name: 'es-export',
      component: () => import('../views/EsExportPage.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/admin/users',
      name: 'admin-users',
      component: () => import('../views/AdminUsersPage.vue'),
      meta: { requiresAuth: true, requiresAdmin: true },
    },
    {
      path: '/settings/password',
      name: 'change-password',
      component: () => import('../views/ChangePasswordPage.vue'),
      meta: { requiresAuth: true },
    },
  ],
})

router.beforeEach((to, _from, next) => {
  const token = getToken()

  if (to.meta.requiresAuth && !token) {
    next('/login')
    return
  }

  if (to.meta.guest && token) {
    next('/chat')
    return
  }

  if (to.meta.requiresAdmin) {
    const user = getUser()
    if (!user || user.role !== 'admin') {
      next('/chat')
      return
    }
  }

  next()
})

export default router
