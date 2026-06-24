import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Question } from '@/types'

export const useQuestionsStore = defineStore('questions', () => {
  const items = ref<Question[]>([])
  const total = ref(0)
  const loading = ref(false)

  function setList(questions: Question[], count: number) {
    items.value = questions
    total.value = count
  }

  function removeById(id: string) {
    items.value = items.value.filter(q => q.id !== id)
    total.value = Math.max(0, total.value - 1)
  }

  return { items, total, loading, setList, removeById }
})
