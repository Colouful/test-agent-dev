import type { ApiResponse, ReviewQueue, ReviewStats } from '@/types'

export const mockReview = {
  async queue(): Promise<ApiResponse<ReviewQueue>> {
    await new Promise(r => setTimeout(r, 300))
    return {
      data: {
        items: [
          { id: 'q-1', content: '已知 $\\sin\\theta = \\dfrac{3}{5}$，求 $\\cos\\theta$。',
            correct_answer: '$\\cos\\theta = \\pm\\dfrac{4}{5}$',
            subject: '数学', question_type: 'fill',
            image_url: null, ease_factor: 2.5, interval_days: 1, review_count: 0 },
        ],
        total: 1,
      },
      error: null,
    }
  },
  async submitScore(questionId: string, score: number): Promise<ApiResponse<{
    question_id: string; score: number; new_ease_factor: number;
    new_interval_days: number; new_review_count: number; next_review_at: string
  }>> {
    await new Promise(r => setTimeout(r, 400))
    return {
      data: {
        question_id: questionId,
        score,
        new_ease_factor: score >= 3 ? 2.5 + (score - 3) * 0.1 : 2.5,
        new_interval_days: score >= 3 ? 6 : 1,
        new_review_count: score >= 3 ? 1 : 0,
        next_review_at: new Date(Date.now() + 86400000 * (score >= 3 ? 6 : 1)).toISOString(),
      },
      error: null,
    }
  },
  async stats(): Promise<ApiResponse<ReviewStats>> {
    return { data: { due_count: 3, reviewed_today: 7, pending_correction_count: 2 }, error: null }
  },
}
