<!-- frontend/src/pages/DashboardPage.vue -->
<script setup lang="ts">
import { onMounted, inject } from 'vue'
import { useReview } from '@/composables/useReview'
import { useAuth } from '@/composables/useAuth'

const { store: reviewStore, fetchStats } = useReview()
const { logout } = useAuth()
const toast = inject<{ show: (t: string, type?: 'success'|'error'|'info') => void }>('toast')

onMounted(fetchStats)

const NAV_ITEMS = [
  { to: '/upload',    icon: '📷', label: '拍照录题', desc: '上传错题图片，AI 自动识别' },
  { to: '/questions', icon: '📚', label: '我的错题', desc: '浏览和管理所有错题' },
  { to: '/review',    icon: '🔄', label: '开始复习', desc: '按 SM-2 算法安排复习' },
  { to: '/print',     icon: '🖨️', label: '打印题目', desc: '生成打印预览，支持 PDF' },
]
</script>

<template>
  <div class="min-h-screen bg-gray-50">
    <!-- 顶部导航 -->
    <header class="bg-white border-b border-gray-200 sticky top-0 z-10">
      <div class="max-w-2xl mx-auto px-4 py-3 flex items-center justify-between">
        <h1 class="text-lg font-bold text-gray-900">📝 错题本</h1>
        <button @click="logout" class="text-sm text-gray-400 hover:text-gray-600">退出</button>
      </div>
    </header>

    <main class="max-w-2xl mx-auto px-4 py-6 space-y-6">
      <!-- 复习状态卡 -->
      <div class="bg-gradient-to-r from-primary-500 to-primary-600 rounded-2xl p-6 text-white">
        <p class="text-sm opacity-75 mb-1">今日待复习</p>
        <p class="text-4xl font-bold mb-4">{{ reviewStore.stats.due_count }}</p>
        <div class="flex items-center gap-4 text-sm">
          <span>今日已完成 <strong>{{ reviewStore.stats.reviewed_today }}</strong> 题</span>
        </div>
        <RouterLink v-if="reviewStore.stats.due_count > 0" to="/review"
          class="mt-4 inline-block bg-white text-primary-600 px-4 py-2 rounded-lg text-sm font-medium
                 hover:bg-primary-50 transition-colors">
          立即复习 →
        </RouterLink>
      </div>

      <!-- 功能入口 -->
      <div class="grid grid-cols-2 gap-3">
        <RouterLink v-for="item in NAV_ITEMS" :key="item.to" :to="item.to"
          class="bg-white rounded-xl p-4 shadow-sm border border-gray-100
                 hover:shadow-md hover:border-primary-200 transition-all
                 focus:outline-none focus:ring-2 focus:ring-primary-500">
          <div class="text-2xl mb-2">{{ item.icon }}</div>
          <p class="font-semibold text-gray-900 text-sm">{{ item.label }}</p>
          <p class="text-xs text-gray-400 mt-0.5">{{ item.desc }}</p>
        </RouterLink>
      </div>
    </main>
  </div>
</template>
