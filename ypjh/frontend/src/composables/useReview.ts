import { ref } from 'vue'
import { useReviewStore } from '@/stores/review'
import { IS_MOCK, mockReview } from '@/api/mock'
import { reviewApi } from '@/api/endpoints/review'

export function useReview() {
  const store = useReviewStore()
  const submitting = ref(false)
  const loading = ref(false)

  async function fetchQueue() {
    loading.value = true
    store.reset()
    try {
      const resp = IS_MOCK
        ? await mockReview.queue()
        : (await reviewApi.queue()).data
      store.queue = resp.data.items
    } finally {
      loading.value = false
    }
  }

  async function fetchStats() {
    const resp = IS_MOCK
      ? await mockReview.stats()
      : (await reviewApi.stats()).data
    store.stats = resp.data
  }

  async function submitScore(questionId: string, score: number) {
    submitting.value = true
    try {
      IS_MOCK
        ? await mockReview.submitScore(questionId, score)
        : await reviewApi.submitScore(questionId, score)
      store.advance()
    } finally {
      submitting.value = false
    }
  }

  return { store, submitting, loading, fetchQueue, fetchStats, submitScore }
}
