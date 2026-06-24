import type { ApiResponse, Question, QuestionList, RecognitionResult } from '@/types'

let _idCounter = 1

const MOCK_QUESTIONS: Question[] = [
  {
    id: 'q-1', user_id: 'mock-user-1',
    content: '已知 $\\sin\\theta = \\dfrac{3}{5}$，$\\theta \\in (0, \\pi)$，求 $\\cos\\theta$。',
    correct_answer: '$\\cos\\theta = -\\dfrac{4}{5}$',
    wrong_answer: '$\\cos\\theta = \\dfrac{4}{5}$（忽略了第二象限余弦为负）',
    subject: '数学', question_type: 'fill',
    status: 'confirmed', confidence: 0.92,
    note: '第二象限：sin > 0，cos < 0',
    image_url: null, image_url_expires_at: null,
    ease_factor: 2.5, interval_days: 1, review_count: 0,
    next_review_at: new Date(Date.now() - 86400000).toISOString(),
    created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
  },
  {
    id: 'q-2', user_id: 'mock-user-1',
    content: 'The Industrial Revolution began in which country?\nA. France  B. United States  C. Germany  D. Britain',
    correct_answer: 'D. Britain',
    wrong_answer: 'A. France',
    subject: '英语', question_type: 'single',
    status: 'confirmed', confidence: 0.85,
    note: null, image_url: null, image_url_expires_at: null,
    ease_factor: 2.6, interval_days: 3, review_count: 1,
    next_review_at: new Date(Date.now() + 86400000 * 2).toISOString(),
    created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
  },
]

export const mockQuestions = {
  async list(limit = 20, offset = 0): Promise<ApiResponse<QuestionList>> {
    await new Promise(r => setTimeout(r, 300))
    const items = MOCK_QUESTIONS.slice(offset, offset + limit)
    return { data: { items, total: MOCK_QUESTIONS.length, limit, offset }, error: null }
  },
  async get(id: string): Promise<ApiResponse<Question>> {
    const q = MOCK_QUESTIONS.find(q => q.id === id)
    if (!q) return { data: null as unknown as Question, error: { code: 'NOT_FOUND', message: '题目不存在' } }
    return { data: q, error: null }
  },
  async create(data: Partial<Question>): Promise<ApiResponse<Question>> {
    await new Promise(r => setTimeout(r, 300))
    const q: Question = {
      id: `q-new-${++_idCounter}`,
      user_id: 'mock-user-1',
      content: data.content ?? '',
      correct_answer: data.correct_answer ?? '',
      wrong_answer: data.wrong_answer ?? null,
      subject: data.subject ?? null,
      question_type: data.question_type ?? null,
      status: 'confirmed',
      confidence: data.confidence ?? null,
      note: null, image_url: null, image_url_expires_at: null,
      ease_factor: 2.5, interval_days: 1, review_count: 0,
      next_review_at: new Date(Date.now() + 86400000).toISOString(),
      created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
    }
    MOCK_QUESTIONS.push(q)
    return { data: q, error: null }
  },
  async recognize(_file: File): Promise<ApiResponse<RecognitionResult>> {
    await new Promise(r => setTimeout(r, 1200))  // 模拟识别延迟
    return {
      data: {
        status: 'high_confidence',
        candidate: {
          content: '已知函数 $f(x) = 2x^2 - 3x + 1$，求 $f(2)$。',
          correct_answer: '$f(2) = 2(4) - 6 + 1 = 3$',
          wrong_answer: '学生计算得 $f(2) = 8 - 3 + 1 = 6$（未正确展开 $2x^2$）',
          confidence: 0.88,
          subject: '数学',
          question_type: 'fill',
          image_key: null,
        },
        error_hint: null,
        error_code: null,
      },
      error: null,
    }
  },
  async softDelete(_id: string): Promise<ApiResponse<null>> {
    await new Promise(r => setTimeout(r, 200))
    return { data: null, error: null }
  },
}
