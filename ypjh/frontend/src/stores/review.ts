import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { ReviewQueueItem, ReviewStats } from '@/types'

export const useReviewStore = defineStore('review', () => {
  const queue = ref<ReviewQueueItem[]>([])
  const stats = ref<ReviewStats>({ due_count: 0, reviewed_today: 0 })
  const currentIndex = ref(0)

  const current = () => queue.value[currentIndex.value] ?? null

  function advance() { currentIndex.value++ }
  function reset() { currentIndex.value = 0; queue.value = [] }

  return { queue, stats, currentIndex, current, advance, reset }
})
