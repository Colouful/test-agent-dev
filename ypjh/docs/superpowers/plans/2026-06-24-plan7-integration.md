# 错题本 Plan 7：前后端集成

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Plan 6 的 mock 数据层替换为真实 FastAPI 后端调用，完成端到端联调，所有功能在 `VITE_MOCK=false` 下正常工作。

**Architecture:** 切换 `VITE_MOCK=false`，Axios client 指向 `http://localhost:8000`，后端 CORS 允许前端域名，开发环境 Vite 代理转发 `/api` 请求，消除跨域问题。

**Tech Stack:** Vite proxy（开发）, FastAPI CORS middleware, uvicorn

**前置条件:** Plan 1-5（后端全部完成）+ Plan 6（前端 mock 阶段完成）

## Global Constraints

- `user_id` 只从 JWT sub 取，前端不传（R22）
- 所有 API 响应必须是 `{ data: ..., error: ... }` 格式（统一 Schema）
- 图片响应含 `image_url`（预签名 URL），不含 `image_key`（R23）
- 软删除后 GET 返回 404，前端处理此场景（R21）

---

## 文件结构

```
frontend/
├── vite.config.ts            # 添加 /api proxy
└── src/api/endpoints/        # 真实 API 调用（已在 Plan 6 的 composable 中引用）

backend/
└── main.py                   # 添加 CORS middleware
```

---

### Task 1：后端 CORS + 运行验证

**Files:**
- Modify: `backend/main.py`

- [ ] **Step 1: 添加 CORS middleware**

```python
# backend/main.py（在已有内容基础上添加 CORS）
from fastapi.middleware.cors import CORSMiddleware

# 在 app = FastAPI(...) 后添加：
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

- [ ] **Step 2: 启动后端**

```bash
cd /workshop/ypjh/backend && uv run uvicorn main:app --reload --port 8000
```

- [ ] **Step 3: 验证 API 文档可访问**

访问 `http://localhost:8000/docs`，确认所有路由显示正确：
- POST `/api/v1/auth/register`
- POST `/api/v1/auth/login`
- POST `/api/v1/questions/recognize`
- GET/POST `/api/v1/questions`
- GET/PATCH/DELETE `/api/v1/questions/{id}`
- GET `/api/v1/review/queue`
- POST `/api/v1/review/{id}/score`
- GET `/api/v1/review/stats`
- POST `/api/v1/print/preview`

- [ ] **Step 4: Commit**

```bash
git add backend/main.py
git commit -m "feat: add CORS middleware for frontend dev origin"
```

---

### Task 2：Vite Proxy 配置

**Files:**
- Modify: `frontend/vite.config.ts`
- Create: `frontend/.env.development`
- Create: `frontend/.env.production`

- [ ] **Step 1: 配置 Vite proxy**

```ts
// frontend/vite.config.ts
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
```

- [ ] **Step 2: 环境变量文件**

```bash
# frontend/.env.development
VITE_MOCK=false
VITE_API_BASE_URL=/api
```

```bash
# frontend/.env.production
VITE_MOCK=false
VITE_API_BASE_URL=/api
```

```bash
# frontend/.env.mock（可选，开发时快速切换）
VITE_MOCK=true
VITE_API_BASE_URL=/api
```

- [ ] **Step 3: 更新 api/client.ts 使用环境变量**

```ts
// frontend/src/api/client.ts（完整替换）
import axios from 'axios'

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 30_000,
})

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

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

- [ ] **Step 4: Commit**

```bash
git add frontend/vite.config.ts frontend/.env.development frontend/.env.production
git commit -m "feat: Vite proxy config, env files for API routing"
```

---

### Task 3：真实 API 端点函数

**Files:**
- Create: `frontend/src/api/endpoints/auth.ts`
- Create: `frontend/src/api/endpoints/questions.ts`
- Create: `frontend/src/api/endpoints/review.ts`
- Create: `frontend/src/api/endpoints/print.ts`

> 说明：Plan 6 的 composable 已通过 `IS_MOCK` 分支调 mock 或 `apiClient.xxx()`。这里提取可复用的端点函数，避免 composable 中散落 URL 字符串。

- [ ] **Step 1: auth.ts**

```ts
// frontend/src/api/endpoints/auth.ts
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

- [ ] **Step 2: questions.ts**

```ts
// frontend/src/api/endpoints/questions.ts
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

- [ ] **Step 3: review.ts**

```ts
// frontend/src/api/endpoints/review.ts
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

- [ ] **Step 4: print.ts**

```ts
// frontend/src/api/endpoints/print.ts
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

- [ ] **Step 5: 更新 composable 使用真实端点（非 mock 分支）**

更新 `frontend/src/composables/useAuth.ts`（非 mock 分支）：

```ts
// 替换 useAuth.ts 中的非 mock 分支：
import { authApi } from '@/api/endpoints/auth'

// login 函数中：
const resp = IS_MOCK
  ? await mockAuth.login(email, password)
  : (await authApi.login(email, password)).data
```

更新 `frontend/src/composables/useQuestions.ts`（非 mock 分支）：

```ts
import { questionsApi } from '@/api/endpoints/questions'

// fetchList 中：
const resp = IS_MOCK
  ? await mockQuestions.list(limit, offset)
  : (await questionsApi.list(limit, offset)).data

// recognize 中：
const resp = IS_MOCK
  ? await mockQuestions.recognize(file)
  : (await questionsApi.recognize(file)).data

// confirmAndSave 中：
const resp = IS_MOCK
  ? await mockQuestions.create(data)
  : (await questionsApi.create(data)).data

// softDelete 中：
IS_MOCK
  ? await mockQuestions.softDelete(id)
  : await questionsApi.delete(id)
```

更新 `frontend/src/composables/useReview.ts`（非 mock 分支）：

```ts
import { reviewApi } from '@/api/endpoints/review'

// fetchQueue 中：
const resp = IS_MOCK
  ? await mockReview.queue()
  : (await reviewApi.queue()).data

// fetchStats 中：
const resp = IS_MOCK
  ? await mockReview.stats()
  : (await reviewApi.stats()).data

// submitScore 中：
IS_MOCK
  ? await mockReview.submitScore(questionId, score)
  : await reviewApi.submitScore(questionId, score)
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/api/endpoints/ frontend/src/composables/
git commit -m "feat: real API endpoint functions, wire composables to backend (REQ-F1~F13)"
```

---

### Task 4：端到端联调验证

> 本 Task 为手动测试清单，所有路径必须在 `VITE_MOCK=false` 下验证通过。

- [ ] **Step 1: 启动后端**

```bash
cd /workshop/ypjh/backend && MOCK_BEDROCK=true uv run uvicorn main:app --reload --port 8000
```

- [ ] **Step 2: 启动前端**

```bash
cd /workshop/ypjh/frontend && npm run dev
```

- [ ] **Step 3: 注册 + 登录流程**

1. 访问 `http://localhost:5173/register`
2. 填写邮箱和密码，提交
3. 自动跳转 `/login`（或直接进 dashboard）
4. 登录后看到 Dashboard，复习统计显示"今日待复习 0"

- [ ] **Step 4: 录题流程**

1. 进入 `/upload`
2. 选择一张任意图片（JPEG/PNG）
3. 看到 loading spinner（AI识别中…）约 1-2s
4. 识别结果显示（mock_bedrock 给出预设内容）
5. 点"确认录入"
6. 跳转到 `/questions`，新题目出现在列表

- [ ] **Step 5: 复习流程**

1. 进入 `/review`
2. 若队列有题目：看到题目卡片
3. 点"查看答案"展开
4. 点评分按钮（1-5 分）
5. 下一题或完成界面正常展示

- [ ] **Step 6: 打印流程**

1. 进入 `/print`
2. 勾选若干题目
3. 点"生成打印预览"
4. iframe 中显示 HTML（含题目内容和 KaTeX）
5. 点 iframe 中"打印"按钮触发浏览器打印对话框

- [ ] **Step 7: 安全验证（R1 跨用户隔离）**

```bash
# 注册两个用户
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"alice@test.com","password":"password123"}'

curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"bob@test.com","password":"password123"}'

# 获取 Alice 的 token，创建一道题
ALICE_TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"alice@test.com","password":"password123"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['access_token'])")

curl -X POST http://localhost:8000/api/v1/questions \
  -H "Authorization: Bearer $ALICE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content":"Alice 的私密题目","correct_answer":"答案"}'

# 用 Bob 的 token 查询 Alice 的题目列表
BOB_TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"bob@test.com","password":"password123"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['access_token'])")

curl http://localhost:8000/api/v1/questions \
  -H "Authorization: Bearer $BOB_TOKEN"
# 预期：total=0，items=[]
```

- [ ] **Step 8: 运行后端全套测试**

```bash
cd /workshop/ypjh/backend && uv run pytest -v
```

Expected: 全部通过（≥20 个测试）

- [ ] **Step 9: 运行前端全套测试 + 类型检查**

```bash
cd /workshop/ypjh/frontend && npm run test -- --run && npm run type-check
```

Expected: 全部通过，无 TS 错误

- [ ] **Step 10: Commit**

```bash
git add .
git commit -m "feat: frontend-backend integration complete, all flows verified (Plan 7 done)"
```

---

### Task 5：.env.example + 部署说明

**Files:**
- Create: `frontend/.env.example`
- Create: `backend/.env.example`

- [ ] **Step 1: frontend/.env.example**

```bash
# frontend/.env.example
# 开发时用 mock 数据
VITE_MOCK=true

# 连接真实后端
# VITE_MOCK=false
# VITE_API_BASE_URL=/api
```

- [ ] **Step 2: backend/.env.example**

```bash
# backend/.env.example

# 应用配置
SECRET_KEY=change-me-in-production-use-openssl-rand-hex-32
DATABASE_URL=sqlite+aiosqlite:///./wrongbook.db
DEBUG=true

# Bedrock / S3（生产时设为 false）
MOCK_BEDROCK=true
# S3_BUCKET=wrongbook-images-prod
# AWS_DEFAULT_REGION=us-east-1
```

- [ ] **Step 3: 添加 .gitignore 条目（确保 .env 不提交）**

```bash
echo ".env" >> /workshop/ypjh/.gitignore
echo ".env.local" >> /workshop/ypjh/.gitignore
echo "frontend/.env.development.local" >> /workshop/ypjh/.gitignore
```

- [ ] **Step 4: Commit**

```bash
git add frontend/.env.example backend/.env.example .gitignore
git commit -m "docs: add .env.example files and update .gitignore"
```

---

## 集成完成标准

所有以下命令必须 **无错误退出**：

```bash
# 后端
cd /workshop/ypjh/backend && uv run pytest -v
# 预期：≥20 tests passed

# 前端
cd /workshop/ypjh/frontend && npm run test -- --run && npm run type-check
# 预期：all tests passed, no TS errors

# 架构检查（如果 ci/arch-check.sh 存在）
cd /workshop/ypjh && bash ci/arch-check.sh
# 预期：PASS 或 OK

# mock 模式快速验证（无需启动后端）
cd /workshop/ypjh/frontend && VITE_MOCK=true npm run build
# 预期：build succeeded
```
