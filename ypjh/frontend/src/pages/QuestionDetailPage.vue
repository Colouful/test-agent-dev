<!-- frontend/src/pages/QuestionDetailPage.vue -->
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { IS_MOCK, mockQuestions } from '@/api/mock'
import { questionsApi } from '@/api/endpoints/questions'
import type { Question } from '@/types'

const route = useRoute()
const question = ref<Question | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)

onMounted(async () => {
  try {
    const id = route.params.id as string
    if (IS_MOCK) {
      const resp = await mockQuestions.get(id)
      if (resp.error) {
        error.value = resp.error.message || '题目不存在'
      } else {
        question.value = resp.data
      }
    } else {
      const resp = await questionsApi.get(id)
      question.value = resp.data.data
    }
  } catch {
    error.value = '加载失败，请返回重试'
  } finally {
    loading.value = false
  }
})

const TYPE_LABELS: Record<string, string> = {
  multiple_choice: '选择题',
  fill: '填空题',
  short_answer: '简答题',
  calculation: '计算题',
}
</script>

<template>
  <div class="min-h-screen bg-gray-50 pb-20">
    <!-- 顶部标题栏 -->
    <header class="bg-white border-b sticky top-0 z-10">
      <div class="max-w-2xl mx-auto px-4 py-3 flex items-center gap-3">
        <button @click="$router.back()" class="text-gray-400 hover:text-gray-600 transition-colors">
          ←
        </button>
        <h2 class="font-semibold text-gray-900">错题详情</h2>
      </div>
    </header>

    <main class="max-w-2xl mx-auto px-4 py-4 space-y-4">
      <!-- 加载中 -->
      <div v-if="loading" class="space-y-3">
        <div class="h-6 bg-gray-200 rounded animate-pulse w-1/3"></div>
        <div class="h-32 bg-gray-200 rounded animate-pulse"></div>
        <div class="h-20 bg-gray-200 rounded animate-pulse"></div>
      </div>

      <!-- 加载失败 -->
      <div v-else-if="error" class="text-center py-16 text-gray-400">
        <div class="text-4xl mb-3">⚠️</div>
        <p>{{ error }}</p>
      </div>

      <!-- 内容 -->
      <template v-else-if="question">
        <!-- 标签行 -->
        <div class="flex flex-wrap gap-2">
          <span v-if="question.subject"
            class="text-xs px-2 py-0.5 rounded-full bg-blue-50 text-blue-600 font-medium">
            {{ question.subject }}
          </span>
          <span v-if="question.question_type && TYPE_LABELS[question.question_type]"
            class="text-xs px-2 py-0.5 rounded-full bg-purple-50 text-purple-600 font-medium">
            {{ TYPE_LABELS[question.question_type] }}
          </span>
          <span :class="[
            'text-xs px-2 py-0.5 rounded-full font-medium',
            question.status === 'confirmed'
              ? 'bg-green-50 text-green-600'
              : 'bg-yellow-50 text-yellow-600'
          ]">
            {{ question.status === 'confirmed' ? '已确认' : '待确认' }}
          </span>
        </div>

        <!-- 图片 -->
        <div v-if="question.image_url" class="bg-white rounded-2xl overflow-hidden shadow-sm">
          <img :src="question.image_url" alt="题目图片"
            class="w-full object-contain bg-gray-50 max-h-72" loading="lazy">
        </div>

        <!-- 题目内容 -->
        <div class="bg-white rounded-2xl shadow-sm p-5">
          <p class="text-xs text-gray-400 mb-2">题目内容</p>
          <p class="font-serif text-gray-800 text-base leading-relaxed whitespace-pre-wrap">
            {{ question.content }}
          </p>
        </div>

        <!-- 答案区 -->
        <div class="bg-white rounded-2xl shadow-sm p-5 space-y-4">
          <div>
            <p class="text-xs text-gray-400 mb-1.5">正确答案</p>
            <p class="text-green-700 font-medium leading-relaxed">{{ question.correct_answer }}</p>
          </div>
          <div v-if="question.wrong_answer" class="border-t border-gray-100 pt-4">
            <p class="text-xs text-gray-400 mb-1.5">我的错误</p>
            <p class="text-red-500 leading-relaxed">{{ question.wrong_answer }}</p>
          </div>
          <div v-if="question.note" class="border-t border-gray-100 pt-4">
            <p class="text-xs text-gray-400 mb-1.5">笔记</p>
            <p class="text-gray-600 italic leading-relaxed">{{ question.note }}</p>
          </div>
        </div>

        <!-- 统计信息 -->
        <div class="bg-white rounded-2xl shadow-sm p-5">
          <p class="text-xs text-gray-400 mb-3">复习记录</p>
          <div class="grid grid-cols-3 gap-4 text-center">
            <div>
              <p class="text-xl font-bold text-gray-800">{{ question.review_count }}</p>
              <p class="text-xs text-gray-400 mt-0.5">复习次数</p>
            </div>
            <div>
              <p class="text-xl font-bold text-gray-800">{{ question.interval_days }}</p>
              <p class="text-xs text-gray-400 mt-0.5">复习间隔(天)</p>
            </div>
            <div>
              <p class="text-xl font-bold text-gray-800">{{ question.ease_factor.toFixed(1) }}</p>
              <p class="text-xs text-gray-400 mt-0.5">难度系数</p>
            </div>
          </div>
        </div>
      </template>
    </main>
  </div>
</template>
