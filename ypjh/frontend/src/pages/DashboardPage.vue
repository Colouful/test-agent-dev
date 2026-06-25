<!-- frontend/src/pages/DashboardPage.vue -->
<script setup lang="ts">
import { onMounted } from 'vue'
import { useReview } from '@/composables/useReview'
import { useAuth } from '@/composables/useAuth'

const { store: reviewStore, fetchStats } = useReview()
const { logout } = useAuth()

onMounted(fetchStats)
</script>

<template>
  <div class="min-h-screen bg-gray-50 pb-20">
    <header class="bg-white border-b border-gray-200 sticky top-0 z-10">
      <div class="max-w-2xl mx-auto px-4 py-3 flex items-center justify-between">
        <h1 class="text-lg font-bold text-gray-900">📝 错题本</h1>
        <button @click="logout" class="text-sm text-gray-400 hover:text-gray-600">退出</button>
      </div>
    </header>

    <main class="max-w-2xl mx-auto px-4 py-6 space-y-5">
      <!-- 复习状态卡 -->
      <div class="bg-gradient-to-br from-primary-500 to-primary-700 rounded-2xl p-6 text-white shadow-md">
        <p class="text-sm opacity-80 mb-1">今日待复习</p>
        <p class="text-5xl font-bold mb-4">{{ reviewStore.stats.due_count }}</p>
        <div class="flex items-center gap-4 text-sm opacity-80 flex-wrap">
          <span>今日已完成 <strong class="opacity-100">{{ reviewStore.stats.reviewed_today }}</strong> 题</span>
          <span v-if="reviewStore.stats.pending_correction_count > 0">
            待分析 <strong class="opacity-100 text-yellow-200">{{ reviewStore.stats.pending_correction_count }}</strong> 题
          </span>
        </div>
        <RouterLink v-if="reviewStore.stats.due_count > 0" to="/review"
          class="mt-5 inline-flex items-center gap-1 bg-white text-primary-600 px-5 py-2.5
                 rounded-xl text-sm font-semibold hover:bg-primary-50 transition-colors shadow-sm">
          立即复习 →
        </RouterLink>
        <p v-else class="mt-4 text-sm opacity-70">今日无待复习，保持！💪</p>
      </div>

      <!-- 快捷统计 -->
      <div class="grid grid-cols-2 gap-3">
        <RouterLink to="/questions"
          class="bg-white rounded-2xl p-5 shadow-sm border border-gray-100
                 hover:shadow-md hover:border-primary-200 transition-all active:scale-[0.98]">
          <div class="text-3xl mb-2">📚</div>
          <p class="font-semibold text-gray-900">我的错题</p>
          <p class="text-xs text-gray-400 mt-1">浏览和管理所有错题</p>
        </RouterLink>
        <RouterLink to="/upload"
          class="bg-white rounded-2xl p-5 shadow-sm border border-gray-100
                 hover:shadow-md hover:border-primary-200 transition-all active:scale-[0.98]">
          <div class="text-3xl mb-2">📷</div>
          <p class="font-semibold text-gray-900">拍照录题</p>
          <p class="text-xs text-gray-400 mt-1">AI 自动识别题目</p>
        </RouterLink>
        <RouterLink to="/review"
          class="bg-white rounded-2xl p-5 shadow-sm border border-gray-100
                 hover:shadow-md hover:border-primary-200 transition-all active:scale-[0.98]">
          <div class="text-3xl mb-2">🔄</div>
          <p class="font-semibold text-gray-900">开始复习</p>
          <p class="text-xs text-gray-400 mt-1">SM-2 智能间隔复习</p>
        </RouterLink>
        <RouterLink to="/print"
          class="bg-white rounded-2xl p-5 shadow-sm border border-gray-100
                 hover:shadow-md hover:border-primary-200 transition-all active:scale-[0.98]">
          <div class="text-3xl mb-2">🖨️</div>
          <p class="font-semibold text-gray-900">打印题目</p>
          <p class="text-xs text-gray-400 mt-1">生成 PDF 打印预览</p>
        </RouterLink>
      </div>
    </main>
  </div>
</template>
