import { apiClient } from '@/api/client'

export const printApi = {
  preview(questionIds: string[], options: { show_answer?: boolean; layout?: string }) {
    return apiClient.post(
      '/v1/print/preview',
      { question_ids: questionIds, ...options },
      { responseType: 'text' }
    )
  },
}
