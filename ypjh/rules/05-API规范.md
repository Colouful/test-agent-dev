# 05 - API 规范

## 后端：FastAPI 路由

### 路由职责边界

路由函数只允许做三件事：
1. 接收并验证请求（FastAPI + Pydantic 自动完成）
2. 调用 service 方法
3. 返回响应或抛出 `HTTPException`

```python
# api/v1/endpoints/questions.py
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_session
from schemas.question import QuestionCreate, QuestionOut, QuestionListOut
from services.question_service import QuestionService

router = APIRouter(prefix="/questions", tags=["questions"])

@router.post("/", response_model=QuestionOut, status_code=status.HTTP_201_CREATED)
async def create_question(
    body: QuestionCreate,
    session: AsyncSession = Depends(get_session),
) -> QuestionOut:
    return await QuestionService(session).create(body)
```

### URL 命名规范

```
GET    /api/v1/questions          # 列表
POST   /api/v1/questions          # 创建
GET    /api/v1/questions/{id}     # 详情
PATCH  /api/v1/questions/{id}     # 部分更新
DELETE /api/v1/questions/{id}     # 删除（204）

# 嵌套资源
GET    /api/v1/questions/{id}/reviews
POST   /api/v1/questions/{id}/reviews

# 多词用 kebab-case
GET    /api/v1/review-plans
```

### Pydantic Schema

```python
# schemas/question.py
from pydantic import BaseModel, Field, ConfigDict

class QuestionBase(BaseModel):
    subject_id: int
    content: str = Field(..., min_length=1)
    correct_answer: str = Field(..., min_length=1)
    difficulty: int = Field(..., ge=1, le=5)

class QuestionCreate(QuestionBase):
    wrong_answer: str | None = None
    analysis: str | None = None

class QuestionUpdate(BaseModel):
    content: str | None = Field(None, min_length=1)
    correct_answer: str | None = Field(None, min_length=1)
    difficulty: int | None = Field(None, ge=1, le=5)
    wrong_answer: str | None = None
    analysis: str | None = None

class QuestionOut(QuestionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    review_count: int
    next_review_at: datetime | None
    created_at: datetime
    updated_at: datetime
```

规则：
- `Base → Create / Update / Out` 分层继承
- `Out` 必须设置 `ConfigDict(from_attributes=True)`
- 更新 Schema 所有字段可选
- 响应 Schema 不暴露密码 hash 等内部字段

### 统一响应格式

```python
# 列表
{"items": [...], "total": 100, "page": 1, "page_size": 20}

# 单条资源 — 直接返回对象，不额外包 data 层
{"id": 1, "content": "...", ...}

# 错误 — FastAPI 默认格式
{"detail": "题目不存在"}

# 删除 — 204，无响应体
@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
```

### HTTP 状态码

| 操作 | 状态码 |
|---|---|
| 查询成功 | 200 |
| 创建成功 | 201 |
| 更新成功 | 200 |
| 删除成功 | 204 |
| 参数错误 | 400 |
| 未认证 | 401 |
| 无权限 | 403 |
| 不存在 | 404 |
| 服务器错误 | 500 |

---

## 前端：Axios 请求封装

### Axios 实例

```typescript
// api/client.ts
import axios from 'axios'
import { useAuthStore } from '@/stores/useAuthStore'

export const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 10_000,
})

client.interceptors.request.use((config) => {
  const token = useAuthStore().token
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

client.interceptors.response.use(
  (res) => res.data,
  (error) => {
    const message = error.response?.data?.detail ?? '请求失败'
    // Toast 通知由 composable 层处理，这里只透传
    return Promise.reject(new Error(message))
  },
)
```

### 请求函数规范

```typescript
// api/questions.ts
import { client } from './client'
import type { Question, QuestionCreate, QuestionUpdate, PaginatedResult } from '@/types'

export const questionsApi = {
  list(params?: { page?: number; page_size?: number; subject_id?: number }) {
    return client.get<PaginatedResult<Question>>('/api/v1/questions', { params })
  },
  get(id: number) {
    return client.get<Question>(`/api/v1/questions/${id}`)
  },
  create(data: QuestionCreate) {
    return client.post<Question>('/api/v1/questions', data)
  },
  update(id: number, data: QuestionUpdate) {
    return client.patch<Question>(`/api/v1/questions/${id}`, data)
  },
  remove(id: number) {
    return client.delete<void>(`/api/v1/questions/${id}`)
  },
}
```

规则：
- 所有 HTTP 请求通过 `api/` 模块，禁止在组件或 store 里直接用 `axios`
- 函数返回 Promise，不在 api 层 try/catch（由 composable/store 处理）
- 字段名使用 snake_case 与后端保持一致

### 前端数据模型

```typescript
// types/models.ts
export interface Question {
  id: number
  subject_id: number
  type: 'single' | 'multiple' | 'fill' | 'essay'
  content: string
  wrong_answer?: string
  correct_answer: string
  analysis?: string
  difficulty: 1 | 2 | 3 | 4 | 5
  next_review_at?: string  // ISO 8601
  review_count: number
  ease_factor: number
  created_at: string
  updated_at: string
}

export interface PaginatedResult<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}
```
