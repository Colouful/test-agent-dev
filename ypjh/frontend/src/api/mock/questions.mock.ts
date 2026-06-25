import type { ApiResponse, Analysis, Question, QuestionList, RecognitionResult } from '@/types'

let _idCounter = 1

const MOCK_ANALYSIS_RICH: Analysis = {
  solution_summary: '根据第二象限符号规则，sin>0 而 cos<0，用勾股定理求 cos',
  solution_steps: [
    { step: 1, title: '确定象限', content: 'θ∈(0,π) 且 sinθ>0，θ 在第一或第二象限' },
    { step: 2, title: '应用勾股', content: 'cos²θ=1-sin²θ=1-9/25=16/25' },
    { step: 3, title: '确定符号', content: 'θ 在第二象限，cosθ<0，取负值得 cosθ=-4/5' },
  ],
  knowledge_points: {
    core: ['三角函数', '第二象限符号'],
    prerequisite: ['勾股定理', '象限定义'],
    related: ['正弦定理', '余弦定理'],
  },
  key_examination: '考查三角函数在各象限的符号判断及勾股定理应用',
  error_analysis: {
    type: '条件遗漏',
    reason: '学生常忽略象限限制，直接取正值，未考虑 cos 在第二象限为负',
    improvement: ['判断三角函数值先确认角所在象限', '取平方根后根据象限确定正负号'],
  },
  common_mistakes: [
    '只应用勾股定理取正值，忽略象限符号',
    '将 θ∈(0,π) 理解为第一象限',
  ],
  practice_questions: [
    {
      content: '已知 cosα=-3/5，α∈(π/2, π)，求 sinα 的值。',
      answer: 'sinα=4/5',
      explanation: '第二象限 sin>0，由 sin²α=1-9/25=16/25，取正值得 4/5',
    },
  ],
}

const MOCK_RECOGNIZE_ANALYSIS: Analysis = {
  solution_summary: '将 x=2 代入 f(x)=2x²-3x+1，逐项计算后求和',
  solution_steps: [
    { step: 1, title: '代入 x=2', content: '将 x=2 代入，得 f(2)=2×4-3×2+1' },
    { step: 2, title: '逐项计算', content: '8-6+1=3，所以 f(2)=3' },
  ],
  knowledge_points: {
    core: ['二次函数求值', '代入法'],
    prerequisite: ['多项式运算'],
    related: ['函数定义域'],
  },
  key_examination: '考查多项式函数代入求值的计算能力',
  error_analysis: {
    type: '计算错误',
    reason: '常见错误是将 2x² 误算为 (2x)²=4x²，导致结果偏大',
    improvement: ['代入时逐项展开写清楚', '计算后代回原式验证'],
  },
  common_mistakes: [
    '将 2x² 错误展开为 (2x)²',
    '漏算常数项',
  ],
  practice_questions: [
    {
      content: '已知 g(x)=x²-4x+3，求 g(5) 的值。',
      answer: '8',
      explanation: '将 x=5 代入：25-20+3=8',
    },
  ],
}

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
    analysis: MOCK_ANALYSIS_RICH,
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
    analysis: null,
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
      analysis: data.analysis ?? null,
    }
    MOCK_QUESTIONS.push(q)
    return { data: q, error: null }
  },
  async recognize(_file: File): Promise<ApiResponse<RecognitionResult>> {
    await new Promise(r => setTimeout(r, 1200))
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
          analysis: MOCK_RECOGNIZE_ANALYSIS,
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
