<script setup lang="ts">
import { ref, watch } from 'vue'
import { IS_MOCK, mockQuestions } from '@/api/mock'
import { questionsApi } from '@/api/endpoints/questions'
import type { Question, RecognitionResult } from '@/types'

const props = defineProps<{
  visible: boolean
  candidate: RecognitionResult['candidate'] | null
}>()

const emit = defineEmits<{
  close: []
  saved: [question: Question]
}>()

const content = ref('')
const correctAnswer = ref('')
const wrongAnswer = ref('')
const subject = ref('')
const saving = ref(false)

const SUBJECTS = ['语文', '数学', '英语', '物理', '化学', '生物', '历史', '地理', '政治']

watch(() => props.candidate, (c) => {
  if (c) {
    content.value = c.content
    correctAnswer.value = c.correct_answer
    wrongAnswer.value = c.wrong_answer ?? ''
    subject.value = c.subject ?? ''
  }
}, { immediate: true })

async function onSave() {
  if (!props.candidate || saving.value) return
  saving.value = true
  try {
    const payload = {
      content: content.value,
      correct_answer: correctAnswer.value,
      wrong_answer: wrongAnswer.value || null,
      subject: subject.value || null,
      question_type: props.candidate.question_type ?? null,
      confidence: props.candidate.confidence,
      image_key: props.candidate.image_key ?? null,
      analysis: props.candidate.analysis ?? null,
    }
    let question: Question
    if (IS_MOCK) {
      const resp = await mockQuestions.create(payload)
      question = resp.data
    } else {
      const resp = await questionsApi.create(payload)
      question = resp.data.data
    }
    emit('saved', question)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <Teleport to="body">
    <Transition name="sheet">
      <div v-if="visible" class="fixed inset-0 z-50 flex flex-col justify-end">
        <!-- 遮罩 -->
        <div class="absolute inset-0 bg-black/40" />

        <!-- Sheet 主体 -->
        <div class="relative bg-white rounded-t-2xl max-h-[85vh] flex flex-col shadow-2xl">
          <!-- 拖拽条 -->
          <div class="flex justify-center pt-3 pb-1">
            <div class="w-10 h-1 bg-gray-300 rounded-full" />
          </div>

          <!-- 头部 -->
          <div class="flex items-center justify-between px-5 py-3 border-b border-gray-100">
            <div class="flex items-center gap-2">
              <span v-if="candidate && candidate.confidence >= 0.7"
                class="text-sm font-semibold text-gray-800">识别完成 ✓</span>
              <span v-else class="text-sm font-semibold text-yellow-700">⚠️ 识别置信度较低，请仔细检查</span>
              <span v-if="candidate"
                :class="['text-xs px-2 py-0.5 rounded-full', candidate.confidence >= 0.7
                  ? 'bg-green-50 text-green-600' : 'bg-yellow-50 text-yellow-700']">
                {{ Math.round((candidate.confidence) * 100) }}%
              </span>
            </div>
            <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600 text-xl leading-none">×</button>
          </div>

          <!-- 表单 -->
          <div class="overflow-y-auto flex-1 px-5 py-4 space-y-4">
            <div>
              <label class="text-xs text-gray-400 block mb-1">题目内容</label>
              <textarea v-model="content" rows="4"
                class="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm
                       text-gray-800 resize-none focus:outline-none focus:ring-2 focus:ring-primary-300" />
            </div>
            <div>
              <label class="text-xs text-gray-400 block mb-1">正确答案</label>
              <input v-model="correctAnswer" type="text"
                class="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm
                       focus:outline-none focus:ring-2 focus:ring-primary-300" />
            </div>
            <div>
              <label class="text-xs text-gray-400 block mb-1">我的错误答案（选填）</label>
              <input v-model="wrongAnswer" type="text" placeholder="留空跳过"
                class="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm
                       text-gray-400 placeholder-gray-300 focus:outline-none focus:ring-2 focus:ring-primary-300" />
            </div>
            <div>
              <label class="text-xs text-gray-400 block mb-1">学科</label>
              <select v-model="subject"
                class="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm
                       focus:outline-none focus:ring-2 focus:ring-primary-300 bg-white">
                <option value="">不确定</option>
                <option v-for="s in SUBJECTS" :key="s" :value="s">{{ s }}</option>
              </select>
            </div>
          </div>

          <!-- 底部按钮 -->
          <div class="px-5 py-4 border-t border-gray-100">
            <button @click="onSave" :disabled="saving || !content || !correctAnswer"
              class="w-full py-3.5 bg-primary-500 text-white rounded-xl font-semibold text-sm
                     hover:bg-primary-600 disabled:opacity-50 transition-colors">
              {{ saving ? '保存中…' : (candidate && candidate.confidence < 0.7 ? '确认并保存' : '保存到错题本') }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.sheet-enter-active,
.sheet-leave-active {
  transition: all 0.3s ease;
}
.sheet-enter-from .relative,
.sheet-leave-to .relative {
  transform: translateY(100%);
}
.sheet-enter-from .absolute,
.sheet-leave-to .absolute {
  opacity: 0;
}
</style>
