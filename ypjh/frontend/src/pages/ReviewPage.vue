<!-- frontend/src/pages/ReviewPage.vue -->
<script setup lang="ts">
import { onMounted, computed, ref } from 'vue'
import { useKatex } from '@/composables/useKatex'
import { useReview } from '@/composables/useReview'
import ReviewScoreButtons from '@/components/ReviewScoreButtons.vue'

const { store, submitting, loading, fetchQueue, submitScore } = useReview()
const showAnswer = ref(false)
const container = ref<HTMLElement | null>(null)
useKatex(container)

onMounted(fetchQueue)

const current = computed(() => store.current())
const isDone = computed(() => store.currentIndex >= store.queue.length && store.queue.length > 0)

async function onScore(score: number) {
  if (!current.value) return
  showAnswer.value = false
  await submitScore(current.value.id, score)
}
</script>

<template>
  <div class="min-h-screen bg-gray-50 flex flex-col pb-20">
    <header class="bg-white border-b sticky top-0 z-10">
      <div class="max-w-2xl mx-auto px-4 py-3 flex items-center justify-between">
        <h2 class="font-semibold text-gray-900">每日复习</h2>
        <p class="text-sm text-gray-500">
          {{ store.currentIndex }}/{{ store.queue.length }}
        </p>
      </div>
    </header>

    <main class="max-w-2xl mx-auto px-4 py-6 flex-1 flex flex-col">
      <!-- 全部完成 -->
      <div v-if="isDone" class="flex-1 flex flex-col items-center justify-center text-center gap-4">
        <div class="text-6xl">🎉</div>
        <h2 class="text-xl font-bold text-gray-900">今日复习完成！</h2>
        <p class="text-gray-400 text-sm">共完成 {{ store.queue.length }} 道题</p>
        <RouterLink to="/dashboard"
          class="bg-primary-500 text-white px-6 py-2.5 rounded-lg text-sm font-medium hover:bg-primary-600">
          返回首页
        </RouterLink>
      </div>

      <!-- 加载中 -->
      <div v-else-if="loading"
        class="flex-1 flex items-center justify-center text-gray-300 text-sm">
        加载中…
      </div>

      <!-- 无待复习 -->
      <div v-else-if="store.queue.length === 0 && !current"
        class="flex-1 flex flex-col items-center justify-center text-center gap-4 text-gray-400">
        <div class="text-5xl">✅</div>
        <p class="font-medium">今天没有待复习题目</p>
        <RouterLink to="/dashboard" class="text-primary-500 text-sm hover:underline">返回首页</RouterLink>
      </div>

      <!-- 复习卡片 -->
      <div v-else-if="current" ref="container" class="flex-1 flex flex-col gap-4">
        <!-- 进度条 -->
        <div class="h-1.5 bg-gray-200 rounded-full overflow-hidden">
          <div class="h-full bg-primary-500 transition-all"
            :style="`width: ${(store.currentIndex / store.queue.length) * 100}%`"></div>
        </div>

        <!-- 题目卡片 -->
        <div class="bg-white rounded-2xl shadow-sm p-6 flex-1">
          <div v-if="current.subject" class="mb-3">
            <span class="text-xs px-2 py-0.5 bg-blue-50 text-blue-600 rounded-full">
              {{ current.subject }}
            </span>
          </div>
          <div v-if="current.image_url" class="mb-4">
            <img :src="current.image_url" alt="题目图片"
              class="max-w-full rounded-lg border border-gray-100" loading="lazy">
          </div>
          <p class="font-serif text-gray-800 text-base leading-relaxed whitespace-pre-wrap">
            {{ current.content }}
          </p>

          <!-- 答案（点击显示）-->
          <div v-if="showAnswer" class="mt-4 pt-4 border-t border-dashed border-gray-200">
            <p class="text-xs text-gray-400 mb-1">正确答案</p>
            <p class="text-green-700 font-medium">{{ current.correct_answer }}</p>
          </div>
        </div>

        <!-- 操作区 -->
        <div class="space-y-3">
          <button v-if="!showAnswer"
            @click="showAnswer = true"
            class="w-full py-3 bg-white border border-gray-300 rounded-xl text-sm font-medium
                   text-gray-700 hover:bg-gray-50 transition-colors shadow-sm">
            查看答案
          </button>

          <ReviewScoreButtons v-else :disabled="submitting" @score="onScore" />
        </div>
      </div>
    </main>
  </div>
</template>
