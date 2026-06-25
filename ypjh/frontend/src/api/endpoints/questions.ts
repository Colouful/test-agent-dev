import { apiClient } from '@/api/client'
import type { ApiResponse, Question, QuestionList, RecognitionResult } from '@/types'

export const questionsApi = {
  list(limit = 20, offset = 0) {
    return apiClient.get<ApiResponse<QuestionList>>(`/v1/questions?limit=${limit}&offset=${offset}`)
  },
  get(id: string) {
    return apiClient.get<ApiResponse<Question>>(`/v1/questions/${id}`)
  },
  create(data: Partial<Question>) {
    return apiClient.post<ApiResponse<Question>>('/v1/questions', data)
  },
  update(id: string, data: Partial<Question>) {
    return apiClient.patch<ApiResponse<Question>>(`/v1/questions/${id}`, data)
  },
  delete(id: string) {
    return apiClient.delete(`/v1/questions/${id}`)
  },
  recognize(file: File) {
    const form = new FormData()
    form.append('image', file)
    return apiClient.post<ApiResponse<RecognitionResult>>('/v1/questions/recognize', form)
  },
  setErrorType: (id: string, userErrorType: string) =>
    apiClient.patch<ApiResponse<Question>>(`/v1/questions/${id}/error-type`, { user_error_type: userErrorType }),

  setLearningStatus: (id: string, learningStatus: string) =>
    apiClient.patch<ApiResponse<Question>>(`/v1/questions/${id}/learning-status`, { learning_status: learningStatus }),
}
