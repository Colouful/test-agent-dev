import { ref } from 'vue'
import { useQuestionsStore } from '@/stores/questions'
import { IS_MOCK, mockQuestions } from '@/api/mock'
import { apiClient } from '@/api/client'
import type { RecognitionResult } from '@/types'

export function useQuestions() {
  const store = useQuestionsStore()
  const recognizing = ref(false)
  const recognitionResult = ref<RecognitionResult | null>(null)

  async function fetchList(limit = 20, offset = 0) {
    store.loading = true
    try {
      const resp = IS_MOCK
        ? await mockQuestions.list(limit, offset)
        : (await apiClient.get(`/v1/questions?limit=${limit}&offset=${offset}`)).data
      store.setList(resp.data.items, resp.data.total)
    } finally {
      store.loading = false
    }
  }

  async function recognize(file: File) {
    recognizing.value = true
    recognitionResult.value = null
    try {
      if (IS_MOCK) {
        const resp = await mockQuestions.recognize(file)
        recognitionResult.value = resp.data
      } else {
        const form = new FormData()
        form.append('image', file)
        const resp = await apiClient.post('/v1/questions/recognize', form)
        recognitionResult.value = resp.data.data
      }
    } finally {
      recognizing.value = false
    }
  }

  async function confirmAndSave(data: Parameters<typeof mockQuestions.create>[0]) {
    const resp = IS_MOCK
      ? await mockQuestions.create(data)
      : (await apiClient.post('/v1/questions', data)).data
    return resp.data
  }

  async function softDelete(id: string) {
    IS_MOCK
      ? await mockQuestions.softDelete(id)
      : await apiClient.delete(`/v1/questions/${id}`)
    store.removeById(id)
  }

  return { store, recognizing, recognitionResult, fetchList, recognize, confirmAndSave, softDelete }
}
