<!-- frontend/src/pages/LoginPage.vue -->
<script setup lang="ts">
import { ref } from 'vue'
import { useAuth } from '@/composables/useAuth'

const email = ref('')
const password = ref('')
const { loading, error, login } = useAuth()
</script>

<template>
  <div class="min-h-screen bg-gradient-to-br from-primary-50 to-blue-100 flex items-center justify-center p-4">
    <div class="bg-white rounded-2xl shadow-lg w-full max-w-sm p-8">
      <div class="text-center mb-8">
        <div class="text-4xl mb-2">📝</div>
        <h1 class="text-2xl font-bold text-gray-900">错题本</h1>
        <p class="text-sm text-gray-400 mt-1">登录开始复习</p>
      </div>

      <form @submit.prevent="login(email, password)" class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">邮箱</label>
          <input v-model="email" type="email" required placeholder="your@email.com"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm
                   focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent
                   transition-colors" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">密码</label>
          <input v-model="password" type="password" required placeholder="请输入密码"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm
                   focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent" />
        </div>

        <p v-if="error" class="text-sm text-red-500">{{ error }}</p>

        <button type="submit" :disabled="loading"
          class="w-full py-2.5 bg-primary-500 text-white rounded-lg font-medium text-sm
                 hover:bg-primary-600 active:bg-primary-700
                 disabled:opacity-60 disabled:cursor-not-allowed transition-colors
                 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2">
          {{ loading ? '登录中…' : '登录' }}
        </button>
      </form>

      <p class="text-center text-sm text-gray-400 mt-6">
        还没有账号？
        <RouterLink to="/register" class="text-primary-500 hover:underline">注册</RouterLink>
      </p>
    </div>
  </div>
</template>
