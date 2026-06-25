# 题目确认 Sheet + 错因诊断 + 错题状态机 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 升级「拍照→直接保存」流程为：底部半屏校对 Sheet → 保存后错因诊断引导 → 六态学习状态机全程追踪。

**Architecture:** 后端新增 `learning_status`/`user_error_type` 两个字段 + 两个 PATCH 端点（error-type、learning-status），前端新增 `ConfirmSheet.vue` 组件替换 UploadPage 内联确认逻辑，DetailPage 嵌入错因选择横幅和底部操作栏，QuestionCard 展示状态角标，Dashboard 展示待订正计数。

**Tech Stack:** FastAPI + SQLAlchemy 2 async + SQLite（Alembic migrate）, Vue 3 + TypeScript + Tailwind CSS v3, Pinia

## Global Constraints

- R1: 所有查询必须带 user_id 过滤，禁止跨用户操作（BOLA）
- R22: user_id 从 JWT sub 提取，拒绝客户端传入
- R21: 软删除，禁止物理删除 Question 记录
- 状态只能正向流转：待分析→待订正→待巩固→待复习→基本掌握→已掌握
- user_error_type 枚举（8 个）：`知识点没掌握`/`概念混淆`/`漏看题目条件`/`解题思路错误`/`计算错误`/`粗心手误`/`时间不足`/`其他`
- learning_status 枚举（6 个）：`待分析`/`待订正`/`待巩固`/`待复习`/`基本掌握`/`已掌握`
- 非法状态跳跃后端返回 400 `INVALID_STATUS_TRANSITION`
- 前端 IS_MOCK flag：`import.meta.env.VITE_MOCK === 'true'`
- 后端测试用 pytest-asyncio + SQLite in-memory，conftest 在 `backend/tests/conftest.py`

---

### Task 1: 后端数据模型 + Schema + 迁移

**Files:**
- Modify: `backend/models/question.py`
- Modify: `backend/schemas/question.py`
- Modify: `backend/repositories/question_repository.py`
- Modify: `backend/services/question_service.py`（`_to_out` + `create` 初始化）
- Test: `backend/tests/test_learning_status.py`（新建）

**Interfaces:**
- Produces: `Question.learning_status: str = "待分析"`, `Question.user_error_type: str | None = None`
- Produces: `QuestionOut.learning_status: str`, `QuestionOut.user_error_type: str | None`
- Produces: `QuestionCreate` 不暴露 learning_status（后端内部初始化）

- [ ] **Step 1: 写失败测试**

新建 `backend/tests/test_learning_status.py`：

```python
import os, pytest
os.environ["MOCK_BEDROCK"] = "true"

from sqlalchemy.ext.asyncio import AsyncSession
from backend.services.question_service import QuestionService
from backend.schemas.question import QuestionCreate


@pytest.mark.asyncio
async def test_new_question_has_learning_status_待分析(session: AsyncSession):
    svc = QuestionService()
    out = await svc.create(session, "u1", QuestionCreate(content="题目", correct_answer="答案"))
    assert out.learning_status == "待分析"
    assert out.user_error_type is None


@pytest.mark.asyncio
async def test_learning_status_returned_in_list(session: AsyncSession):
    svc = QuestionService()
    await svc.create(session, "u1", QuestionCreate(content="题目", correct_answer="答案"))
    result = await svc.get_list(session, "u1")
    assert result.items[0].learning_status == "待分析"
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
cd /workshop/ypjh && backend/.venv/bin/pytest backend/tests/test_learning_status.py -v 2>&1 | tail -15
```

Expected: `AttributeError` 或 `ValidationError`，因为字段不存在。

- [ ] **Step 3: 在 Question model 新增字段**

修改 `backend/models/question.py`，在 `deleted_at` 行后面添加：

```python
    learning_status: Mapped[str] = mapped_column(default="待分析")
    user_error_type: Mapped[str | None] = mapped_column(default=None)
```

- [ ] **Step 4: 在 QuestionOut 新增字段**

修改 `backend/schemas/question.py`，`QuestionOut` 中 `analysis` 字段之后添加：

```python
    learning_status: str = "待分析"
    user_error_type: str | None = None
```

- [ ] **Step 5: 在 `_to_out()` 中传递新字段**

修改 `backend/services/question_service.py` 的 `_to_out()` 函数，在 `analysis=question.analysis,` 后面添加：

```python
        learning_status=question.learning_status,
        user_error_type=question.user_error_type,
```

- [ ] **Step 6: 在 `QuestionRepository.create()` 初始化新字段**

修改 `backend/repositories/question_repository.py` 的 `create()` 方法，在 `analysis=data.analysis,` 后面添加：

```python
            learning_status="待分析",
            user_error_type=None,
```

- [ ] **Step 7: 运行测试，确认通过**

```bash
cd /workshop/ypjh && backend/.venv/bin/pytest backend/tests/test_learning_status.py -v 2>&1 | tail -10
```

Expected: `2 passed`

- [ ] **Step 8: 运行全量测试，确认无回归**

```bash
cd /workshop/ypjh && backend/.venv/bin/pytest backend/tests/ -v --tb=short 2>&1 | tail -20
```

Expected: 全部 passed（现有测试不受影响，因为 SQLite 会自动加新列）

- [ ] **Step 9: Commit**

```bash
cd /workshop/ypjh && git add backend/models/question.py backend/schemas/question.py backend/repositories/question_repository.py backend/services/question_service.py backend/tests/test_learning_status.py
git commit -m "feat: add learning_status and user_error_type fields to Question"
```

---

### Task 2: 后端 PATCH /error-type 端点

**Files:**
- Modify: `backend/api/v1/endpoints/questions.py`
- Modify: `backend/services/question_service.py`
- Modify: `backend/schemas/question.py`
- Test: `backend/tests/test_learning_status.py`（追加）

**Interfaces:**
- Consumes: Task 1 的 `learning_status`/`user_error_type` 字段、`QuestionOut`
- Produces: `PATCH /api/v1/questions/{id}/error-type` — body `ErrorTypeUpdate`, 返回 `ApiResponse[QuestionOut]`
- Produces: `QuestionService.set_error_type(session, question_id, user_id, error_type) -> QuestionOut`

- [ ] **Step 1: 写失败测试**

在 `backend/tests/test_learning_status.py` 追加：

```python
from httpx import AsyncClient
from backend.core.security import get_current_user
from backend.models.user import User
from unittest.mock import AsyncMock


def _mock_user(uid: str):
    user = User()
    user.id = uid
    user.email = f"{uid}@test.com"
    return user


@pytest.mark.asyncio
async def test_set_error_type_transitions_to_待订正(session: AsyncSession):
    svc = QuestionService()
    out = await svc.create(session, "u1", QuestionCreate(content="题目", correct_answer="答案"))
    updated = await svc.set_error_type(session, out.id, "u1", "计算错误")
    assert updated.user_error_type == "计算错误"
    assert updated.learning_status == "待订正"


@pytest.mark.asyncio
async def test_set_error_type_invalid_value_raises(session: AsyncSession):
    from fastapi import HTTPException
    svc = QuestionService()
    out = await svc.create(session, "u1", QuestionCreate(content="题目", correct_answer="答案"))
    with pytest.raises(HTTPException) as exc:
        await svc.set_error_type(session, out.id, "u1", "无效错因")
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_set_error_type_cross_user_raises(session: AsyncSession):
    from fastapi import HTTPException
    svc = QuestionService()
    out = await svc.create(session, "u1", QuestionCreate(content="题目", correct_answer="答案"))
    with pytest.raises(HTTPException) as exc:
        await svc.set_error_type(session, out.id, "u2", "计算错误")
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_set_error_type_already_待订正_only_updates_type(session: AsyncSession):
    svc = QuestionService()
    out = await svc.create(session, "u1", QuestionCreate(content="题目", correct_answer="答案"))
    await svc.set_error_type(session, out.id, "u1", "计算错误")
    updated = await svc.set_error_type(session, out.id, "u1", "概念混淆")
    assert updated.user_error_type == "概念混淆"
    assert updated.learning_status == "待订正"  # 不倒退
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
cd /workshop/ypjh && backend/.venv/bin/pytest backend/tests/test_learning_status.py -v 2>&1 | tail -15
```

Expected: `AttributeError: 'QuestionService' object has no attribute 'set_error_type'`

- [ ] **Step 3: 在 schemas 新增 ErrorTypeUpdate**

在 `backend/schemas/question.py` 末尾添加：

```python
VALID_ERROR_TYPES = frozenset({
    "知识点没掌握", "概念混淆", "漏看题目条件",
    "解题思路错误", "计算错误", "粗心手误", "时间不足", "其他",
})

STATUS_FORWARD_ORDER = [
    "待分析", "待订正", "待巩固", "待复习", "基本掌握", "已掌握",
]

class ErrorTypeUpdate(BaseModel):
    user_error_type: str
```

- [ ] **Step 4: 在 QuestionService 新增 set_error_type()**

在 `backend/services/question_service.py` 的 `QuestionService` 类内，`delete()` 方法之后添加：

```python
    async def set_error_type(
        self,
        session: AsyncSession,
        question_id: str,
        user_id: str,
        error_type: str,
    ) -> QuestionOut:
        from backend.schemas.question import VALID_ERROR_TYPES, STATUS_FORWARD_ORDER
        if error_type not in VALID_ERROR_TYPES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": "INVALID_ERROR_TYPE", "message": f"错因必须是: {', '.join(sorted(VALID_ERROR_TYPES))}"},
            )
        q = await _repo.get_by_id(session, question_id, user_id)
        if q is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "NOT_FOUND", "message": "题目不存在"},
            )
        q.user_error_type = error_type
        # 正向推进：仅当当前状态靠前时推进到 待订正
        current_idx = STATUS_FORWARD_ORDER.index(q.learning_status) if q.learning_status in STATUS_FORWARD_ORDER else 0
        target_idx = STATUS_FORWARD_ORDER.index("待订正")
        if current_idx < target_idx:
            q.learning_status = "待订正"
        await session.flush()
        await session.commit()
        return _to_out(q)
```

- [ ] **Step 5: 在 questions.py 路由新增 PATCH /{id}/error-type**

在 `backend/api/v1/endpoints/questions.py` 的 imports 中追加 `ErrorTypeUpdate`：

```python
from backend.schemas.question import (
    ErrorTypeUpdate,
    QuestionCreate,
    QuestionListOut,
    QuestionOut,
    QuestionUpdate,
)
```

在文件末尾的 `delete_question` 之后添加：

```python
@router.patch("/{question_id}/error-type", response_model=ApiResponse[QuestionOut])
async def set_error_type(
    question_id: str,
    body: ErrorTypeUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[QuestionOut]:
    result = await _svc.set_error_type(session, question_id, current_user.id, body.user_error_type)
    return ApiResponse(data=result)
```

- [ ] **Step 6: 运行测试，确认通过**

```bash
cd /workshop/ypjh && backend/.venv/bin/pytest backend/tests/test_learning_status.py -v 2>&1 | tail -15
```

Expected: 所有测试 passed

- [ ] **Step 7: Commit**

```bash
cd /workshop/ypjh && git add backend/schemas/question.py backend/services/question_service.py backend/api/v1/endpoints/questions.py backend/tests/test_learning_status.py
git commit -m "feat: add PATCH /questions/{id}/error-type endpoint with status transition"
```

---

### Task 3: 后端 PATCH /learning-status 端点 + stats 扩展

**Files:**
- Modify: `backend/api/v1/endpoints/questions.py`
- Modify: `backend/services/question_service.py`
- Modify: `backend/schemas/question.py`
- Modify: `backend/schemas/review.py`
- Modify: `backend/services/review_service.py`
- Modify: `backend/repositories/review_repository.py`
- Test: `backend/tests/test_learning_status.py`（追加）

**Interfaces:**
- Consumes: Task 1/2 的 `STATUS_FORWARD_ORDER`, `QuestionOut`
- Produces: `PATCH /api/v1/questions/{id}/learning-status` — body `LearningStatusUpdate`, 返回 `ApiResponse[QuestionOut]`
- Produces: `ReviewStatsOut.pending_correction_count: int`（`GET /review/stats` 新增字段）
- Produces: `QuestionService.set_learning_status(session, question_id, user_id, new_status) -> QuestionOut`

- [ ] **Step 1: 写失败测试**

在 `backend/tests/test_learning_status.py` 追加：

```python
@pytest.mark.asyncio
async def test_set_learning_status_forward_ok(session: AsyncSession):
    svc = QuestionService()
    out = await svc.create(session, "u1", QuestionCreate(content="题目", correct_answer="答案"))
    # 先推到 待订正
    await svc.set_error_type(session, out.id, "u1", "计算错误")
    # 再推到 待巩固
    updated = await svc.set_learning_status(session, out.id, "u1", "待巩固")
    assert updated.learning_status == "待巩固"


@pytest.mark.asyncio
async def test_set_learning_status_backward_raises(session: AsyncSession):
    from fastapi import HTTPException
    svc = QuestionService()
    out = await svc.create(session, "u1", QuestionCreate(content="题目", correct_answer="答案"))
    await svc.set_error_type(session, out.id, "u1", "计算错误")
    await svc.set_learning_status(session, out.id, "u1", "待巩固")
    with pytest.raises(HTTPException) as exc:
        await svc.set_learning_status(session, out.id, "u1", "待分析")
    assert exc.value.status_code == 400
    assert exc.value.detail["code"] == "INVALID_STATUS_TRANSITION"


@pytest.mark.asyncio
async def test_pending_correction_count_in_stats(session: AsyncSession):
    from backend.services.review_service import ReviewService
    svc = QuestionService()
    rsvc = ReviewService()
    # 创建两道题，一道推进，一道停在待分析
    await svc.create(session, "u1", QuestionCreate(content="题1", correct_answer="答1"))
    out2 = await svc.create(session, "u1", QuestionCreate(content="题2", correct_answer="答2"))
    await svc.set_error_type(session, out2.id, "u1", "计算错误")
    stats = await rsvc.get_stats(session, "u1")
    # 待分析 的题不算待订正，只有 learning_status="待分析" 才需要被标记
    assert hasattr(stats, "pending_correction_count")
    assert stats.pending_correction_count == 1  # 题1 是 待分析，尚未标注错因
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
cd /workshop/ypjh && backend/.venv/bin/pytest backend/tests/test_learning_status.py::test_set_learning_status_forward_ok backend/tests/test_learning_status.py::test_pending_correction_count_in_stats -v 2>&1 | tail -15
```

Expected: `AttributeError` 或 `AssertionError`

- [ ] **Step 3: 在 schemas/question.py 新增 LearningStatusUpdate**

在 `ErrorTypeUpdate` 类之后添加：

```python
class LearningStatusUpdate(BaseModel):
    learning_status: str
```

- [ ] **Step 4: 在 QuestionService 新增 set_learning_status()**

在 `set_error_type()` 之后添加：

```python
    async def set_learning_status(
        self,
        session: AsyncSession,
        question_id: str,
        user_id: str,
        new_status: str,
    ) -> QuestionOut:
        from backend.schemas.question import STATUS_FORWARD_ORDER
        if new_status not in STATUS_FORWARD_ORDER:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": "INVALID_STATUS", "message": f"状态必须是: {', '.join(STATUS_FORWARD_ORDER)}"},
            )
        q = await _repo.get_by_id(session, question_id, user_id)
        if q is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "NOT_FOUND", "message": "题目不存在"},
            )
        current_idx = STATUS_FORWARD_ORDER.index(q.learning_status) if q.learning_status in STATUS_FORWARD_ORDER else 0
        target_idx = STATUS_FORWARD_ORDER.index(new_status)
        if target_idx <= current_idx and new_status != q.learning_status:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "INVALID_STATUS_TRANSITION", "message": f"状态不能从 {q.learning_status} 退回到 {new_status}"},
            )
        q.learning_status = new_status
        await session.flush()
        await session.commit()
        return _to_out(q)
```

- [ ] **Step 5: 在 questions.py 路由新增 PATCH /{id}/learning-status**

在 `questions.py` 的 imports 追加 `LearningStatusUpdate`：

```python
from backend.schemas.question import (
    ErrorTypeUpdate,
    LearningStatusUpdate,
    QuestionCreate,
    QuestionListOut,
    QuestionOut,
    QuestionUpdate,
)
```

在 `set_error_type` 路由之后添加：

```python
@router.patch("/{question_id}/learning-status", response_model=ApiResponse[QuestionOut])
async def set_learning_status(
    question_id: str,
    body: LearningStatusUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[QuestionOut]:
    result = await _svc.set_learning_status(session, question_id, current_user.id, body.learning_status)
    return ApiResponse(data=result)
```

- [ ] **Step 6: 扩展 ReviewStatsOut 新增 pending_correction_count**

修改 `backend/schemas/review.py`，`ReviewStatsOut` 中添加字段：

```python
class ReviewStatsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    due_count: int
    reviewed_today: int
    pending_correction_count: int = 0
```

- [ ] **Step 7: ReviewRepository 新增 get_pending_correction_count()**

修改 `backend/repositories/review_repository.py`，在 `get_stats()` 方法前添加：

```python
    async def get_pending_correction_count(
        self, session: AsyncSession, user_id: str
    ) -> int:
        stmt = select(func.count()).select_from(Question).where(
            Question.user_id == user_id,
            Question.learning_status == "待分析",
            Question.deleted_at.is_(None),
        )
        return (await session.execute(stmt)).scalar_one()
```

在文件顶部 imports 中补充 `Question` 的导入（如果还没有）：

```python
from backend.models.question import Question
```

- [ ] **Step 8: ReviewService.get_stats() 调用新方法**

修改 `backend/services/review_service.py` 的 `get_stats()` 方法：

```python
    async def get_stats(
        self, session: AsyncSession, user_id: str
    ) -> ReviewStatsOut:
        stats = await _rrepo.get_stats(session, user_id)
        pending_correction_count = await _rrepo.get_pending_correction_count(session, user_id)
        return ReviewStatsOut(
            due_count=stats["due_count"],
            reviewed_today=stats["reviewed_today"],
            pending_correction_count=pending_correction_count,
        )
```

- [ ] **Step 9: 运行测试，确认通过**

```bash
cd /workshop/ypjh && backend/.venv/bin/pytest backend/tests/test_learning_status.py -v 2>&1 | tail -20
```

Expected: 全部 passed

- [ ] **Step 10: 运行全量测试**

```bash
cd /workshop/ypjh && backend/.venv/bin/pytest backend/tests/ -v --tb=short 2>&1 | tail -20
```

Expected: 全部 passed

- [ ] **Step 11: Commit**

```bash
cd /workshop/ypjh && git add backend/schemas/question.py backend/schemas/review.py backend/services/question_service.py backend/services/review_service.py backend/repositories/review_repository.py backend/api/v1/endpoints/questions.py backend/tests/test_learning_status.py
git commit -m "feat: add PATCH /learning-status endpoint and pending_correction_count to stats"
```

---

### Task 4: 前端 types + mock + questionsApi

**Files:**
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/api/mock/questions.mock.ts`
- Modify: `frontend/src/api/endpoints/questions.ts`（如存在，否则新建）

**Interfaces:**
- Consumes: Task 1-3 产出的字段名和枚举值
- Produces: `Question.learning_status: string`, `Question.user_error_type: string | null`
- Produces: `ReviewStats.pending_correction_count: number`
- Produces: `questionsApi.setErrorType(id, type)`, `questionsApi.setLearningStatus(id, status)`

- [ ] **Step 1: 更新 frontend/src/types/index.ts**

在 `Question` interface 中，`analysis` 字段之后添加：

```typescript
  learning_status: string
  user_error_type: string | null
```

在 `ReviewStats` interface 中添加：

```typescript
  pending_correction_count: number
```

完整的更新后 `ReviewStats`：

```typescript
export interface ReviewStats {
  due_count: number
  reviewed_today: number
  pending_correction_count: number
}
```

- [ ] **Step 2: 更新 mock 数据**

修改 `frontend/src/api/mock/questions.mock.ts`，在两个 mock 题目中添加字段（q-1 和 q-2 均添加）：

```typescript
// q-1
learning_status: '待订正',
user_error_type: '计算错误',

// q-2
learning_status: '待分析',
user_error_type: null,
```

在 `mockQuestions` 对象中添加两个新方法（在 `softDelete` 之前）：

```typescript
  async setErrorType(id: string, errorType: string): Promise<ApiResponse<Question>> {
    await new Promise(r => setTimeout(r, 200))
    const q = MOCK_QUESTIONS.find(q => q.id === id)
    if (!q) return { data: null as unknown as Question, error: { code: 'NOT_FOUND', message: '题目不存在' } }
    q.user_error_type = errorType
    if (q.learning_status === '待分析') q.learning_status = '待订正'
    return { data: { ...q }, error: null }
  },
  async setLearningStatus(id: string, status: string): Promise<ApiResponse<Question>> {
    await new Promise(r => setTimeout(r, 200))
    const q = MOCK_QUESTIONS.find(q => q.id === id)
    if (!q) return { data: null as unknown as Question, error: { code: 'NOT_FOUND', message: '题目不存在' } }
    q.learning_status = status
    return { data: { ...q }, error: null }
  },
```

- [ ] **Step 3: 扩展 questionsApi**

找到 `frontend/src/api/endpoints/questions.ts`（如不存在则查找 `frontend/src/api/` 下的 questions 相关文件），新增两个方法：

```typescript
  setErrorType: (id: string, userErrorType: string) =>
    apiClient.patch<Question>(`/questions/${id}/error-type`, { user_error_type: userErrorType }),

  setLearningStatus: (id: string, learningStatus: string) =>
    apiClient.patch<Question>(`/questions/${id}/learning-status`, { learning_status: learningStatus }),
```

- [ ] **Step 4: 更新 mock/index.ts 导出新方法（如有聚合文件）**

检查 `frontend/src/api/mock/index.ts`（或 `frontend/src/api/mock.ts`），确保新方法被导出。

- [ ] **Step 5: 类型检查**

```bash
cd /workshop/ypjh/frontend && npm run type-check 2>&1 | tail -15
```

Expected: 无错误

- [ ] **Step 6: Commit**

```bash
cd /workshop/ypjh && git add frontend/src/types/index.ts frontend/src/api/mock/questions.mock.ts frontend/src/api/
git commit -m "feat: frontend types + mock + API methods for learning_status and error_type"
```

---

### Task 5: ConfirmSheet.vue 组件 + UploadPage 集成

**Files:**
- Create: `frontend/src/components/ConfirmSheet.vue`
- Modify: `frontend/src/pages/UploadPage.vue`

**Interfaces:**
- Consumes: Task 4 的 `Question`, `questionsApi`, `mockQuestions`, `IS_MOCK`
- Produces: `ConfirmSheet` props: `{ visible: boolean, candidate: RecognitionResult['candidate'] }`, emits: `close`, `saved(question: Question)`

- [ ] **Step 1: 新建 ConfirmSheet.vue**

新建 `frontend/src/components/ConfirmSheet.vue`：

```vue
<script setup lang="ts">
import { ref, watch } from 'vue'
import { IS_MOCK, mockQuestions } from '@/api/mock'
import { questionsApi } from '@/api/endpoints/questions'
import type { Question, RecognitionResult } from '@/types'

const props = defineProps<{
  visible: boolean
  candidate: RecognitionResult['candidate'] | null
}>()

const emit = defineEmits<{
  close: []
  saved: [question: Question]
}>()

const content = ref('')
const correctAnswer = ref('')
const wrongAnswer = ref('')
const subject = ref('')
const saving = ref(false)

const SUBJECTS = ['语文', '数学', '英语', '物理', '化学', '生物', '历史', '地理', '政治']

watch(() => props.candidate, (c) => {
  if (c) {
    content.value = c.content
    correctAnswer.value = c.correct_answer
    wrongAnswer.value = c.wrong_answer ?? ''
    subject.value = c.subject ?? ''
  }
}, { immediate: true })

async function onSave() {
  if (!props.candidate || saving.value) return
  saving.value = true
  try {
    const payload = {
      content: content.value,
      correct_answer: correctAnswer.value,
      wrong_answer: wrongAnswer.value || null,
      subject: subject.value || null,
      question_type: props.candidate.question_type ?? null,
      confidence: props.candidate.confidence,
      image_key: props.candidate.image_key ?? null,
      analysis: props.candidate.analysis ?? null,
    }
    let question: Question
    if (IS_MOCK) {
      const resp = await mockQuestions.create(payload)
      question = resp.data
    } else {
      const resp = await questionsApi.create(payload)
      question = resp.data.data
    }
    emit('saved', question)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <Teleport to="body">
    <Transition name="sheet">
      <div v-if="visible" class="fixed inset-0 z-50 flex flex-col justify-end">
        <!-- 遮罩 -->
        <div class="absolute inset-0 bg-black/40" />

        <!-- Sheet 主体 -->
        <div class="relative bg-white rounded-t-2xl max-h-[85vh] flex flex-col shadow-2xl">
          <!-- 拖拽条 -->
          <div class="flex justify-center pt-3 pb-1">
            <div class="w-10 h-1 bg-gray-300 rounded-full" />
          </div>

          <!-- 头部 -->
          <div class="flex items-center justify-between px-5 py-3 border-b border-gray-100">
            <div class="flex items-center gap-2">
              <span v-if="candidate && candidate.confidence >= 0.7"
                class="text-sm font-semibold text-gray-800">识别完成 ✓</span>
              <span v-else class="text-sm font-semibold text-yellow-700">⚠️ 识别置信度较低，请仔细检查</span>
              <span v-if="candidate"
                :class="['text-xs px-2 py-0.5 rounded-full', candidate.confidence >= 0.7
                  ? 'bg-green-50 text-green-600' : 'bg-yellow-50 text-yellow-700']">
                {{ Math.round((candidate.confidence) * 100) }}%
              </span>
            </div>
            <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600 text-xl leading-none">×</button>
          </div>

          <!-- 表单 -->
          <div class="overflow-y-auto flex-1 px-5 py-4 space-y-4">
            <div>
              <label class="text-xs text-gray-400 block mb-1">题目内容</label>
              <textarea v-model="content" rows="4"
                class="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm
                       text-gray-800 resize-none focus:outline-none focus:ring-2 focus:ring-primary-300" />
            </div>
            <div>
              <label class="text-xs text-gray-400 block mb-1">正确答案</label>
              <input v-model="correctAnswer" type="text"
                class="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm
                       focus:outline-none focus:ring-2 focus:ring-primary-300" />
            </div>
            <div>
              <label class="text-xs text-gray-400 block mb-1">我的错误答案（选填）</label>
              <input v-model="wrongAnswer" type="text" placeholder="留空跳过"
                class="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm
                       text-gray-400 placeholder-gray-300 focus:outline-none focus:ring-2 focus:ring-primary-300" />
            </div>
            <div>
              <label class="text-xs text-gray-400 block mb-1">学科</label>
              <select v-model="subject"
                class="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm
                       focus:outline-none focus:ring-2 focus:ring-primary-300 bg-white">
                <option value="">不确定</option>
                <option v-for="s in SUBJECTS" :key="s" :value="s">{{ s }}</option>
              </select>
            </div>
          </div>

          <!-- 底部按钮 -->
          <div class="px-5 py-4 border-t border-gray-100">
            <button @click="onSave" :disabled="saving || !content || !correctAnswer"
              class="w-full py-3.5 bg-primary-500 text-white rounded-xl font-semibold text-sm
                     hover:bg-primary-600 disabled:opacity-50 transition-colors">
              {{ saving ? '保存中…' : (candidate && candidate.confidence < 0.7 ? '确认并保存' : '保存到错题本') }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.sheet-enter-active,
.sheet-leave-active {
  transition: all 0.3s ease;
}
.sheet-enter-from .relative,
.sheet-leave-to .relative {
  transform: translateY(100%);
}
.sheet-enter-from .absolute,
.sheet-leave-to .absolute {
  opacity: 0;
}
</style>
```

- [ ] **Step 2: 修改 UploadPage.vue**

将 `frontend/src/pages/UploadPage.vue` 的 `<script setup>` 部分替换为：

```vue
<script setup lang="ts">
import { ref, inject } from 'vue'
import { useRouter } from 'vue-router'
import { useQuestions } from '@/composables/useQuestions'
import ConfirmSheet from '@/components/ConfirmSheet.vue'
import type { Question } from '@/types'

const router = useRouter()
const toast = inject<{ show: (t: string, type?: 'success'|'error'|'info') => void }>('toast')
const { recognizing, recognitionResult, recognize } = useQuestions()
const fileInput = ref<HTMLInputElement | null>(null)
const previewUrl = ref<string | null>(null)
const sheetVisible = ref(false)

async function onFileChange(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  previewUrl.value = URL.createObjectURL(file)
  await recognize(file)
  if (recognitionResult.value?.status !== 'error') {
    sheetVisible.value = true
  }
}

function onSheetClose() {
  sheetVisible.value = false
}

function onSaved(question: Question) {
  sheetVisible.value = false
  toast?.show('录题成功！', 'success')
  router.push(`/questions/${question.id}?new=1`)
}
</script>
```

将 template 中的「识别结果」卡片区块（`v-if="recognitionResult && !recognizing"` 的整个 `<div>`）替换为：

```vue
      <!-- 识别完成提示（Sheet 已打开，不再展示卡片） -->
      <div v-if="recognitionResult && !recognizing && recognitionResult.status === 'error'"
        class="bg-white rounded-2xl shadow-sm p-5">
        <div class="text-center py-4">
          <p class="text-red-500 font-medium">识别失败</p>
          <p class="text-sm text-gray-400 mt-1">{{ recognitionResult.error_hint || '请重新拍摄' }}</p>
          <button @click="previewUrl = null; recognitionResult = null"
            class="mt-3 px-4 py-2 bg-gray-100 rounded-lg text-sm hover:bg-gray-200">
            重新选择
          </button>
        </div>
      </div>
```

在 `</template>` 结束之前（`</div>` 最外层之后）添加：

```vue
      <ConfirmSheet
        :visible="sheetVisible"
        :candidate="recognitionResult?.candidate ?? null"
        @close="onSheetClose"
        @saved="onSaved"
      />
```

- [ ] **Step 3: 类型检查**

```bash
cd /workshop/ypjh/frontend && npm run type-check 2>&1 | tail -15
```

Expected: 无错误

- [ ] **Step 4: Commit**

```bash
cd /workshop/ypjh && git add frontend/src/components/ConfirmSheet.vue frontend/src/pages/UploadPage.vue
git commit -m "feat: add ConfirmSheet bottom sheet for recognition result editing"
```

---

### Task 6: DetailPage 错因诊断横幅 + 底部操作栏

**Files:**
- Modify: `frontend/src/pages/QuestionDetailPage.vue`

**Interfaces:**
- Consumes: Task 4/5 的 `questionsApi.setErrorType`, `mockQuestions.setErrorType`, `questionsApi.setLearningStatus`, `mockQuestions.setLearningStatus`, `Question.learning_status`, `Question.user_error_type`

- [ ] **Step 1: 在 script setup 新增状态和方法**

在 `QuestionDetailPage.vue` 的 `<script setup>` 中，`route`/`question`/`loading`/`error` 等 ref 之后添加：

```typescript
import { computed } from 'vue'
import { useRoute } from 'vue-router'

// 已有 route, question, loading, error refs — 只追加以下内容：

const showErrorBanner = ref(true)
const errorTypeExpanded = ref(false)
const submittingErrorType = ref(false)
const submittingStatus = ref(false)
const selectedErrorType = ref('')

const isNewQuestion = computed(() => route.query.new === '1')
const showErrorTypeGuide = computed(() =>
  isNewQuestion.value &&
  showErrorBanner.value &&
  question.value?.learning_status === '待分析'
)

const ERROR_TYPES = [
  '知识点没掌握', '概念混淆', '漏看题目条件', '解题思路错误',
  '计算错误', '粗心手误', '时间不足', '其他',
]

async function submitErrorType() {
  if (!selectedErrorType.value || !question.value) return
  submittingErrorType.value = true
  try {
    let updated
    if (IS_MOCK) {
      const resp = await mockQuestions.setErrorType(question.value.id, selectedErrorType.value)
      updated = resp.data
    } else {
      const resp = await questionsApi.setErrorType(question.value.id, selectedErrorType.value)
      updated = resp.data.data
    }
    question.value = updated
    showErrorBanner.value = false
  } finally {
    submittingErrorType.value = false
  }
}

async function advanceStatus(newStatus: string) {
  if (!question.value) return
  submittingStatus.value = true
  try {
    let updated
    if (IS_MOCK) {
      const resp = await mockQuestions.setLearningStatus(question.value.id, newStatus)
      updated = resp.data
    } else {
      const resp = await questionsApi.setLearningStatus(question.value.id, newStatus)
      updated = resp.data.data
    }
    question.value = updated
  } finally {
    submittingStatus.value = false
  }
}
```

- [ ] **Step 2: 在 template 添加错因横幅（题目内容卡片之前）**

在 `<!-- 图片 -->` div 之前添加：

```vue
        <!-- 错因诊断引导横幅 -->
        <div v-if="showErrorTypeGuide" class="bg-orange-50 border border-orange-200 rounded-2xl p-4">
          <div class="flex items-center justify-between">
            <p class="text-sm text-orange-800 font-medium">
              📌 标记一下你的错误原因，帮助AI优化解析
            </p>
            <button v-if="!errorTypeExpanded"
              @click="errorTypeExpanded = true"
              class="text-xs text-orange-600 border border-orange-300 rounded-lg px-3 py-1.5 hover:bg-orange-100 shrink-0 ml-3">
              立即标记 →
            </button>
          </div>

          <!-- 展开的选择区 -->
          <div v-if="errorTypeExpanded" class="mt-4 space-y-3">
            <p class="text-xs text-gray-500">你认为这题出错的主要原因？</p>
            <div class="grid grid-cols-2 gap-2">
              <button
                v-for="t in ERROR_TYPES" :key="t"
                @click="selectedErrorType = t"
                :class="[
                  'text-xs py-2 px-3 rounded-lg border transition-colors text-left',
                  selectedErrorType === t
                    ? 'border-orange-400 bg-orange-50 text-orange-700 font-medium'
                    : 'border-gray-200 text-gray-600 hover:border-gray-300'
                ]"
              >{{ t }}</button>
            </div>
            <div class="flex gap-2 pt-1">
              <button @click="submitErrorType" :disabled="!selectedErrorType || submittingErrorType"
                class="flex-1 py-2 bg-orange-500 text-white rounded-lg text-sm font-medium
                       hover:bg-orange-600 disabled:opacity-50 transition-colors">
                {{ submittingErrorType ? '提交中…' : '确认' }}
              </button>
              <button @click="showErrorBanner = false"
                class="px-4 py-2 border border-gray-200 rounded-lg text-sm text-gray-500 hover:bg-gray-50">
                跳过
              </button>
            </div>
          </div>
        </div>
```

- [ ] **Step 3: 在 AI 解析卡片内添加用户错因标签**

在 AI 解析卡片（`v-if="question.analysis"`）的 `<h3>💡 AI 解析</h3>` 之后、`<!-- 新格式：解题思路 -->` 之前添加：

```vue
          <!-- 用户错因标签 -->
          <div v-if="question.user_error_type" class="flex items-center gap-2 flex-wrap">
            <span class="text-xs px-2.5 py-1 bg-orange-100 text-orange-700 rounded-full font-medium">
              你的错因：{{ question.user_error_type }}
            </span>
            <span v-if="question.analysis.error_analysis"
              class="text-xs px-2.5 py-1 bg-red-50 text-red-600 rounded-full font-medium">
              AI诊断：{{ question.analysis.error_analysis.type }}
            </span>
          </div>
```

- [ ] **Step 4: 添加底部固定操作栏**

在 `</main>` 结束标签之后、`</div>` 最外层关闭之前，添加：

```vue
      <!-- 底部操作栏（随学习状态变化） -->
      <div v-if="question && (question.learning_status === '待订正' || question.learning_status === '待巩固')"
        class="fixed bottom-16 left-0 right-0 z-20 px-4 pb-2 max-w-2xl mx-auto">
        <button
          v-if="question.learning_status === '待订正'"
          @click="advanceStatus('待巩固')"
          :disabled="submittingStatus"
          class="w-full py-3.5 bg-blue-500 text-white rounded-xl font-semibold text-sm
                 hover:bg-blue-600 disabled:opacity-50 transition-colors shadow-lg">
          {{ submittingStatus ? '更新中…' : '✓ 我已理解，进入复习' }}
        </button>
        <button
          v-else-if="question.learning_status === '待巩固'"
          @click="advanceStatus('待复习')"
          :disabled="submittingStatus"
          class="w-full py-3.5 bg-purple-500 text-white rounded-xl font-semibold text-sm
                 hover:bg-purple-600 disabled:opacity-50 transition-colors shadow-lg">
          {{ submittingStatus ? '更新中…' : '📚 加入今日复习' }}
        </button>
      </div>
```

- [ ] **Step 5: 类型检查**

```bash
cd /workshop/ypjh/frontend && npm run type-check 2>&1 | tail -15
```

Expected: 无错误

- [ ] **Step 6: Commit**

```bash
cd /workshop/ypjh && git add frontend/src/pages/QuestionDetailPage.vue
git commit -m "feat: add error type guide banner and learning status action bar to DetailPage"
```

---

### Task 7: 状态角标 + Dashboard 待订正徽章 + 部署

**Files:**
- Modify: `frontend/src/components/QuestionCard.vue`
- Modify: `frontend/src/pages/DashboardPage.vue`
- Modify: `frontend/src/api/mock/review.mock.ts`（如存在）或 `frontend/src/composables/useReview.ts`

**Interfaces:**
- Consumes: Task 4 的 `Question.learning_status`, `ReviewStats.pending_correction_count`

- [ ] **Step 1: QuestionCard 新增状态角标**

在 `QuestionCard.vue` 的 template 中，找到 `<div class="flex items-center justify-between mb-3">` 内的第一个子 div（包含 subject 和 status 的 `flex gap-2` div），在其后、删除按钮之前，添加状态角标到右侧区域。

将整个 `flex items-center justify-between mb-3` div 替换为：

```vue
    <div class="flex items-center justify-between mb-3">
      <div class="flex gap-2 flex-wrap">
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
      <div class="flex items-center gap-2">
        <!-- 学习状态角标 -->
        <span v-if="question.learning_status === '已掌握'" class="text-green-500 text-xs font-bold">✓</span>
        <span v-else-if="question.learning_status" :class="[
          'w-2 h-2 rounded-full shrink-0',
          question.learning_status === '待分析' ? 'bg-gray-300' :
          question.learning_status === '待订正' ? 'bg-orange-400' :
          question.learning_status === '待巩固' ? 'bg-blue-400' :
          question.learning_status === '待复习' ? 'bg-purple-400' :
          question.learning_status === '基本掌握' ? 'bg-green-400' : 'bg-gray-200'
        ]" :title="question.learning_status" />
        <button
          @click.stop="$emit('delete', question.id)"
          class="text-gray-300 hover:text-red-400 transition-colors text-xs px-2 py-1 -mr-1"
        >
          删除
        </button>
      </div>
    </div>
```

- [ ] **Step 2: 更新 mock review stats**

找到 review 相关 mock（`frontend/src/api/mock/review.mock.ts` 或 `useReview.ts` 里的 mock 数据），在 stats 返回值中添加：

```typescript
pending_correction_count: 1,
```

如果 stats 在 `useReview.ts` 内联，找到类似 `{ due_count: ..., reviewed_today: ... }` 的地方补充该字段。

- [ ] **Step 3: DashboardPage 新增待订正徽章**

在 `DashboardPage.vue` template 的「今日已完成」行旁边，在复习状态卡中添加待订正提示。

找到：

```vue
        <div class="flex items-center gap-4 text-sm opacity-80">
          <span>今日已完成 <strong class="opacity-100">{{ reviewStore.stats.reviewed_today }}</strong> 题</span>
        </div>
```

替换为：

```vue
        <div class="flex items-center gap-4 text-sm opacity-80 flex-wrap">
          <span>今日已完成 <strong class="opacity-100">{{ reviewStore.stats.reviewed_today }}</strong> 题</span>
          <span v-if="reviewStore.stats.pending_correction_count > 0">
            待订正 <strong class="opacity-100 text-yellow-200">{{ reviewStore.stats.pending_correction_count }}</strong> 题
          </span>
        </div>
```

- [ ] **Step 4: 类型检查**

```bash
cd /workshop/ypjh/frontend && npm run type-check 2>&1 | tail -15
```

Expected: 无错误

- [ ] **Step 5: 构建前端**

```bash
cd /workshop/ypjh/frontend && npm run build 2>&1 | tail -10
```

Expected: `✓ built in X.XXs`，无错误

- [ ] **Step 6: 重启后端（加载新的 model 字段）**

```bash
pkill -f "uvicorn backend.main" 2>/dev/null; sleep 2
cd /workshop/ypjh && AWS_DEFAULT_REGION="us-east-1" \
  AWS_ACCESS_KEY_ID="$(grep AWS_ACCESS_KEY_ID /proc/$(pgrep -f 'uvicorn backend')/environ 2>/dev/null | cut -d= -f2 || echo '')" \
  MOCK_BEDROCK=false \
  backend/.venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 1 \
  > /tmp/wrongbook-backend.log 2>&1 &
sleep 3 && tail -5 /tmp/wrongbook-backend.log
```

如果 AWS 凭证读取失败（环境变量为空），从 `.env` 或之前的部署脚本获取凭证后再启动。

- [ ] **Step 7: 验证后端新端点可达**

```bash
curl -s http://localhost:8000/api/v1/questions/nonexistent/error-type \
  -X PATCH -H "Content-Type: application/json" -H "Authorization: Bearer invalid" \
  -d '{"user_error_type":"计算错误"}' | python3 -m json.tool
```

Expected: `{"detail": {"code": "TOKEN_INVALID", ...}}` （401/422）— 端点存在，未授权

- [ ] **Step 8: Commit**

```bash
cd /workshop/ypjh && git add frontend/src/components/QuestionCard.vue frontend/src/pages/DashboardPage.vue frontend/src/api/
git commit -m "feat: status badge on cards, pending_correction_count on dashboard, deploy"
```
