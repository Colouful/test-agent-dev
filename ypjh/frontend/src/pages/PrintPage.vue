<!-- frontend/src/pages/PrintPage.vue -->
<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useQuestions } from '@/composables/useQuestions'
import { IS_MOCK, mockPrint } from '@/api/mock'
import { apiClient } from '@/api/client'

const { store, fetchList } = useQuestions()
const selected = ref<Set<string>>(new Set())
const showAnswer = ref(true)
const layout = ref<'single' | 'double'>('single')
const loading = ref(false)
const previewHtml = ref('')

onMounted(() => fetchList(100, 0))

function toggleSelect(id: string) {
  selected.value.has(id) ? selected.value.delete(id) : selected.value.add(id)
}
const allSelected = computed(() => store.items.every(q => selected.value.has(q.id)))
function toggleAll() {
  allSelected.value
    ? (selected.value = new Set())
    : store.items.forEach(q => selected.value.add(q.id))
}

async function generatePreview() {
  if (selected.value.size === 0) return
  loading.value = true
  try {
    if (IS_MOCK) {
      const resp = await mockPrint.preview([...selected.value], {})
      previewHtml.value = resp.data.html
    } else {
      const resp = await apiClient.post('/v1/print/preview', {
        question_ids: [...selected.value],
        show_answer: showAnswer.value,
        layout: layout.value,
      }, { responseType: 'text' })
      previewHtml.value = resp.data
    }
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="min-h-screen bg-gray-50">
    <header class="bg-white border-b sticky top-0 z-10">
      <div class="max-w-2xl mx-auto px-4 py-3 flex items-center justify-between">
        <div class="flex items-center gap-3">
          <RouterLink to="/dashboard" class="text-gray-400">← 返回</RouterLink>
          <h2 class="font-semibold text-gray-900">打印设置</h2>
        </div>
        <span class="text-sm text-gray-400">已选 {{ selected.size }} 题</span>
      </div>
    </header>

    <main class="max-w-2xl mx-auto px-4 py-4">
      <!-- 打印选项 -->
      <div class="bg-white rounded-xl shadow-sm p-4 mb-4 space-y-3">
        <label class="flex items-center gap-3 cursor-pointer">
          <input type="checkbox" v-model="showAnswer" class="rounded text-primary-500">
          <span class="text-sm text-gray-700">显示答案</span>
        </label>
        <div class="flex items-center gap-3">
          <span class="text-sm text-gray-700">布局</span>
          <select v-model="layout"
            class="text-sm border border-gray-300 rounded-lg px-2 py-1
                   focus:outline-none focus:ring-2 focus:ring-primary-500">
            <option value="single">单列</option>
            <option value="double">双列</option>
          </select>
        </div>
      </div>

      <!-- 全选 -->
      <div class="flex items-center justify-between mb-3 px-1">
        <p class="text-sm text-gray-500">选择要打印的题目</p>
        <button @click="toggleAll" class="text-xs text-primary-500 hover:underline">
          {{ allSelected ? '取消全选' : '全选' }}
        </button>
      </div>

      <!-- 题目列表 -->
      <div class="space-y-2 mb-6">
        <div v-for="q in store.items" :key="q.id"
          @click="toggleSelect(q.id)"
          :class="['bg-white rounded-xl p-4 border cursor-pointer transition-all',
                   selected.has(q.id)
                     ? 'border-primary-400 ring-1 ring-primary-200'
                     : 'border-gray-100 hover:border-gray-300']">
          <div class="flex items-start gap-3">
            <div :class="['w-4 h-4 rounded border-2 flex-shrink-0 mt-0.5 transition-colors',
                          selected.has(q.id)
                            ? 'border-primary-500 bg-primary-500'
                            : 'border-gray-300']">
              <svg v-if="selected.has(q.id)" class="w-3 h-3 text-white" viewBox="0 0 12 12" fill="none">
                <path d="M2 6l3 3 5-5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
              </svg>
            </div>
            <div class="flex-1 min-w-0">
              <span v-if="q.subject" class="text-xs text-blue-600 bg-blue-50 px-1.5 py-0.5 rounded">{{ q.subject }}</span>
              <p class="text-sm text-gray-700 truncate mt-1">{{ q.content }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- 生成预览按钮 -->
      <button @click="generatePreview" :disabled="loading || selected.size === 0"
        class="w-full py-3 bg-primary-500 text-white rounded-xl font-medium
               hover:bg-primary-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors">
        {{ loading ? '生成中…' : `生成打印预览（${selected.size} 题）` }}
      </button>

      <!-- 预览结果 iframe -->
      <div v-if="previewHtml" class="mt-4 bg-white rounded-xl overflow-hidden shadow-sm">
        <div class="px-4 py-2 border-b border-gray-100 text-xs text-gray-400">预览</div>
        <iframe :srcdoc="previewHtml" class="w-full h-[600px] border-0"></iframe>
      </div>
    </main>
  </div>
</template>
