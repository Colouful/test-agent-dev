<!-- frontend/src/pages/UploadPage.vue -->
<script setup lang="ts">
import { ref, inject } from 'vue'
import { useRouter } from 'vue-router'
import { useQuestions } from '@/composables/useQuestions'

const router = useRouter()
const toast = inject<{ show: (t: string, type?: 'success'|'error'|'info') => void }>('toast')
const { recognizing, recognitionResult, recognize, confirmAndSave } = useQuestions()
const fileInput = ref<HTMLInputElement | null>(null)
const previewUrl = ref<string | null>(null)
const saving = ref(false)

async function onFileChange(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  previewUrl.value = URL.createObjectURL(file)
  await recognize(file)
}

async function onConfirm() {
  if (!recognitionResult.value?.candidate) return
  saving.value = true
  try {
    await confirmAndSave({
      content: recognitionResult.value.candidate.content,
      correct_answer: recognitionResult.value.candidate.correct_answer,
      wrong_answer: recognitionResult.value.candidate.wrong_answer ?? undefined,
      subject: recognitionResult.value.candidate.subject ?? undefined,
      question_type: recognitionResult.value.candidate.question_type ?? undefined,
      confidence: recognitionResult.value.candidate.confidence,
      analysis: recognitionResult.value.candidate.analysis ?? null,
    })
    toast?.show('录题成功！', 'success')
    router.push('/questions')
  } finally {
    saving.value = false
  }
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

      <!-- 识别结果 -->
      <div v-if="recognitionResult && !recognizing" class="bg-white rounded-2xl shadow-sm p-5 space-y-4">
        <div v-if="recognitionResult.status === 'error'"
          class="text-center py-4">
          <p class="text-red-500 font-medium">识别失败</p>
          <p class="text-sm text-gray-400 mt-1">{{ recognitionResult.error_hint || '请重新拍摄' }}</p>
          <button @click="previewUrl = null; recognitionResult = null"
            class="mt-3 px-4 py-2 bg-gray-100 rounded-lg text-sm hover:bg-gray-200">
            重新选择
          </button>
        </div>

        <template v-else-if="recognitionResult.candidate">
          <div class="flex items-center gap-2">
            <span class="text-xs px-2 py-0.5 rounded-full"
              :class="recognitionResult.status === 'high_confidence'
                ? 'bg-green-50 text-green-600' : 'bg-yellow-50 text-yellow-600'">
              {{ recognitionResult.status === 'high_confidence' ? '识别成功' : '需人工确认' }}
            </span>
            <span class="text-xs text-gray-400">
              置信度 {{ Math.round(recognitionResult.candidate.confidence * 100) }}%
            </span>
          </div>

          <div>
            <p class="text-xs text-gray-400 mb-1">题目内容</p>
            <p class="font-serif text-gray-800 text-sm leading-relaxed whitespace-pre-wrap">
              {{ recognitionResult.candidate.content }}
            </p>
          </div>
          <div>
            <p class="text-xs text-gray-400 mb-1">正确答案</p>
            <p class="text-sm text-green-700 font-medium">{{ recognitionResult.candidate.correct_answer }}</p>
          </div>
          <div v-if="recognitionResult.candidate.wrong_answer">
            <p class="text-xs text-gray-400 mb-1">我的错误</p>
            <p class="text-sm text-red-600">{{ recognitionResult.candidate.wrong_answer }}</p>
          </div>

          <div class="flex gap-3 pt-2">
            <button @click="previewUrl = null; recognitionResult = null"
              class="flex-1 py-2 border border-gray-300 rounded-lg text-sm text-gray-600 hover:bg-gray-50">
              重新拍摄
            </button>
            <button @click="onConfirm" :disabled="saving"
              class="flex-1 py-2 bg-primary-500 text-white rounded-lg text-sm font-medium
                     hover:bg-primary-600 disabled:opacity-60 transition-colors">
              {{ saving ? '保存中…' : '确认录入' }}
            </button>
          </div>
        </template>
      </div>
    </main>
  </div>
</template>
