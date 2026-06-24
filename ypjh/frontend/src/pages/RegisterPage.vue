<!-- frontend/src/pages/RegisterPage.vue -->
<script setup lang="ts">
import { ref } from 'vue'
import { useAuth } from '@/composables/useAuth'

const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const validationError = ref('')
const { loading, error, register } = useAuth()

function submit() {
  if (password.value !== confirmPassword.value) {
    validationError.value = '两次密码不一致'
    return
  }
  validationError.value = ''
  register(email.value, password.value)
}
</script>

<template>
  <div class="min-h-screen bg-gradient-to-br from-primary-50 to-blue-100 flex items-center justify-center p-4">
    <div class="bg-white rounded-2xl shadow-lg w-full max-w-sm p-8">
      <div class="text-center mb-8">
        <div class="text-4xl mb-2">📝</div>
        <h1 class="text-2xl font-bold text-gray-900">创建账号</h1>
      </div>

      <form @submit.prevent="submit" class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">邮箱</label>
          <input v-model="email" type="email" required placeholder="your@email.com"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm
                   focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">密码（至少 8 位）</label>
          <input v-model="password" type="password" required minlength="8" placeholder="请设置密码"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm
                   focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">确认密码</label>
          <input v-model="confirmPassword" type="password" required placeholder="再次输入密码"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm
                   focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent" />
        </div>

        <p v-if="validationError || error" class="text-sm text-red-500">
          {{ validationError || error }}
        </p>

        <button type="submit" :disabled="loading"
          class="w-full py-2.5 bg-primary-500 text-white rounded-lg font-medium text-sm
                 hover:bg-primary-600 disabled:opacity-60 disabled:cursor-not-allowed transition-colors">
          {{ loading ? '创建中…' : '创建账号' }}
        </button>
      </form>

      <p class="text-center text-sm text-gray-400 mt-6">
        已有账号？
        <RouterLink to="/login" class="text-primary-500 hover:underline">登录</RouterLink>
      </p>
    </div>
  </div>
</template>
