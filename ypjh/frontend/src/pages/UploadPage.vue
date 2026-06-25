<!-- frontend/src/pages/UploadPage.vue -->
<script setup lang="ts">
import { ref, inject } from 'vue'
import { useRouter } from 'vue-router'
import { useQuestions } from '@/composables/useQuestions'
import ConfirmSheet from '@/components/ConfirmSheet.vue'
import type { Question } from '@/types'

const router = useRouter()
const toast = inject<{ show: (t: string, type?: 'success'|'error'|'info') => void }>('toast')
const { recognizing, recognitionResult, recognize } = useQuestions()
const fileInput = ref<HTMLInputElement | null>(null)
const previewUrl = ref<string | null>(null)
const sheetVisible = ref(false)

async function onFileChange(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  previewUrl.value = URL.createObjectURL(file)
  await recognize(file)
  if (recognitionResult.value?.status !== 'error') {
    sheetVisible.value = true
  }
}

function onSheetClose() {
  sheetVisible.value = false
}

function onSaved(question: Question) {
  sheetVisible.value = false
  toast?.show('录题成功！', 'success')
  router.push(`/questions/${question.id}?new=1`)
}
</script>

<template>
  <div class="min-h-screen bg-gray-50 pb-20">
    <header class="bg-white border-b sticky top-0 z-10">
      <div class="max-w-2xl mx-auto px-4 py-3">
        <h2 class="font-semibold text-gray-900">拍照录题</h2>
      </div>
    </header>

    <main class="max-w-2xl mx-auto px-4 py-6 space-y-4">
      <!-- 上传区域 -->
      <div v-if="!previewUrl"
        @click="fileInput?.click()"
        class="bg-white border-2 border-dashed border-gray-300 rounded-2xl p-12
               flex flex-col items-center gap-3 cursor-pointer
               hover:border-primary-400 hover:bg-primary-50 transition-colors">
        <div class="text-5xl">📷</div>
        <p class="text-gray-600 font-medium">点击选择或拍摄错题图片</p>
        <p class="text-xs text-gray-400">支持 JPEG、PNG、HEIC，最大 20MB</p>
        <input ref="fileInput" type="file" accept="image/*" capture="environment"
          class="hidden" @change="onFileChange">
      </div>

      <!-- 图片预览 -->
      <div v-if="previewUrl" class="bg-white rounded-2xl overflow-hidden shadow-sm">
        <img :src="previewUrl" alt="预览" class="w-full max-h-64 object-contain bg-gray-50">
      </div>

      <!-- 识别中 -->
      <div v-if="recognizing" class="bg-white rounded-2xl p-8 text-center shadow-sm">
        <div class="inline-block w-8 h-8 border-4 border-primary-500 border-t-transparent
                    rounded-full animate-spin mb-3"></div>
        <p class="text-gray-600 text-sm">AI 识别中，请稍候…</p>
      </div>

      <!-- 识别完成提示（Sheet 已打开，不再展示卡片） -->
      <div v-if="recognitionResult && !recognizing && recognitionResult.status === 'error'"
        class="bg-white rounded-2xl shadow-sm p-5">
        <div class="text-center py-4">
          <p class="text-red-500 font-medium">识别失败</p>
          <p class="text-sm text-gray-400 mt-1">{{ recognitionResult.error_hint || '请重新拍摄' }}</p>
          <button @click="previewUrl = null; recognitionResult = null"
            class="mt-3 px-4 py-2 bg-gray-100 rounded-lg text-sm hover:bg-gray-200">
            重新选择
          </button>
        </div>
      </div>
    </main>

      <ConfirmSheet
        :visible="sheetVisible"
        :candidate="recognitionResult?.candidate ?? null"
        @close="onSheetClose"
        @saved="onSaved"
      />
  </div>
</template>
