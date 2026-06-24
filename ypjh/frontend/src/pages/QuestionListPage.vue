<!-- frontend/src/pages/QuestionListPage.vue -->
<script setup lang="ts">
import { onMounted, inject } from 'vue'
import { useQuestions } from '@/composables/useQuestions'
import QuestionCard from '@/components/QuestionCard.vue'
import SkeletonCard from '@/components/SkeletonCard.vue'

const { store, fetchList, softDelete } = useQuestions()
const toast = inject<{ show: (t: string, type?: 'success'|'error'|'info') => void }>('toast')

onMounted(() => fetchList())

async function onDelete(id: string) {
  await softDelete(id)
  toast?.show('已删除', 'success')
}
</script>

<template>
  <div class="min-h-screen bg-gray-50">
    <header class="bg-white border-b sticky top-0 z-10">
      <div class="max-w-2xl mx-auto px-4 py-3 flex items-center justify-between">
        <div class="flex items-center gap-3">
          <RouterLink to="/dashboard" class="text-gray-400">← 返回</RouterLink>
          <h2 class="font-semibold text-gray-900">我的错题（{{ store.total }}）</h2>
        </div>
        <RouterLink to="/upload"
          class="text-sm bg-primary-500 text-white px-3 py-1.5 rounded-lg hover:bg-primary-600">
          + 录题
        </RouterLink>
      </div>
    </header>

    <main class="max-w-2xl mx-auto px-4 py-4 space-y-3">
      <template v-if="store.loading">
        <SkeletonCard v-for="i in 3" :key="i" :lines="4" />
      </template>

      <template v-else-if="store.items.length === 0">
        <div class="text-center py-16 text-gray-400">
          <div class="text-5xl mb-4">📭</div>
          <p class="font-medium">还没有错题</p>
          <RouterLink to="/upload" class="text-primary-500 text-sm mt-2 block hover:underline">
            去录第一道题 →
          </RouterLink>
        </div>
      </template>

      <template v-else>
        <QuestionCard v-for="q in store.items" :key="q.id"
          :question="q" @delete="onDelete" />
      </template>
    </main>
  </div>
</template>
