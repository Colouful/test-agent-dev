# 错题本 Plan 6：前端 Vue 3（Mock 阶段）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 搭建完整 Vue 3 前端应用，全部使用 mock 数据（`VITE_MOCK=true`），覆盖 7 条路由对应的所有页面。界面需达到生产级视觉质量：统一设计系统、清晰的中文排版、触手可及的交互反馈。

**Architecture:** Pinia 状态管理 + Composable 数据获取层 + Mock Service（`src/api/mock/`）。组件不直接调 API，通过 Composable 获取数据。`VITE_MOCK=true` 时全部 API 调用由 mock 模块拦截。

**Tech Stack:** Vue 3.4+, TypeScript 5, Vite 5, Pinia 2, Vue Router 4, Tailwind CSS 3（设计系统）, KaTeX（公式渲染）, VueUse（工具集）

## UI/UX 设计规范（适用于所有前端 Task）

### 设计系统（Tailwind 配置）
- 主色 `primary`: `#1976d2`（教育蓝）；成功 `#2e7d32`；警告 `#ed6c02`；错误 `#d32f2f`
- 文字：标题 `text-gray-900`，正文 `text-gray-700`，辅助 `text-gray-400`
- 圆角：卡片 `rounded-xl`，按钮 `rounded-lg`，输入框 `rounded-lg`
- 阴影：卡片 `shadow-sm`，悬停 `shadow-md`
- 所有可交互元素必须有 focus ring（`focus:ring-2 focus:ring-primary-500`）

### 交互质量规范
- 每个异步操作配 loading skeleton 或 spinner（不许裸白屏）
- 表单提交时按钮 disabled + 显示"提交中..."
- 错误状态用 toast（右下角，3s 自动消失）而非 alert()
- 路由跳转使用 Vue Router，不用 `location.href`
- 所有输入框带 `placeholder`，选填字段标注"（选填）"
- 手机屏幕优先（`sm:`/`md:` 响应式扩展）

### 中文排版
- 正文：16px / `leading-relaxed`（行高 1.625）
- 题目内容：`font-serif`（宋体/衬线）提高阅读感
- 数学公式必须 KaTeX 渲染（`$...$` 内联，`$$...$$` 块级）
- 中英文混排：用 CSS `letter-spacing` 而非空格

---

## 文件结构

```
frontend/src/
├── api/
│   ├── client.ts              # Axios 实例（含 JWT 拦截）
│   ├── mock/
│   │   ├── index.ts           # mock 路由分发
│   │   ├── auth.mock.ts
│   │   ├── questions.mock.ts
│   │   ├── review.mock.ts
│   │   └── print.mock.ts
│   └── endpoints/
│       ├── auth.ts
│       ├── questions.ts
│       ├── review.ts
│       └── print.ts
├── stores/
│   ├── auth.ts                # Pinia: token, currentUser
│   ├── questions.ts           # Pinia: 题目列表
│   └── review.ts              # Pinia: 复习队列
├── composables/
│   ├── useAuth.ts
│   ├── useQuestions.ts
│   ├── useReview.ts
│   ├── usePrint.ts
│   └── useKatex.ts
├── components/
│   ├── AppToast.vue           # 全局 toast
│   ├── QuestionCard.vue
│   ├── ReviewScoreButtons.vue # 5级评分按钮
│   ├── ImageUpload.vue
│   └── SkeletonCard.vue
├── pages/
│   ├── LoginPage.vue
│   ├── RegisterPage.vue
│   ├── DashboardPage.vue
│   ├── UploadPage.vue
│   ├── QuestionListPage.vue
│   ├── ReviewPage.vue
│   └── PrintPage.vue
├── types/
│   └── index.ts               # 全局 TypeScript 类型
├── router/
│   └── index.ts               # 7 条路由（含 auth guard）
└── App.vue
```

---

### Task 1：项目初始化 + 设计系统

**Files:**
- Modify: `frontend/package.json`（添加依赖）
- Modify: `frontend/tailwind.config.ts`（主题扩展）
- Create: `frontend/src/types/index.ts`
- Create: `frontend/src/router/index.ts`

- [ ] **Step 1: 安装依赖**

```bash
cd /workshop/ypjh/frontend
npm install tailwindcss @tailwindcss/typography postcss autoprefixer
npm install pinia vue-router@4 axios vueuse katex
npm install -D @types/katex
npx tailwindcss init -p
```

- [ ] **Step 2: 配置 tailwind.config.ts**

```ts
// frontend/tailwind.config.ts
import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{vue,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#e3f2fd', 100: '#bbdefb', 200: '#90caf9',
          300: '#64b5f6', 400: '#42a5f5', 500: '#1976d2',
          600: '#1565c0', 700: '#0d47a1', 800: '#0a3880',
          900: '#071e56',
        },
      },
      fontFamily: {
        serif: ['"Noto Serif SC"', '"Source Han Serif"', 'SimSun', 'serif'],
        sans:  ['"Noto Sans SC"', '"PingFang SC"', 'sans-serif'],
      },
    },
  },
  plugins: [require('@tailwindcss/typography')],
} satisfies Config
```

- [ ] **Step 3: 更新 src/main.ts 注册 Pinia**

```ts
// frontend/src/main.ts
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './assets/main.css'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')
```

- [ ] **Step 4: 添加 Tailwind 到 main.css**

```css
/* frontend/src/assets/main.css */
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  body { @apply font-sans text-gray-700 bg-gray-50; }
  h1, h2, h3 { @apply font-bold text-gray-900; }
}
```

- [ ] **Step 5: 定义全局 TypeScript 类型**

```ts
// frontend/src/types/index.ts
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
```

- [ ] **Step 6: 配置路由**

```ts
// frontend/src/router/index.ts
import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: () => import('@/pages/LoginPage.vue'), meta: { public: true } },
    { path: '/register', component: () => import('@/pages/RegisterPage.vue'), meta: { public: true } },
    { path: '/', redirect: '/dashboard' },
    { path: '/dashboard', component: () => import('@/pages/DashboardPage.vue') },
    { path: '/upload', component: () => import('@/pages/UploadPage.vue') },
    { path: '/questions', component: () => import('@/pages/QuestionListPage.vue') },
    { path: '/review', component: () => import('@/pages/ReviewPage.vue') },
    { path: '/print', component: () => import('@/pages/PrintPage.vue') },
  ],
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (!to.meta.public && !auth.token) {
    return '/login'
  }
})

export default router
```

- [ ] **Step 7: Commit**

```bash
cd /workshop/ypjh/frontend
git add src/main.ts src/router/ src/types/ src/assets/main.css tailwind.config.ts
git commit -m "feat: frontend setup with Tailwind design system, Pinia, Vue Router (REQ-F1)"
```

---

### Task 2：Auth Store + Mock API + Axios Client

**Files:**
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/api/mock/auth.mock.ts`
- Create: `frontend/src/api/mock/index.ts`
- Create: `frontend/src/stores/auth.ts`
- Create: `frontend/src/composables/useAuth.ts`

- [ ] **Step 1: Axios Client（含 JWT 拦截器）**

```ts
// frontend/src/api/client.ts
import axios from 'axios'

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 30_000,
})

// 请求拦截：注入 JWT（R7 约定：组件不直接知道 token 存哪）
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// 响应拦截：401 → 清除 token 并跳转登录
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)
```

- [ ] **Step 2: Auth Mock**

```ts
// frontend/src/api/mock/auth.mock.ts
import type { ApiResponse, AuthTokens, User } from '@/types'

const MOCK_USER: User = { id: 'mock-user-1', email: 'demo@wrongbook.app' }

export const mockAuth = {
  async login(_email: string, _password: string): Promise<ApiResponse<AuthTokens & { user: User }>> {
    await new Promise(r => setTimeout(r, 400))  // 模拟网络延迟
    return {
      data: { access_token: 'mock-jwt-token', token_type: 'bearer', user: MOCK_USER },
      error: null,
    }
  },
  async register(_email: string, _password: string): Promise<ApiResponse<User>> {
    await new Promise(r => setTimeout(r, 400))
    return { data: MOCK_USER, error: null }
  },
  async me(): Promise<ApiResponse<User>> {
    return { data: MOCK_USER, error: null }
  },
}
```

- [ ] **Step 3: Mock 路由分发**

```ts
// frontend/src/api/mock/index.ts
export { mockAuth } from './auth.mock'
export { mockQuestions } from './questions.mock'
export { mockReview } from './review.mock'
export { mockPrint } from './print.mock'

export const IS_MOCK = import.meta.env.VITE_MOCK === 'true'
```

- [ ] **Step 4: Auth Store**

```ts
// frontend/src/stores/auth.ts
import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { User } from '@/types'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('access_token'))
  const user = ref<User | null>(null)

  function setToken(t: string) {
    token.value = t
    localStorage.setItem('access_token', t)
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem('access_token')
  }

  return { token, user, setToken, logout }
})
```

- [ ] **Step 5: useAuth Composable**

```ts
// frontend/src/composables/useAuth.ts
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { IS_MOCK, mockAuth } from '@/api/mock'
import { apiClient } from '@/api/client'

export function useAuth() {
  const auth = useAuthStore()
  const router = useRouter()
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function login(email: string, password: string) {
    loading.value = true
    error.value = null
    try {
      const resp = IS_MOCK
        ? await mockAuth.login(email, password)
        : (await apiClient.post('/v1/auth/login', { email, password })).data
      auth.setToken(resp.data.access_token)
      if (resp.data.user) auth.user = resp.data.user
      router.push('/dashboard')
    } catch (e: unknown) {
      error.value = (e as Error).message || '登录失败，请检查邮箱和密码'
    } finally {
      loading.value = false
    }
  }

  async function register(email: string, password: string) {
    loading.value = true
    error.value = null
    try {
      IS_MOCK
        ? await mockAuth.register(email, password)
        : await apiClient.post('/v1/auth/register', { email, password })
      await login(email, password)
    } catch (e: unknown) {
      error.value = (e as Error).message || '注册失败'
    } finally {
      loading.value = false
    }
  }

  function logout() {
    auth.logout()
    router.push('/login')
  }

  return { loading, error, login, register, logout }
}
```

- [ ] **Step 6: Vitest 测试**

```ts
// frontend/src/composables/__tests__/useAuth.test.ts
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from '@/stores/auth'

describe('useAuthStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
  })

  it('starts with null token', () => {
    const store = useAuthStore()
    expect(store.token).toBeNull()
  })

  it('setToken persists to localStorage', () => {
    const store = useAuthStore()
    store.setToken('test-jwt')
    expect(store.token).toBe('test-jwt')
    expect(localStorage.getItem('access_token')).toBe('test-jwt')
  })

  it('logout clears token and localStorage', () => {
    const store = useAuthStore()
    store.setToken('test-jwt')
    store.logout()
    expect(store.token).toBeNull()
    expect(localStorage.getItem('access_token')).toBeNull()
  })
})
```

- [ ] **Step 7: 运行 Vitest**

```bash
cd /workshop/ypjh/frontend && npm run test -- --run
```

Expected: `3 passed`

- [ ] **Step 8: Commit**

```bash
git add src/api/ src/stores/auth.ts src/composables/useAuth.ts src/composables/__tests__/
git commit -m "feat: auth store, mock API, Axios JWT interceptor"
```

---

### Task 3：题目 Mock + Store + Composable

**Files:**
- Create: `frontend/src/api/mock/questions.mock.ts`
- Create: `frontend/src/stores/questions.ts`
- Create: `frontend/src/composables/useQuestions.ts`

- [ ] **Step 1: Questions Mock（含识别场景）**

```ts
// frontend/src/api/mock/questions.mock.ts
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
```

- [ ] **Step 2: Questions Store**

```ts
// frontend/src/stores/questions.ts
import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Question } from '@/types'

export const useQuestionsStore = defineStore('questions', () => {
  const items = ref<Question[]>([])
  const total = ref(0)
  const loading = ref(false)

  function setList(questions: Question[], count: number) {
    items.value = questions
    total.value = count
  }

  function removeById(id: string) {
    items.value = items.value.filter(q => q.id !== id)
    total.value = Math.max(0, total.value - 1)
  }

  return { items, total, loading, setList, removeById }
})
```

- [ ] **Step 3: useQuestions Composable**

```ts
// frontend/src/composables/useQuestions.ts
import { ref } from 'vue'
import { useQuestionsStore } from '@/stores/questions'
import { IS_MOCK, mockQuestions } from '@/api/mock'
import { apiClient } from '@/api/client'
import type { RecognitionResult } from '@/types'

export function useQuestions() {
  const store = useQuestionsStore()
  const recognizing = ref(false)
  const recognitionResult = ref<RecognitionResult | null>(null)

  async function fetchList(limit = 20, offset = 0) {
    store.loading = true
    try {
      const resp = IS_MOCK
        ? await mockQuestions.list(limit, offset)
        : (await apiClient.get(`/v1/questions?limit=${limit}&offset=${offset}`)).data
      store.setList(resp.data.items, resp.data.total)
    } finally {
      store.loading = false
    }
  }

  async function recognize(file: File) {
    recognizing.value = true
    recognitionResult.value = null
    try {
      if (IS_MOCK) {
        const resp = await mockQuestions.recognize(file)
        recognitionResult.value = resp.data
      } else {
        const form = new FormData()
        form.append('image', file)
        const resp = await apiClient.post('/v1/questions/recognize', form)
        recognitionResult.value = resp.data.data
      }
    } finally {
      recognizing.value = false
    }
  }

  async function confirmAndSave(data: Parameters<typeof mockQuestions.create>[0]) {
    const resp = IS_MOCK
      ? await mockQuestions.create(data)
      : (await apiClient.post('/v1/questions', data)).data
    return resp.data
  }

  async function softDelete(id: string) {
    IS_MOCK
      ? await mockQuestions.softDelete(id)
      : await apiClient.delete(`/v1/questions/${id}`)
    store.removeById(id)
  }

  return { store, recognizing, recognitionResult, fetchList, recognize, confirmAndSave, softDelete }
}
```

- [ ] **Step 4: Vitest 测试**

```ts
// frontend/src/composables/__tests__/useQuestions.test.ts
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useQuestionsStore } from '@/stores/questions'

describe('useQuestionsStore', () => {
  beforeEach(() => { setActivePinia(createPinia()) })

  it('setList updates items and total', () => {
    const store = useQuestionsStore()
    const fakeQ = [{ id: '1', content: '题目', correct_answer: '答案' }] as never[]
    store.setList(fakeQ, 1)
    expect(store.items.length).toBe(1)
    expect(store.total).toBe(1)
  })

  it('removeById removes item and decrements total', () => {
    const store = useQuestionsStore()
    const fakeQ = [{ id: 'q1' }, { id: 'q2' }] as never[]
    store.setList(fakeQ, 2)
    store.removeById('q1')
    expect(store.items.length).toBe(1)
    expect(store.total).toBe(1)
  })
})
```

- [ ] **Step 5: 运行测试**

```bash
cd /workshop/ypjh/frontend && npm run test -- --run
```

Expected: `5 passed`（含之前 auth 3条）

- [ ] **Step 6: Commit**

```bash
git add src/api/mock/ src/stores/questions.ts src/composables/useQuestions.ts
git commit -m "feat: questions mock, store, useQuestions composable with recognize support"
```

---

### Task 4：复习 Mock + Store + Composable

**Files:**
- Create: `frontend/src/api/mock/review.mock.ts`
- Create: `frontend/src/api/mock/print.mock.ts`
- Create: `frontend/src/stores/review.ts`
- Create: `frontend/src/composables/useReview.ts`

- [ ] **Step 1: Review + Print Mock**

```ts
// frontend/src/api/mock/review.mock.ts
import type { ApiResponse, ReviewQueue, ReviewStats } from '@/types'

export const mockReview = {
  async queue(): Promise<ApiResponse<ReviewQueue>> {
    await new Promise(r => setTimeout(r, 300))
    return {
      data: {
        items: [
          { id: 'q-1', content: '已知 $\\sin\\theta = \\dfrac{3}{5}$，求 $\\cos\\theta$。',
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
    return { data: { due_count: 3, reviewed_today: 7 }, error: null }
  },
}
```

```ts
// frontend/src/api/mock/print.mock.ts
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
```

- [ ] **Step 2: Review Store + useReview**

```ts
// frontend/src/stores/review.ts
import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { ReviewQueueItem, ReviewStats } from '@/types'

export const useReviewStore = defineStore('review', () => {
  const queue = ref<ReviewQueueItem[]>([])
  const stats = ref<ReviewStats>({ due_count: 0, reviewed_today: 0 })
  const currentIndex = ref(0)

  const current = () => queue.value[currentIndex.value] ?? null

  function advance() { currentIndex.value++ }
  function reset() { currentIndex.value = 0; queue.value = [] }

  return { queue, stats, currentIndex, current, advance, reset }
})
```

```ts
// frontend/src/composables/useReview.ts
import { ref } from 'vue'
import { useReviewStore } from '@/stores/review'
import { IS_MOCK, mockReview } from '@/api/mock'
import { apiClient } from '@/api/client'

export function useReview() {
  const store = useReviewStore()
  const submitting = ref(false)

  async function fetchQueue() {
    const resp = IS_MOCK
      ? await mockReview.queue()
      : (await apiClient.get('/v1/review/queue')).data
    store.queue = resp.data.items
  }

  async function fetchStats() {
    const resp = IS_MOCK
      ? await mockReview.stats()
      : (await apiClient.get('/v1/review/stats')).data
    store.stats = resp.data
  }

  async function submitScore(questionId: string, score: number) {
    submitting.value = true
    try {
      IS_MOCK
        ? await mockReview.submitScore(questionId, score)
        : await apiClient.post(`/v1/review/${questionId}/score`, { score })
      store.advance()
    } finally {
      submitting.value = false
    }
  }

  return { store, submitting, fetchQueue, fetchStats, submitScore }
}
```

- [ ] **Step 3: Commit**

```bash
git add src/api/mock/review.mock.ts src/api/mock/print.mock.ts src/stores/review.ts src/composables/useReview.ts
git commit -m "feat: review/print mock, review store and composable"
```

---

### Task 5：全局组件（Toast、KaTeX、Skeleton）

**Files:**
- Create: `frontend/src/components/AppToast.vue`
- Create: `frontend/src/components/SkeletonCard.vue`
- Create: `frontend/src/components/QuestionCard.vue`
- Create: `frontend/src/components/ReviewScoreButtons.vue`
- Create: `frontend/src/composables/useKatex.ts`
- Modify: `frontend/src/App.vue`

- [ ] **Step 1: AppToast.vue（右下角，3s 消失）**

```vue
<!-- frontend/src/components/AppToast.vue -->
<script setup lang="ts">
import { ref } from 'vue'

export interface ToastMessage { id: number; type: 'success' | 'error' | 'info'; text: string }

const messages = ref<ToastMessage[]>([])
let _id = 0

function show(text: string, type: ToastMessage['type'] = 'info') {
  const id = ++_id
  messages.value.push({ id, type, text })
  setTimeout(() => { messages.value = messages.value.filter(m => m.id !== id) }, 3000)
}

defineExpose({ show })
</script>

<template>
  <div class="fixed bottom-4 right-4 z-50 flex flex-col gap-2 items-end">
    <TransitionGroup name="toast">
      <div v-for="msg in messages" :key="msg.id"
        :class="[
          'px-4 py-3 rounded-lg shadow-lg text-sm text-white max-w-xs',
          msg.type === 'success' ? 'bg-green-600' :
          msg.type === 'error'   ? 'bg-red-600'   : 'bg-gray-700'
        ]">
        {{ msg.text }}
      </div>
    </TransitionGroup>
  </div>
</template>

<style scoped>
.toast-enter-active { transition: all .25s ease-out; }
.toast-leave-active { transition: all .2s ease-in; }
.toast-enter-from, .toast-leave-to { opacity: 0; transform: translateY(8px); }
</style>
```

- [ ] **Step 2: SkeletonCard.vue（loading 占位）**

```vue
<!-- frontend/src/components/SkeletonCard.vue -->
<script setup lang="ts">
defineProps<{ lines?: number }>()
</script>

<template>
  <div class="bg-white rounded-xl shadow-sm p-5 animate-pulse">
    <div class="h-3 bg-gray-200 rounded w-1/4 mb-3"></div>
    <div v-for="i in (lines ?? 3)" :key="i" class="mb-2">
      <div :class="['h-2.5 bg-gray-200 rounded', i === (lines ?? 3) ? 'w-3/4' : 'w-full']"></div>
    </div>
  </div>
</template>
```

- [ ] **Step 3: useKatex Composable**

```ts
// frontend/src/composables/useKatex.ts
import { onMounted, onUpdated, type Ref } from 'vue'

export function useKatex(containerRef: Ref<HTMLElement | null>) {
  function renderMath() {
    if (!containerRef.value) return
    import('katex/contrib/auto-render').then(({ default: renderMathInElement }) => {
      if (!containerRef.value) return
      renderMathInElement(containerRef.value, {
        delimiters: [
          { left: '$$', right: '$$', display: true },
          { left: '$', right: '$', display: false },
        ],
        throwOnError: false,
      })
    })
  }
  onMounted(renderMath)
  onUpdated(renderMath)
}
```

- [ ] **Step 4: QuestionCard.vue（显示题目，含 KaTeX）**

```vue
<!-- frontend/src/components/QuestionCard.vue -->
<script setup lang="ts">
import { ref } from 'vue'
import { useKatex } from '@/composables/useKatex'
import type { Question } from '@/types'

defineProps<{ question: Question; showAnswer?: boolean }>()
defineEmits<{ delete: [id: string] }>()

const container = ref<HTMLElement | null>(null)
useKatex(container)
</script>

<template>
  <div ref="container" class="bg-white rounded-xl shadow-sm border border-gray-100 p-5 hover:shadow-md transition-shadow">
    <div class="flex items-center justify-between mb-3">
      <div class="flex gap-2">
        <span v-if="question.subject"
          class="text-xs px-2 py-0.5 rounded-full bg-blue-50 text-blue-600 font-medium">
          {{ question.subject }}
        </span>
        <span :class="[
          'text-xs px-2 py-0.5 rounded-full font-medium',
          question.status === 'confirmed' ? 'bg-green-50 text-green-600' : 'bg-yellow-50 text-yellow-600'
        ]">
          {{ question.status === 'confirmed' ? '已确认' : '待确认' }}
        </span>
      </div>
      <button @click="$emit('delete', question.id)"
        class="text-gray-300 hover:text-red-400 transition-colors text-xs">
        删除
      </button>
    </div>

    <div v-if="question.image_url" class="mb-3">
      <img :src="question.image_url" alt="题目图片"
        class="max-w-full rounded-lg border border-gray-100" loading="lazy">
    </div>

    <p class="font-serif text-gray-800 text-base leading-relaxed mb-3 whitespace-pre-wrap">
      {{ question.content }}
    </p>

    <template v-if="showAnswer !== false">
      <div class="border-t border-dashed border-gray-200 pt-3 mt-3 space-y-2">
        <div>
          <p class="text-xs text-gray-400 mb-1">正确答案</p>
          <p class="text-sm text-green-700 font-medium">{{ question.correct_answer }}</p>
        </div>
        <div v-if="question.wrong_answer">
          <p class="text-xs text-gray-400 mb-1">我的错误</p>
          <p class="text-sm text-red-600">{{ question.wrong_answer }}</p>
        </div>
        <div v-if="question.note">
          <p class="text-xs text-gray-400 mb-1">笔记</p>
          <p class="text-sm text-gray-600 italic">{{ question.note }}</p>
        </div>
      </div>
    </template>
  </div>
</template>
```

- [ ] **Step 5: ReviewScoreButtons.vue（1-5 分评分，带标签）**

```vue
<!-- frontend/src/components/ReviewScoreButtons.vue -->
<script setup lang="ts">
defineProps<{ disabled?: boolean }>()
defineEmits<{ score: [n: number] }>()

const SCORES = [
  { score: 1, label: '完全不会', color: 'bg-red-100 text-red-700 hover:bg-red-200 border-red-200' },
  { score: 2, label: '模糊', color: 'bg-orange-100 text-orange-700 hover:bg-orange-200 border-orange-200' },
  { score: 3, label: '想起来了', color: 'bg-yellow-100 text-yellow-700 hover:bg-yellow-200 border-yellow-200' },
  { score: 4, label: '记得', color: 'bg-blue-100 text-blue-700 hover:bg-blue-200 border-blue-200' },
  { score: 5, label: '完全掌握', color: 'bg-green-100 text-green-700 hover:bg-green-200 border-green-200' },
]
</script>

<template>
  <div class="flex gap-2 flex-wrap justify-center">
    <button v-for="s in SCORES" :key="s.score"
      :disabled="disabled"
      :class="['px-4 py-2 rounded-lg border text-sm font-medium transition-all',
               'focus:outline-none focus:ring-2 focus:ring-offset-1',
               'disabled:opacity-50 disabled:cursor-not-allowed', s.color]"
      @click="$emit('score', s.score)">
      <span class="block font-bold">{{ s.score }}</span>
      <span class="text-xs">{{ s.label }}</span>
    </button>
  </div>
</template>
```

- [ ] **Step 6: 更新 App.vue 挂载 AppToast**

```vue
<!-- frontend/src/App.vue -->
<script setup lang="ts">
import { ref, provide } from 'vue'
import AppToast from '@/components/AppToast.vue'
import type { ToastMessage } from '@/components/AppToast.vue'

const toastRef = ref<{ show: (text: string, type?: ToastMessage['type']) => void } | null>(null)
provide('toast', {
  show(text: string, type: ToastMessage['type'] = 'info') {
    toastRef.value?.show(text, type)
  },
})
</script>

<template>
  <RouterView />
  <AppToast ref="toastRef" />
</template>
```

- [ ] **Step 7: Commit**

```bash
git add src/components/ src/composables/useKatex.ts src/App.vue
git commit -m "feat: global components (Toast, Skeleton, QuestionCard, ReviewScoreButtons)"
```

---

### Task 6：全部页面

**Files:**
- Create: `frontend/src/pages/LoginPage.vue`
- Create: `frontend/src/pages/RegisterPage.vue`
- Create: `frontend/src/pages/DashboardPage.vue`
- Create: `frontend/src/pages/UploadPage.vue`
- Create: `frontend/src/pages/QuestionListPage.vue`
- Create: `frontend/src/pages/ReviewPage.vue`
- Create: `frontend/src/pages/PrintPage.vue`

- [ ] **Step 1: LoginPage.vue**

```vue
<!-- frontend/src/pages/LoginPage.vue -->
<script setup lang="ts">
import { ref } from 'vue'
import { useAuth } from '@/composables/useAuth'

const email = ref('')
const password = ref('')
const { loading, error, login } = useAuth()
</script>

<template>
  <div class="min-h-screen bg-gradient-to-br from-primary-50 to-blue-100 flex items-center justify-center p-4">
    <div class="bg-white rounded-2xl shadow-lg w-full max-w-sm p-8">
      <div class="text-center mb-8">
        <div class="text-4xl mb-2">📝</div>
        <h1 class="text-2xl font-bold text-gray-900">错题本</h1>
        <p class="text-sm text-gray-400 mt-1">登录开始复习</p>
      </div>

      <form @submit.prevent="login(email, password)" class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">邮箱</label>
          <input v-model="email" type="email" required placeholder="your@email.com"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm
                   focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent
                   transition-colors" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">密码</label>
          <input v-model="password" type="password" required placeholder="请输入密码"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm
                   focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent" />
        </div>

        <p v-if="error" class="text-sm text-red-500">{{ error }}</p>

        <button type="submit" :disabled="loading"
          class="w-full py-2.5 bg-primary-500 text-white rounded-lg font-medium text-sm
                 hover:bg-primary-600 active:bg-primary-700
                 disabled:opacity-60 disabled:cursor-not-allowed transition-colors
                 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2">
          {{ loading ? '登录中…' : '登录' }}
        </button>
      </form>

      <p class="text-center text-sm text-gray-400 mt-6">
        还没有账号？
        <RouterLink to="/register" class="text-primary-500 hover:underline">注册</RouterLink>
      </p>
    </div>
  </div>
</template>
```

- [ ] **Step 2: RegisterPage.vue**

```vue
<!-- frontend/src/pages/RegisterPage.vue -->
<script setup lang="ts">
import { ref } from 'vue'
import { useAuth } from '@/composables/useAuth'

const email = ref('')
const password = ref('')
const confirm = ref('')
const validationError = ref('')
const { loading, error, register } = useAuth()

function submit() {
  if (password.value !== confirm.value) {
    validationError.value = '两次密码不一致'
    return
  }
  validationError.value = ''
  register(email.value, password.value)
}
</script>

<template>
  <div class="min-h-screen bg-gradient-to-br from-primary-50 to-blue-100 flex items-center justify-center p-4">
    <div class="bg-white rounded-2xl shadow-lg w-full max-w-sm p-8">
      <div class="text-center mb-8">
        <div class="text-4xl mb-2">📝</div>
        <h1 class="text-2xl font-bold text-gray-900">创建账号</h1>
      </div>

      <form @submit.prevent="submit" class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">邮箱</label>
          <input v-model="email" type="email" required placeholder="your@email.com"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm
                   focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">密码（至少 8 位）</label>
          <input v-model="password" type="password" required minlength="8" placeholder="请设置密码"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm
                   focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">确认密码</label>
          <input v-model="confirm" type="password" required placeholder="再次输入密码"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm
                   focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent" />
        </div>

        <p v-if="validationError || error" class="text-sm text-red-500">
          {{ validationError || error }}
        </p>

        <button type="submit" :disabled="loading"
          class="w-full py-2.5 bg-primary-500 text-white rounded-lg font-medium text-sm
                 hover:bg-primary-600 disabled:opacity-60 disabled:cursor-not-allowed transition-colors">
          {{ loading ? '创建中…' : '创建账号' }}
        </button>
      </form>

      <p class="text-center text-sm text-gray-400 mt-6">
        已有账号？
        <RouterLink to="/login" class="text-primary-500 hover:underline">登录</RouterLink>
      </p>
    </div>
  </div>
</template>
```

- [ ] **Step 3: DashboardPage.vue（首页概览）**

```vue
<!-- frontend/src/pages/DashboardPage.vue -->
<script setup lang="ts">
import { onMounted, inject } from 'vue'
import { useReview } from '@/composables/useReview'
import { useAuth } from '@/composables/useAuth'

const { store: reviewStore, fetchStats } = useReview()
const { logout } = useAuth()
const toast = inject<{ show: (t: string, type?: 'success'|'error'|'info') => void }>('toast')

onMounted(fetchStats)

const NAV_ITEMS = [
  { to: '/upload',    icon: '📷', label: '拍照录题', desc: '上传错题图片，AI 自动识别' },
  { to: '/questions', icon: '📚', label: '我的错题', desc: '浏览和管理所有错题' },
  { to: '/review',    icon: '🔄', label: '开始复习', desc: '按 SM-2 算法安排复习' },
  { to: '/print',     icon: '🖨️', label: '打印题目', desc: '生成打印预览，支持 PDF' },
]
</script>

<template>
  <div class="min-h-screen bg-gray-50">
    <!-- 顶部导航 -->
    <header class="bg-white border-b border-gray-200 sticky top-0 z-10">
      <div class="max-w-2xl mx-auto px-4 py-3 flex items-center justify-between">
        <h1 class="text-lg font-bold text-gray-900">📝 错题本</h1>
        <button @click="logout" class="text-sm text-gray-400 hover:text-gray-600">退出</button>
      </div>
    </header>

    <main class="max-w-2xl mx-auto px-4 py-6 space-y-6">
      <!-- 复习状态卡 -->
      <div class="bg-gradient-to-r from-primary-500 to-primary-600 rounded-2xl p-6 text-white">
        <p class="text-sm opacity-75 mb-1">今日待复习</p>
        <p class="text-4xl font-bold mb-4">{{ reviewStore.stats.due_count }}</p>
        <div class="flex items-center gap-4 text-sm">
          <span>今日已完成 <strong>{{ reviewStore.stats.reviewed_today }}</strong> 题</span>
        </div>
        <RouterLink v-if="reviewStore.stats.due_count > 0" to="/review"
          class="mt-4 inline-block bg-white text-primary-600 px-4 py-2 rounded-lg text-sm font-medium
                 hover:bg-primary-50 transition-colors">
          立即复习 →
        </RouterLink>
      </div>

      <!-- 功能入口 -->
      <div class="grid grid-cols-2 gap-3">
        <RouterLink v-for="item in NAV_ITEMS" :key="item.to" :to="item.to"
          class="bg-white rounded-xl p-4 shadow-sm border border-gray-100
                 hover:shadow-md hover:border-primary-200 transition-all
                 focus:outline-none focus:ring-2 focus:ring-primary-500">
          <div class="text-2xl mb-2">{{ item.icon }}</div>
          <p class="font-semibold text-gray-900 text-sm">{{ item.label }}</p>
          <p class="text-xs text-gray-400 mt-0.5">{{ item.desc }}</p>
        </RouterLink>
      </div>
    </main>
  </div>
</template>
```

- [ ] **Step 4: UploadPage.vue（拍照上传 + 确认录入）**

```vue
<!-- frontend/src/pages/UploadPage.vue -->
<script setup lang="ts">
import { ref, inject } from 'vue'
import { useRouter } from 'vue-router'
import { useQuestions } from '@/composables/useQuestions'
import type { RecognitionResult } from '@/types'

const router = useRouter()
const toast = inject<{ show: (t: string, type?: 'success'|'error'|'info') => void }>('toast')
const { recognizing, recognitionResult, recognize, confirmAndSave } = useQuestions()
const fileInput = ref<HTMLInputElement | null>(null)
const previewUrl = ref<string | null>(null)
const saving = ref(false)

async function onFileChange(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  previewUrl.value = URL.createObjectURL(file)
  await recognize(file)
}

async function onConfirm() {
  if (!recognitionResult.value?.candidate) return
  saving.value = true
  try {
    await confirmAndSave({
      content: recognitionResult.value.candidate.content,
      correct_answer: recognitionResult.value.candidate.correct_answer,
      wrong_answer: recognitionResult.value.candidate.wrong_answer ?? undefined,
      subject: recognitionResult.value.candidate.subject ?? undefined,
      question_type: recognitionResult.value.candidate.question_type ?? undefined,
      confidence: recognitionResult.value.candidate.confidence,
    })
    toast?.show('录题成功！', 'success')
    router.push('/questions')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="min-h-screen bg-gray-50">
    <header class="bg-white border-b sticky top-0 z-10">
      <div class="max-w-2xl mx-auto px-4 py-3 flex items-center gap-3">
        <RouterLink to="/dashboard" class="text-gray-400 hover:text-gray-600">← 返回</RouterLink>
        <h2 class="font-semibold text-gray-900">拍照录题</h2>
      </div>
    </header>

    <main class="max-w-2xl mx-auto px-4 py-6 space-y-4">
      <!-- 上传区域 -->
      <div v-if="!previewUrl"
        @click="fileInput?.click()"
        class="bg-white border-2 border-dashed border-gray-300 rounded-2xl p-12
               flex flex-col items-center gap-3 cursor-pointer
               hover:border-primary-400 hover:bg-primary-50 transition-colors">
        <div class="text-5xl">📷</div>
        <p class="text-gray-600 font-medium">点击选择或拍摄错题图片</p>
        <p class="text-xs text-gray-400">支持 JPEG、PNG、HEIC，最大 20MB</p>
        <input ref="fileInput" type="file" accept="image/*" capture="environment"
          class="hidden" @change="onFileChange">
      </div>

      <!-- 图片预览 -->
      <div v-if="previewUrl" class="bg-white rounded-2xl overflow-hidden shadow-sm">
        <img :src="previewUrl" alt="预览" class="w-full max-h-64 object-contain bg-gray-50">
      </div>

      <!-- 识别中 -->
      <div v-if="recognizing" class="bg-white rounded-2xl p-8 text-center shadow-sm">
        <div class="inline-block w-8 h-8 border-4 border-primary-500 border-t-transparent
                    rounded-full animate-spin mb-3"></div>
        <p class="text-gray-600 text-sm">AI 识别中，请稍候…</p>
      </div>

      <!-- 识别结果 -->
      <div v-if="recognitionResult && !recognizing" class="bg-white rounded-2xl shadow-sm p-5 space-y-4">
        <div v-if="recognitionResult.status === 'error'"
          class="text-center py-4">
          <p class="text-red-500 font-medium">识别失败</p>
          <p class="text-sm text-gray-400 mt-1">{{ recognitionResult.error_hint || '请重新拍摄' }}</p>
          <button @click="previewUrl = null; recognitionResult = null"
            class="mt-3 px-4 py-2 bg-gray-100 rounded-lg text-sm hover:bg-gray-200">
            重新选择
          </button>
        </div>

        <template v-else-if="recognitionResult.candidate">
          <div class="flex items-center gap-2">
            <span class="text-xs px-2 py-0.5 rounded-full"
              :class="recognitionResult.status === 'high_confidence'
                ? 'bg-green-50 text-green-600' : 'bg-yellow-50 text-yellow-600'">
              {{ recognitionResult.status === 'high_confidence' ? '识别成功' : '需人工确认' }}
            </span>
            <span class="text-xs text-gray-400">
              置信度 {{ Math.round(recognitionResult.candidate.confidence * 100) }}%
            </span>
          </div>

          <div>
            <p class="text-xs text-gray-400 mb-1">题目内容</p>
            <p class="font-serif text-gray-800 text-sm leading-relaxed whitespace-pre-wrap">
              {{ recognitionResult.candidate.content }}
            </p>
          </div>
          <div>
            <p class="text-xs text-gray-400 mb-1">正确答案</p>
            <p class="text-sm text-green-700 font-medium">{{ recognitionResult.candidate.correct_answer }}</p>
          </div>
          <div v-if="recognitionResult.candidate.wrong_answer">
            <p class="text-xs text-gray-400 mb-1">我的错误</p>
            <p class="text-sm text-red-600">{{ recognitionResult.candidate.wrong_answer }}</p>
          </div>

          <div class="flex gap-3 pt-2">
            <button @click="previewUrl = null; recognitionResult = null"
              class="flex-1 py-2 border border-gray-300 rounded-lg text-sm text-gray-600 hover:bg-gray-50">
              重新拍摄
            </button>
            <button @click="onConfirm" :disabled="saving"
              class="flex-1 py-2 bg-primary-500 text-white rounded-lg text-sm font-medium
                     hover:bg-primary-600 disabled:opacity-60 transition-colors">
              {{ saving ? '保存中…' : '确认录入' }}
            </button>
          </div>
        </template>
      </div>
    </main>
  </div>
</template>
```

- [ ] **Step 5: QuestionListPage.vue**

```vue
<!-- frontend/src/pages/QuestionListPage.vue -->
<script setup lang="ts">
import { onMounted, inject } from 'vue'
import { useQuestions } from '@/composables/useQuestions'
import QuestionCard from '@/components/QuestionCard.vue'
import SkeletonCard from '@/components/SkeletonCard.vue'

const { store, fetchList, softDelete } = useQuestions()
const toast = inject<{ show: (t: string, type?: 'success'|'error'|'info') => void }>('toast')

onMounted(() => fetchList())

async function onDelete(id: string) {
  await softDelete(id)
  toast?.show('已删除', 'success')
}
</script>

<template>
  <div class="min-h-screen bg-gray-50">
    <header class="bg-white border-b sticky top-0 z-10">
      <div class="max-w-2xl mx-auto px-4 py-3 flex items-center justify-between">
        <div class="flex items-center gap-3">
          <RouterLink to="/dashboard" class="text-gray-400">← 返回</RouterLink>
          <h2 class="font-semibold text-gray-900">我的错题（{{ store.total }}）</h2>
        </div>
        <RouterLink to="/upload"
          class="text-sm bg-primary-500 text-white px-3 py-1.5 rounded-lg hover:bg-primary-600">
          + 录题
        </RouterLink>
      </div>
    </header>

    <main class="max-w-2xl mx-auto px-4 py-4 space-y-3">
      <template v-if="store.loading">
        <SkeletonCard v-for="i in 3" :key="i" :lines="4" />
      </template>

      <template v-else-if="store.items.length === 0">
        <div class="text-center py-16 text-gray-400">
          <div class="text-5xl mb-4">📭</div>
          <p class="font-medium">还没有错题</p>
          <RouterLink to="/upload" class="text-primary-500 text-sm mt-2 block hover:underline">
            去录第一道题 →
          </RouterLink>
        </div>
      </template>

      <template v-else>
        <QuestionCard v-for="q in store.items" :key="q.id"
          :question="q" @delete="onDelete" />
      </template>
    </main>
  </div>
</template>
```

- [ ] **Step 6: ReviewPage.vue（SM-2 复习界面）**

```vue
<!-- frontend/src/pages/ReviewPage.vue -->
<script setup lang="ts">
import { onMounted, computed, ref } from 'vue'
import { useKatex } from '@/composables/useKatex'
import { useReview } from '@/composables/useReview'
import ReviewScoreButtons from '@/components/ReviewScoreButtons.vue'

const { store, submitting, fetchQueue, submitScore } = useReview()
const showAnswer = ref(false)
const container = ref<HTMLElement | null>(null)
useKatex(container)

onMounted(fetchQueue)

const current = computed(() => store.current())
const isDone = computed(() => store.currentIndex >= store.queue.length && store.queue.length > 0)

async function onScore(score: number) {
  if (!current.value) return
  showAnswer.value = false
  await submitScore(current.value.id, score)
}
</script>

<template>
  <div class="min-h-screen bg-gray-50 flex flex-col">
    <header class="bg-white border-b sticky top-0 z-10">
      <div class="max-w-2xl mx-auto px-4 py-3 flex items-center justify-between">
        <RouterLink to="/dashboard" class="text-gray-400">← 返回</RouterLink>
        <p class="text-sm text-gray-500">
          {{ store.currentIndex }}/{{ store.queue.length }}
        </p>
      </div>
    </header>

    <main class="max-w-2xl mx-auto px-4 py-6 flex-1 flex flex-col">
      <!-- 全部完成 -->
      <div v-if="isDone" class="flex-1 flex flex-col items-center justify-center text-center gap-4">
        <div class="text-6xl">🎉</div>
        <h2 class="text-xl font-bold text-gray-900">今日复习完成！</h2>
        <p class="text-gray-400 text-sm">共完成 {{ store.queue.length }} 道题</p>
        <RouterLink to="/dashboard"
          class="bg-primary-500 text-white px-6 py-2.5 rounded-lg text-sm font-medium hover:bg-primary-600">
          返回首页
        </RouterLink>
      </div>

      <!-- 无待复习 -->
      <div v-else-if="store.queue.length === 0 && !current"
        class="flex-1 flex flex-col items-center justify-center text-center gap-4 text-gray-400">
        <div class="text-5xl">✅</div>
        <p class="font-medium">今天没有待复习题目</p>
        <RouterLink to="/dashboard" class="text-primary-500 text-sm hover:underline">返回首页</RouterLink>
      </div>

      <!-- 复习卡片 -->
      <div v-else-if="current" ref="container" class="flex-1 flex flex-col gap-4">
        <!-- 进度条 -->
        <div class="h-1.5 bg-gray-200 rounded-full overflow-hidden">
          <div class="h-full bg-primary-500 transition-all"
            :style="`width: ${(store.currentIndex / store.queue.length) * 100}%`"></div>
        </div>

        <!-- 题目卡片 -->
        <div class="bg-white rounded-2xl shadow-sm p-6 flex-1">
          <div v-if="current.subject" class="mb-3">
            <span class="text-xs px-2 py-0.5 bg-blue-50 text-blue-600 rounded-full">
              {{ current.subject }}
            </span>
          </div>
          <div v-if="current.image_url" class="mb-4">
            <img :src="current.image_url" alt="题目图片"
              class="max-w-full rounded-lg border border-gray-100" loading="lazy">
          </div>
          <p class="font-serif text-gray-800 text-base leading-relaxed whitespace-pre-wrap">
            {{ current.content }}
          </p>

          <!-- 答案（点击显示）-->
          <div v-if="showAnswer" class="mt-4 pt-4 border-t border-dashed border-gray-200">
            <p class="text-xs text-gray-400 mb-1">正确答案</p>
            <p class="text-green-700 font-medium">{{ current.content }}</p>
          </div>
        </div>

        <!-- 操作区 -->
        <div class="space-y-3">
          <button v-if="!showAnswer"
            @click="showAnswer = true"
            class="w-full py-3 bg-white border border-gray-300 rounded-xl text-sm font-medium
                   text-gray-700 hover:bg-gray-50 transition-colors shadow-sm">
            查看答案
          </button>

          <ReviewScoreButtons v-else :disabled="submitting" @score="onScore" />
        </div>
      </div>
    </main>
  </div>
</template>
```

- [ ] **Step 7: PrintPage.vue（选题 + 打印预览）**

```vue
<!-- frontend/src/pages/PrintPage.vue -->
<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useQuestions } from '@/composables/useQuestions'
import { IS_MOCK, mockPrint } from '@/api/mock'
import { apiClient } from '@/api/client'

const { store, fetchList } = useQuestions()
const selected = ref<Set<string>>(new Set())
const showAnswer = ref(true)
const layout = ref<'single' | 'double'>('single')
const loading = ref(false)
const previewHtml = ref('')

onMounted(() => fetchList(100, 0))

function toggleSelect(id: string) {
  selected.value.has(id) ? selected.value.delete(id) : selected.value.add(id)
}
const allSelected = computed(() => store.items.every(q => selected.value.has(q.id)))
function toggleAll() {
  allSelected.value
    ? (selected.value = new Set())
    : store.items.forEach(q => selected.value.add(q.id))
}

async function generatePreview() {
  if (selected.value.size === 0) return
  loading.value = true
  try {
    if (IS_MOCK) {
      const resp = await mockPrint.preview([...selected.value], {})
      previewHtml.value = resp.data.html
    } else {
      const resp = await apiClient.post('/v1/print/preview', {
        question_ids: [...selected.value],
        show_answer: showAnswer.value,
        layout: layout.value,
      }, { responseType: 'text' })
      previewHtml.value = resp.data
    }
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="min-h-screen bg-gray-50">
    <header class="bg-white border-b sticky top-0 z-10">
      <div class="max-w-2xl mx-auto px-4 py-3 flex items-center justify-between">
        <div class="flex items-center gap-3">
          <RouterLink to="/dashboard" class="text-gray-400">← 返回</RouterLink>
          <h2 class="font-semibold text-gray-900">打印设置</h2>
        </div>
        <span class="text-sm text-gray-400">已选 {{ selected.size }} 题</span>
      </div>
    </header>

    <main class="max-w-2xl mx-auto px-4 py-4">
      <!-- 打印选项 -->
      <div class="bg-white rounded-xl shadow-sm p-4 mb-4 space-y-3">
        <label class="flex items-center gap-3 cursor-pointer">
          <input type="checkbox" v-model="showAnswer" class="rounded text-primary-500">
          <span class="text-sm text-gray-700">显示答案</span>
        </label>
        <div class="flex items-center gap-3">
          <span class="text-sm text-gray-700">布局</span>
          <select v-model="layout"
            class="text-sm border border-gray-300 rounded-lg px-2 py-1
                   focus:outline-none focus:ring-2 focus:ring-primary-500">
            <option value="single">单列</option>
            <option value="double">双列</option>
          </select>
        </div>
      </div>

      <!-- 全选 -->
      <div class="flex items-center justify-between mb-3 px-1">
        <p class="text-sm text-gray-500">选择要打印的题目</p>
        <button @click="toggleAll" class="text-xs text-primary-500 hover:underline">
          {{ allSelected ? '取消全选' : '全选' }}
        </button>
      </div>

      <!-- 题目列表 -->
      <div class="space-y-2 mb-6">
        <div v-for="q in store.items" :key="q.id"
          @click="toggleSelect(q.id)"
          :class="['bg-white rounded-xl p-4 border cursor-pointer transition-all',
                   selected.has(q.id)
                     ? 'border-primary-400 ring-1 ring-primary-200'
                     : 'border-gray-100 hover:border-gray-300']">
          <div class="flex items-start gap-3">
            <div :class="['w-4 h-4 rounded border-2 flex-shrink-0 mt-0.5 transition-colors',
                          selected.has(q.id)
                            ? 'border-primary-500 bg-primary-500'
                            : 'border-gray-300']">
              <svg v-if="selected.has(q.id)" class="w-3 h-3 text-white" viewBox="0 0 12 12" fill="none">
                <path d="M2 6l3 3 5-5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
              </svg>
            </div>
            <div class="flex-1 min-w-0">
              <span v-if="q.subject" class="text-xs text-blue-600 bg-blue-50 px-1.5 py-0.5 rounded">{{ q.subject }}</span>
              <p class="text-sm text-gray-700 truncate mt-1">{{ q.content }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- 生成预览按钮 -->
      <button @click="generatePreview" :disabled="loading || selected.size === 0"
        class="w-full py-3 bg-primary-500 text-white rounded-xl font-medium
               hover:bg-primary-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors">
        {{ loading ? '生成中…' : `生成打印预览（${selected.size} 题）` }}
      </button>

      <!-- 预览结果 iframe -->
      <div v-if="previewHtml" class="mt-4 bg-white rounded-xl overflow-hidden shadow-sm">
        <div class="px-4 py-2 border-b border-gray-100 text-xs text-gray-400">预览</div>
        <iframe :srcdoc="previewHtml" class="w-full h-[600px] border-0"></iframe>
      </div>
    </main>
  </div>
</template>
```

- [ ] **Step 8: 运行开发服务器验证**

```bash
cd /workshop/ypjh/frontend && VITE_MOCK=true npm run dev
```

访问 `http://localhost:5173`，验证路径：
1. `/login` → 登录表单正常展示
2. 登录后跳转 `/dashboard`，显示复习统计卡和 4 个功能入口
3. `/upload` → 上传区域、识别流程完整
4. `/questions` → 题目列表含骨架屏
5. `/review` → 复习卡片 + 5 级评分按钮
6. `/print` → 选题 + 布局选项 + 预览 iframe

- [ ] **Step 9: 运行全套测试**

```bash
cd /workshop/ypjh/frontend && npm run test -- --run && npm run type-check
```

Expected: 测试通过，无 TS 错误

- [ ] **Step 10: Commit**

```bash
git add src/pages/
git commit -m "feat: all 7 pages with mock data, Tailwind UI, KaTeX math rendering (REQ-F1~F13)"
```
