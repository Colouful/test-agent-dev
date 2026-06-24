import type { ApiResponse, AuthTokens, User } from '@/types'

const MOCK_USER: User = { id: 'mock-user-1', email: 'demo@wrongbook.app' }

export const mockAuth = {
  async login(_email: string, _password: string): Promise<ApiResponse<AuthTokens & { user: User }>> {
    await new Promise((r) => setTimeout(r, 400)) // 模拟网络延迟
    return {
      data: { access_token: 'mock-jwt-token', token_type: 'bearer', user: MOCK_USER },
      error: null,
    }
  },
  async register(_email: string, _password: string): Promise<ApiResponse<User>> {
    await new Promise((r) => setTimeout(r, 400))
    return { data: MOCK_USER, error: null }
  },
  async me(): Promise<ApiResponse<User>> {
    return { data: MOCK_USER, error: null }
  },
}
