<!-- frontend/src/pages/QuestionListPage.vue -->
<script setup lang="ts">
import { onMounted, inject, computed, ref } from 'vue'
import { useQuestions } from '@/composables/useQuestions'
import QuestionCard from '@/components/QuestionCard.vue'
import SkeletonCard from '@/components/SkeletonCard.vue'
import type { Question } from '@/types'

const { store, fetchList, softDelete } = useQuestions()
const toast = inject<{ show: (t: string, type?: 'success'|'error'|'info') => void }>('toast')
const activeSubject = ref<string>('全部')

onMounted(() => fetchList())

async function onDelete(id: string) {
  await softDelete(id)
  toast?.show('已删除', 'success')
}

// 从题目列表提取科目标签（去重，保持出现顺序）
const subjectTabs = computed(() => {
  const seen = new Set<string>()
  const tabs: string[] = ['全部']
  for (const q of store.items) {
    const s = q.subject ?? '其他'
    if (!seen.has(s)) {
      seen.add(s)
      tabs.push(s)
    }
  }
  // 「其他」始终排最后
  const idx = tabs.indexOf('其他')
  if (idx > 1) {
    tabs.splice(idx, 1)
    tabs.push('其他')
  }
  return tabs
})

// 按当前选中科目过滤并分组
const groupedItems = computed<{ subject: string; items: Question[] }[]>(() => {
  const filtered = store.items.filter(q => {
    if (activeSubject.value === '全部') return true
    const s = q.subject ?? '其他'
    return s === activeSubject.value
  })

  if (activeSubject.value !== '全部') {
    return [{ subject: activeSubject.value, items: filtered }]
  }

  // 全部模式：按科目分组
  const map = new Map<string, Question[]>()
  for (const q of filtered) {
    const s = q.subject ?? '其他'
    if (!map.has(s)) map.set(s, [])
    map.get(s)!.push(q)
  }
  // 保持 subjectTabs 顺序（跳过"全部"）
  const groups: { subject: string; items: Question[] }[] = []
  for (const tab of subjectTabs.value.slice(1)) {
    if (map.has(tab)) groups.push({ subject: tab, items: map.get(tab)! })
  }
  return groups
})
</script>

<template>
  <div class="min-h-screen bg-gray-50 pb-20">
    <header class="bg-white border-b sticky top-0 z-10">
      <div class="max-w-2xl mx-auto px-4 py-3 flex items-center justify-between">
        <h2 class="font-semibold text-gray-900">我的错题（{{ store.total }}）</h2>
        <RouterLink to="/upload"
          class="text-sm bg-primary-500 text-white px-3 py-1.5 rounded-lg
                 hover:bg-primary-600 transition-colors">
          + 录题
        </RouterLink>
      </div>

      <!-- 科目标签栏 -->
      <div v-if="!store.loading && store.items.length > 0"
           class="max-w-2xl mx-auto px-4 pb-2 flex gap-2 overflow-x-auto
                  scrollbar-hide">
        <button
          v-for="tab in subjectTabs"
          :key="tab"
          @click="activeSubject = tab"
          class="shrink-0 px-3 py-1 rounded-full text-xs font-medium transition-colors"
          :class="activeSubject === tab
            ? 'bg-primary-500 text-white'
            : 'bg-gray-100 text-gray-600 hover:bg-gray-200'"
        >
          {{ tab }}
        </button>
      </div>
    </header>

    <main class="max-w-2xl mx-auto px-4 py-4 space-y-3">
      <!-- 加载骨架 -->
      <template v-if="store.loading">
        <SkeletonCard v-for="i in 3" :key="i" :lines="4" />
      </template>

      <!-- 空状态 -->
      <template v-else-if="store.items.length === 0">
        <div class="text-center py-16 text-gray-400">
          <div class="text-5xl mb-4">📭</div>
          <p class="font-medium">还没有错题</p>
          <RouterLink to="/upload" class="text-primary-500 text-sm mt-2 block hover:underline">
            去录第一道题 →
          </RouterLink>
        </div>
      </template>

      <!-- 分组列表 -->
      <template v-else>
        <template v-for="group in groupedItems" :key="group.subject">
          <!-- 分组标题（仅"全部"模式显示） -->
          <p v-if="activeSubject === '全部'"
             class="text-xs text-gray-400 font-medium px-1 pt-2">
            {{ group.subject }} · {{ group.items.length }}题
          </p>
          <QuestionCard
            v-for="q in group.items"
            :key="q.id"
            :question="q"
            :show-answer="false"
            @delete="onDelete"
          />
        </template>
      </template>
    </main>
  </div>
</template>
