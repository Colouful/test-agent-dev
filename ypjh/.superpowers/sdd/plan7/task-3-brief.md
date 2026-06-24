# Task 3: Real API Endpoint Functions + Wire Composables

## Context
You are working on the 错题本 app at /workshop/ypjh. The frontend is a Vue 3 + Vite + TypeScript app at frontend/src/. The app already has:
- API client at frontend/src/api/client.ts (exports `apiClient`)
- Type definitions at frontend/src/types/index.ts (exports ApiResponse, AuthTokens, User, Question, QuestionList, RecognitionResult, ReviewQueue, ReviewStats)
- Composables at frontend/src/composables/useAuth.ts, useQuestions.ts, useReview.ts — these have mock branches and real API branches that currently call apiClient directly

This task creates typed endpoint modules and wires the composables to use them in their non-mock branches.

## What to do

### 1. Create `frontend/src/api/endpoints/auth.ts`:
```ts
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
```

### 2. Create `frontend/src/api/endpoints/questions.ts`:
```ts
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
}
```

### 3. Create `frontend/src/api/endpoints/review.ts`:
```ts
import { apiClient } from '@/api/client'
import type { ApiResponse, ReviewQueue, ReviewStats } from '@/types'

export const reviewApi = {
  queue() {
    return apiClient.get<ApiResponse<ReviewQueue>>('/v1/review/queue')
  },
  submitScore(questionId: string, score: number) {
    return apiClient.post(`/v1/review/${questionId}/score`, { score })
  },
  stats() {
    return apiClient.get<ApiResponse<ReviewStats>>('/v1/review/stats')
  },
}
```

### 4. Create `frontend/src/api/endpoints/print.ts`:
```ts
import { apiClient } from '@/api/client'

export const printApi = {
  preview(questionIds: string[], options: { show_answer?: boolean; layout?: string }) {
    return apiClient.post(
      '/v1/print/preview',
      { question_ids: questionIds, ...options },
      { responseType: 'text' }
    )
  },
}
```

### 5. Update `frontend/src/composables/useAuth.ts`

Read the file first. In the non-mock (real API) branches:
- Add import at top: `import { authApi } from '@/api/endpoints/auth'`
- In login(), replace the non-mock apiClient.post('/v1/auth/login', ...) call with: `(await authApi.login(email, password)).data`
- In register(), replace the non-mock apiClient.post('/v1/auth/register', ...) call with: `await authApi.register(email, password)`
- Remove the direct `apiClient` import if it's no longer used in this file

### 6. Update `frontend/src/composables/useQuestions.ts`

Read the file first. In the non-mock branches:
- Add import: `import { questionsApi } from '@/api/endpoints/questions'`
- In fetchList(), replace the apiClient.get call with: `(await questionsApi.list(limit, offset)).data`
- In recognize(), replace the apiClient.post call with: `(await questionsApi.recognize(file)).data`
- In confirmAndSave(), replace the apiClient.post call with: `(await questionsApi.create(data)).data`
- In softDelete(), replace the apiClient.delete call with: `await questionsApi.delete(id)`

### 7. Update `frontend/src/composables/useReview.ts`

Read the file first. In the non-mock branches:
- Add import: `import { reviewApi } from '@/api/endpoints/review'`
- In fetchQueue(), replace the apiClient.get call with: `(await reviewApi.queue()).data`
- In fetchStats(), replace the apiClient.get call with: `(await reviewApi.stats()).data`
- In submitScore(), replace the apiClient.post call with: `await reviewApi.submitScore(questionId, score)`

## Verification
1. Run: `cd /workshop/ypjh/frontend && npm run type-check` — must pass clean
2. Run: `cd /workshop/ypjh && uv run pytest backend/tests/ -q --tb=short` — must pass (75 tests)

## Commit
`git commit -m "feat: real API endpoint functions, wire composables to backend"`

## Report
Write your full report to: /workshop/ypjh/.superpowers/sdd/plan7/task-3-report.md

Return: status (DONE/DONE_WITH_CONCERNS/BLOCKED), commit hash, test summary (one line).
