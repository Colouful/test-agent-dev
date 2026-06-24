import { apiClient } from '@/api/client'
import type { ApiResponse, ReviewQueue, ReviewStats } from '@/types'

export const reviewApi = {
  queue() {
    return apiClient.get<ApiResponse<ReviewQueue>>('/v1/review/queue')
  },
  submitScore(questionId: string, score: number) {
    return apiClient.post(`/v1/review/${questionId}/score`, { score })
  },
  stats() {
    return apiClient.get<ApiResponse<ReviewStats>>('/v1/review/stats')
  },
}
