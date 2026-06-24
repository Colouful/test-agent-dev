import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { IS_MOCK, mockAuth } from '@/api/mock'
import { authApi } from '@/api/endpoints/auth'

export function useAuth() {
  const auth = useAuthStore()
  const router = useRouter()
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function login(email: string, password: string) {
    loading.value = true
    error.value = null
    try {
      const resp = IS_MOCK
        ? await mockAuth.login(email, password)
        : (await authApi.login(email, password)).data
      auth.setToken(resp.data.access_token)
      if (resp.data.user) auth.user = resp.data.user
      router.push('/dashboard')
    } catch (e: unknown) {
      error.value = (e as Error).message || '登录失败，请检查邮箱和密码'
    } finally {
      loading.value = false
    }
  }

  async function register(email: string, password: string) {
    loading.value = true
    error.value = null
    try {
      IS_MOCK
        ? await mockAuth.register(email, password)
        : await authApi.register(email, password)
      await login(email, password)
    } catch (e: unknown) {
      error.value = (e as Error).message || '注册失败'
    } finally {
      loading.value = false
    }
  }

  function logout() {
    auth.logout()
    router.push('/login')
  }

  return { loading, error, login, register, logout }
}
