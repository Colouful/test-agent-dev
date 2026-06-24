import type { ApiResponse } from '@/types'

export const mockPrint = {
  async preview(_questionIds: string[], _options: object): Promise<ApiResponse<{ html: string }>> {
    await new Promise(r => setTimeout(r, 500))
    return {
      data: {
        html: `<html><body><h1>打印预览（Mock）</h1><p>共选择 ${_questionIds.length} 道题</p></body></html>`,
      },
      error: null,
    }
  },
}
