<!-- frontend/src/components/QuestionCard.vue -->
<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useKatex } from '@/composables/useKatex'
import type { Question } from '@/types'

const props = defineProps<{ question: Question; showAnswer?: boolean }>()
defineEmits<{ delete: [id: string] }>()

const router = useRouter()
const container = ref<HTMLElement | null>(null)
useKatex(container)

function goToDetail() {
  router.push(`/questions/${props.question.id}`)
}
</script>

<template>
  <div
    ref="container"
    @click="goToDetail"
    class="bg-white rounded-xl shadow-sm border border-gray-100 p-5
           hover:shadow-md hover:border-primary-200 transition-all cursor-pointer
           active:scale-[0.98]"
  >
    <div class="flex items-center justify-between mb-3">
      <div class="flex gap-2">
        <span v-if="question.subject"
          class="text-xs px-2 py-0.5 rounded-full bg-blue-50 text-blue-600 font-medium">
          {{ question.subject }}
        </span>
        <span :class="[
          'text-xs px-2 py-0.5 rounded-full font-medium',
          question.status === 'confirmed' ? 'bg-green-50 text-green-600' : 'bg-yellow-50 text-yellow-600'
        ]">
          {{ question.status === 'confirmed' ? '已确认' : '待确认' }}
        </span>
      </div>
      <button
        @click.stop="$emit('delete', question.id)"
        class="text-gray-300 hover:text-red-400 transition-colors text-xs px-2 py-1 -mr-1"
      >
        删除
      </button>
    </div>

    <div v-if="question.image_url" class="mb-3">
      <img :src="question.image_url" alt="题目图片"
        class="w-full h-36 object-cover rounded-lg border border-gray-100" loading="lazy">
    </div>

    <p class="font-serif text-gray-800 text-base leading-relaxed mb-3 whitespace-pre-wrap line-clamp-3">
      {{ question.content }}
    </p>

    <template v-if="showAnswer !== false">
      <div class="border-t border-dashed border-gray-200 pt-3 mt-3 space-y-2">
        <div>
          <p class="text-xs text-gray-400 mb-1">正确答案</p>
          <p class="text-sm text-green-700 font-medium">{{ question.correct_answer }}</p>
        </div>
        <div v-if="question.wrong_answer">
          <p class="text-xs text-gray-400 mb-1">我的错误</p>
          <p class="text-sm text-red-600">{{ question.wrong_answer }}</p>
        </div>
        <div v-if="question.note">
          <p class="text-xs text-gray-400 mb-1">笔记</p>
          <p class="text-sm text-gray-600 italic">{{ question.note }}</p>
        </div>
      </div>
    </template>

    <div class="mt-3 flex items-center justify-end">
      <span class="text-xs text-gray-300">查看详情 →</span>
    </div>
  </div>
</template>
