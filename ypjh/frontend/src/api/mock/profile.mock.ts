import type { ApiResponse } from '@/types'

export const mockProfile = {
  async changePassword(
    _old: string,
    _new: string,
  ): Promise<ApiResponse<{ message: string }>> {
    await new Promise(r => setTimeout(r, 400))
    // mock 永远成功（不校验旧密码）
    return { data: { message: '密码已更新' }, error: null }
  },
}
