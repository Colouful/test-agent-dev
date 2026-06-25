import { apiClient } from '@/api/client'
import type { ApiResponse } from '@/types'

export const profileApi = {
  changePassword(old_password: string, new_password: string) {
    return apiClient.patch<ApiResponse<{ message: string }>>('/v1/auth/password', {
      old_password,
      new_password,
    })
  },
}
