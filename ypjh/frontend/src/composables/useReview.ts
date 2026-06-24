import { ref } from 'vue'
import { useReviewStore } from '@/stores/review'
import { IS_MOCK, mockReview } from '@/api/mock'
import { apiClient } from '@/api/client'

export function useReview() {
  const store = useReviewStore()
  const submitting = ref(false)

  async function fetchQueue() {
    const resp = IS_MOCK
      ? await mockReview.queue()
      : (await apiClient.get('/v1/review/queue')).data
    store.queue = resp.data.items
  }

  async function fetchStats() {
    const resp = IS_MOCK
      ? await mockReview.stats()
      : (await apiClient.get('/v1/review/stats')).data
    store.stats = resp.data
  }

  async function submitScore(questionId: string, score: number) {
    submitting.value = true
    try {
      IS_MOCK
        ? await mockReview.submitScore(questionId, score)
        : await apiClient.post(`/v1/review/${questionId}/score`, { score })
      store.advance()
    } finally {
      submitting.value = false
    }
  }

  return { store, submitting, fetchQueue, fetchStats, submitScore }
}
