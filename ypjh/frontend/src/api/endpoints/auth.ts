import { apiClient } from '@/api/client'
import type { ApiResponse, AuthTokens, User } from '@/types'

export const authApi = {
  login(email: string, password: string) {
    return apiClient.post<ApiResponse<AuthTokens & { user: User }>>('/v1/auth/login', { email, password })
  },
  register(email: string, password: string) {
    return apiClient.post<ApiResponse<User>>('/v1/auth/register', { email, password })
  },
  me() {
    return apiClient.get<ApiResponse<User>>('/v1/auth/me')
  },
}
