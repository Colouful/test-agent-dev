import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: () => import('@/pages/LoginPage.vue'), meta: { public: true } },
    { path: '/register', component: () => import('@/pages/RegisterPage.vue'), meta: { public: true } },
    { path: '/', redirect: '/dashboard' },
    { path: '/dashboard', component: () => import('@/pages/DashboardPage.vue') },
    { path: '/upload', component: () => import('@/pages/UploadPage.vue') },
    { path: '/questions', component: () => import('@/pages/QuestionListPage.vue') },
    { path: '/review', component: () => import('@/pages/ReviewPage.vue') },
    { path: '/print', component: () => import('@/pages/PrintPage.vue') },
  ],
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (!to.meta.public && !auth.token) {
    return '/login'
  }
})

export default router
