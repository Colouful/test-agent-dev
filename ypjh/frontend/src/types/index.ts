export interface User {
  id: string
  email: string
}

export interface AuthTokens {
  access_token: string
  token_type: string
}

export interface Question {
  id: string
  user_id: string
  content: string
  correct_answer: string
  wrong_answer: string | null
  subject: string | null
  question_type: string | null
  status: 'pending_review' | 'confirmed'
  confidence: number | null
  note: string | null
  image_url: string | null
  image_url_expires_at: string | null
  ease_factor: number
  interval_days: number
  review_count: number
  next_review_at: string | null
  created_at: string
  updated_at: string
}

export interface QuestionList {
  items: Question[]
  total: number
  limit: number
  offset: number
}

export interface RecognitionResult {
  status: 'high_confidence' | 'pending_review' | 'error'
  candidate: {
    content: string
    correct_answer: string
    wrong_answer: string | null
    confidence: number
    subject: string | null
    question_type: string | null
    image_key: string | null
  } | null
  error_hint: string | null
  error_code: string | null
}

export interface ReviewQueueItem {
  id: string
  content: string
  correct_answer: string
  subject: string | null
  question_type: string | null
  image_url: string | null
  ease_factor: number
  interval_days: number
  review_count: number
}

export interface ReviewQueue {
  items: ReviewQueueItem[]
  total: number
}

export interface ReviewStats {
  due_count: number
  reviewed_today: number
}

export interface ApiResponse<T> {
  data: T
  error: { code: string; message: string } | null
}
