# 错题本 Plan 4：SM-2 复习模块

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 SM-2 间隔重复复习功能：获取今日复习队列、提交复习得分（1-5）、更新题目 SM-2 参数、记录复习日志、查看复习统计。

**Architecture:** `ReviewRepository` 管理 ReviewLog；`SM2Calculator` 封装算法；`ReviewService` 编排；三个端点 `/api/v1/review/queue`, `/api/v1/review/{id}/score`, `/api/v1/review/stats`。

**Tech Stack:** 纯 Python（SM-2 算法）+ SQLAlchemy 2 async

**前置条件:** Plan 1（models/review_log.py、models/question.py SM-2 字段）+ Plan 3（QuestionRepository）均已完成

## Global Constraints

- 所有查询必须带 `user_id` 过滤（R1）
- `user_id` 从 JWT sub 提取（R22）
- 得分范围：1-5 整数（1=完全不会, 3=模糊记得, 5=完全掌握）
- score < 3 → 重置：review_count=0, interval=1, ease_factor 不变
- ease_factor 最小值 1.3，永不低于此值
- 复习后更新 next_review_at = now() + interval_days

---

## 文件结构

```
backend/
├── core/
│   └── sm2.py                       # SM-2 算法（纯函数，无 DB 依赖）
├── repositories/
│   └── review_repository.py         # ReviewLog DB 操作 + 复习队列查询
├── schemas/
│   └── review.py                    # ReviewQueueOut, ScoreRequest, ScoreOut, ReviewStatsOut
├── services/
│   └── review_service.py            # 复习流程编排
└── api/v1/endpoints/
    └── review.py                    # 3 个端点
tests/
├── test_sm2.py
└── api/test_review.py
```

---

### Task 1：SM-2 算法核心

**Files:**
- Create: `backend/core/sm2.py`

**Interfaces:**
- Produces:
  - `calculate_next_review(score, ease_factor, interval_days, review_count) -> tuple[float, int, int]`
    返回 (new_ef, new_interval, new_review_count)

- [ ] **Step 1: 写算法测试**

```python
# backend/tests/test_sm2.py
import pytest
from backend.core.sm2 import calculate_next_review


# --- 失败路径（score < 3）---
def test_score_1_resets_interval():
    ef, interval, count = calculate_next_review(
        score=1, ease_factor=2.5, interval_days=6, review_count=3
    )
    assert interval == 1
    assert count == 0
    assert ef == 2.5  # 失败时不修改 EF


def test_score_2_resets_interval():
    ef, interval, count = calculate_next_review(
        score=2, ease_factor=2.5, interval_days=10, review_count=5
    )
    assert interval == 1
    assert count == 0


# --- 成功路径（score >= 3）---
def test_score_3_first_review():
    ef, interval, count = calculate_next_review(
        score=3, ease_factor=2.5, interval_days=1, review_count=0
    )
    assert count == 1
    assert interval == 1


def test_score_3_second_review():
    ef, interval, count = calculate_next_review(
        score=3, ease_factor=2.5, interval_days=1, review_count=1
    )
    assert count == 2
    assert interval == 6


def test_score_5_third_review():
    ef, interval, count = calculate_next_review(
        score=5, ease_factor=2.5, interval_days=6, review_count=2
    )
    assert count == 3
    assert interval == round(6 * 2.5)  # 15
    assert ef > 2.5  # score=5 时 EF 增长


def test_ease_factor_minimum_1_3():
    # score=1 时 EF 不变，但 score=3 且初始 EF=1.4 时不应低于 1.3
    ef, _, _ = calculate_next_review(
        score=3, ease_factor=1.4, interval_days=1, review_count=0
    )
    assert ef >= 1.3


def test_ease_factor_never_below_floor():
    # 连续低分后 EF 不低于 1.3
    ef = 1.31
    for _ in range(10):
        ef, _, _ = calculate_next_review(
            score=3, ease_factor=ef, interval_days=1, review_count=0
        )
    assert ef >= 1.3
```

- [ ] **Step 2: 运行确认失败**

```bash
cd /workshop/ypjh/backend && uv run pytest tests/test_sm2.py -v
```

Expected: `ImportError`

- [ ] **Step 3: 实现 sm2.py**

```python
# backend/core/sm2.py
from __future__ import annotations


def calculate_next_review(
    score: int,
    ease_factor: float,
    interval_days: int,
    review_count: int,
) -> tuple[float, int, int]:
    """SM-2 算法核心。返回 (new_ease_factor, new_interval_days, new_review_count)。"""
    if score < 3:
        # 失败：重置间隔，EF 不变
        return ease_factor, 1, 0

    # 成功
    new_count = review_count + 1
    if new_count == 1:
        new_interval = 1
    elif new_count == 2:
        new_interval = 6
    else:
        new_interval = round(interval_days * ease_factor)

    new_ef = ease_factor + (0.1 - (5 - score) * (0.08 + (5 - score) * 0.02))
    new_ef = max(1.3, new_ef)

    return new_ef, new_interval, new_count
```

- [ ] **Step 4: 运行测试**

```bash
cd /workshop/ypjh/backend && uv run pytest tests/test_sm2.py -v
```

Expected: `7 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/core/sm2.py backend/tests/test_sm2.py
git commit -m "feat: SM-2 spaced repetition algorithm with 5-level scoring"
```

---

### Task 2：ReviewRepository + Review Schemas

**Files:**
- Create: `backend/repositories/review_repository.py`
- Create: `backend/schemas/review.py`

**Interfaces:**
- Produces:
  - `ReviewRepository.get_due_questions(session, user_id, limit) -> list[Question]`（next_review_at ≤ now）
  - `ReviewRepository.create_log(session, user_id, question_id, score, prev/new ef/interval) -> ReviewLog`
  - `ReviewRepository.get_stats(session, user_id) -> dict`（due_count, reviewed_today, streak_days）
  - `ReviewQueueItemOut`, `ScoreRequest`, `ScoreOut`, `ReviewStatsOut`

- [ ] **Step 1: 写 repository 测试**

```python
# backend/tests/test_review_repository.py
import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from backend.repositories.review_repository import ReviewRepository
from backend.repositories.question_repository import QuestionRepository
from backend.schemas.question import QuestionCreate


@pytest.mark.asyncio
async def test_get_due_questions_returns_overdue(session: AsyncSession):
    qrepo = QuestionRepository()
    rrepo = ReviewRepository()

    # 创建一道已到期题目（next_review_at = 昨天）
    q = await qrepo.create(session, "user-1", QuestionCreate(
        content="题目", correct_answer="答案"
    ))
    q.next_review_at = datetime.now(timezone.utc) - timedelta(days=1)
    await session.flush()

    due = await rrepo.get_due_questions(session, "user-1", limit=10)
    assert len(due) == 1
    assert due[0].id == q.id


@pytest.mark.asyncio
async def test_get_due_questions_user_isolation(session: AsyncSession):
    qrepo = QuestionRepository()
    rrepo = ReviewRepository()
    q = await qrepo.create(session, "user-1", QuestionCreate(
        content="题目", correct_answer="答案"
    ))
    q.next_review_at = datetime.now(timezone.utc) - timedelta(hours=1)
    await session.flush()

    # user-2 不应看到 user-1 的题目（R1）
    due = await rrepo.get_due_questions(session, "user-2", limit=10)
    assert len(due) == 0


@pytest.mark.asyncio
async def test_create_log_records_review(session: AsyncSession):
    qrepo = QuestionRepository()
    rrepo = ReviewRepository()
    q = await qrepo.create(session, "user-1", QuestionCreate(
        content="题目", correct_answer="答案"
    ))
    log = await rrepo.create_log(
        session,
        user_id="user-1",
        question_id=q.id,
        score=4,
        prev_ease_factor=2.5,
        new_ease_factor=2.6,
        prev_interval=1,
        new_interval=6,
    )
    assert log.score == 4
    assert log.user_id == "user-1"
```

- [ ] **Step 2: 运行确认失败**

```bash
cd /workshop/ypjh/backend && uv run pytest tests/test_review_repository.py -v
```

- [ ] **Step 3: 实现 review_repository.py**

```python
# backend/repositories/review_repository.py
from __future__ import annotations
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.question import Question
from backend.models.review_log import ReviewLog


class ReviewRepository:

    async def get_due_questions(
        self, session: AsyncSession, user_id: str, limit: int = 20
    ) -> list[Question]:
        now = datetime.now(timezone.utc)
        stmt = (
            select(Question)
            .where(
                Question.user_id == user_id,         # R1
                Question.deleted_at.is_(None),        # R21
                Question.next_review_at <= now,
            )
            .order_by(Question.next_review_at.asc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def create_log(
        self,
        session: AsyncSession,
        user_id: str,
        question_id: str,
        score: int,
        prev_ease_factor: float,
        new_ease_factor: float,
        prev_interval: int,
        new_interval: int,
    ) -> ReviewLog:
        log = ReviewLog(
            id=str(uuid.uuid4()),
            user_id=user_id,
            question_id=question_id,
            score=score,
            prev_ease_factor=prev_ease_factor,
            new_ease_factor=new_ease_factor,
            prev_interval=prev_interval,
            new_interval=new_interval,
            reviewed_at=datetime.now(timezone.utc),
        )
        session.add(log)
        await session.flush()
        return log

    async def get_stats(
        self, session: AsyncSession, user_id: str
    ) -> dict[str, int]:
        now = datetime.now(timezone.utc)
        # 待复习数量
        due_stmt = select(func.count()).where(
            Question.user_id == user_id,
            Question.deleted_at.is_(None),
            Question.next_review_at <= now,
        )
        due_count: int = (await session.execute(due_stmt)).scalar_one()

        # 今日已复习
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        reviewed_stmt = select(func.count()).where(
            ReviewLog.user_id == user_id,
            ReviewLog.reviewed_at >= today_start,
        )
        reviewed_today: int = (await session.execute(reviewed_stmt)).scalar_one()

        return {"due_count": due_count, "reviewed_today": reviewed_today}
```

- [ ] **Step 4: 实现 review.py schemas**

```python
# backend/schemas/review.py
from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, Field


class ReviewQueueItemOut(BaseModel):
    id: str
    content: str
    subject: str | None
    question_type: str | None
    image_url: str | None
    image_url_expires_at: datetime | None
    ease_factor: float
    interval_days: int
    review_count: int


class ReviewQueueOut(BaseModel):
    items: list[ReviewQueueItemOut]
    total: int


class ScoreRequest(BaseModel):
    score: int = Field(..., ge=1, le=5)


class ScoreOut(BaseModel):
    question_id: str
    score: int
    new_ease_factor: float
    new_interval_days: int
    new_review_count: int
    next_review_at: datetime


class ReviewStatsOut(BaseModel):
    due_count: int
    reviewed_today: int
```

- [ ] **Step 5: 运行 repository 测试**

```bash
cd /workshop/ypjh/backend && uv run pytest tests/test_review_repository.py -v
```

Expected: `3 passed`

- [ ] **Step 6: Commit**

```bash
git add backend/repositories/review_repository.py backend/schemas/review.py backend/tests/test_review_repository.py
git commit -m "feat: ReviewRepository with due queue, log creation, stats (R1)"
```

---

### Task 3：ReviewService + Review API

**Files:**
- Create: `backend/services/review_service.py`
- Create: `backend/api/v1/endpoints/review.py`
- Modify: `backend/api/v1/router.py`

**Interfaces:**
- Produces:
  - `GET /api/v1/review/queue` → `ApiResponse[ReviewQueueOut]`
  - `POST /api/v1/review/{question_id}/score` → `ApiResponse[ScoreOut]`
  - `GET /api/v1/review/stats` → `ApiResponse[ReviewStatsOut]`

- [ ] **Step 1: 写 API 集成测试**

```python
# backend/tests/api/test_review.py
import pytest
from datetime import datetime, timedelta, timezone
from httpx import AsyncClient


async def _setup_user_with_due_question(client: AsyncClient, email: str):
    await client.post("/api/v1/auth/register",
        json={"email": email, "password": "password123"})
    login = await client.post("/api/v1/auth/login",
        json={"email": email, "password": "password123"})
    token = login.json()["data"]["access_token"]
    # 创建一道题
    create = await client.post("/api/v1/questions",
        json={"content": "复习题", "correct_answer": "答案"},
        headers={"Authorization": f"Bearer {token}"})
    qid = create.json()["data"]["id"]
    return token, qid


@pytest.mark.asyncio
async def test_review_queue_returns_due_items(client: AsyncClient):
    token, _ = await _setup_user_with_due_question(client, "rv1@test.com")
    resp = await client.get("/api/v1/review/queue",
        headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "items" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_score_updates_sm2_params(client: AsyncClient):
    token, qid = await _setup_user_with_due_question(client, "rv2@test.com")
    resp = await client.post(f"/api/v1/review/{qid}/score",
        json={"score": 4},
        headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["score"] == 4
    assert data["new_interval_days"] >= 1
    assert data["new_ease_factor"] >= 1.3
    assert data["next_review_at"] is not None


@pytest.mark.asyncio
async def test_score_invalid_range(client: AsyncClient):
    token, qid = await _setup_user_with_due_question(client, "rv3@test.com")
    resp = await client.post(f"/api/v1/review/{qid}/score",
        json={"score": 6},  # 超出范围
        headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_review_stats_returns_counts(client: AsyncClient):
    token, _ = await _setup_user_with_due_question(client, "rv4@test.com")
    resp = await client.get("/api/v1/review/stats",
        headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "due_count" in data
    assert "reviewed_today" in data
```

- [ ] **Step 2: 运行确认失败**

```bash
cd /workshop/ypjh/backend && uv run pytest tests/api/test_review.py -v
```

- [ ] **Step 3: 实现 review_service.py**

```python
# backend/services/review_service.py
from __future__ import annotations
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.s3_client import generate_presigned_url
from backend.core.sm2 import calculate_next_review
from backend.repositories.question_repository import QuestionRepository
from backend.repositories.review_repository import ReviewRepository
from backend.schemas.review import (
    ReviewQueueItemOut,
    ReviewQueueOut,
    ReviewStatsOut,
    ScoreOut,
)

_qrepo = QuestionRepository()
_rrepo = ReviewRepository()


class ReviewService:

    async def get_queue(
        self, session: AsyncSession, user_id: str, limit: int = 20
    ) -> ReviewQueueOut:
        questions = await _rrepo.get_due_questions(session, user_id, limit)
        items = []
        for q in questions:
            image_url = None
            expires_at = None
            if q.image_key:
                image_url = generate_presigned_url(q.image_key, 3600)
                expires_at = datetime.now(timezone.utc) + timedelta(seconds=3600)
            items.append(ReviewQueueItemOut(
                id=q.id,
                content=q.content,
                subject=q.subject,
                question_type=q.question_type,
                image_url=image_url,
                image_url_expires_at=expires_at,
                ease_factor=q.ease_factor,
                interval_days=q.interval_days,
                review_count=q.review_count,
            ))
        return ReviewQueueOut(items=items, total=len(items))

    async def submit_score(
        self,
        session: AsyncSession,
        question_id: str,
        user_id: str,
        score: int,
    ) -> ScoreOut:
        q = await _qrepo.get_by_id(session, question_id, user_id)
        if q is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail={"code": "NOT_FOUND", "message": "题目不存在"})

        prev_ef = q.ease_factor
        prev_interval = q.interval_days
        new_ef, new_interval, new_count = calculate_next_review(
            score, prev_ef, prev_interval, q.review_count
        )
        next_review_at = datetime.now(timezone.utc) + timedelta(days=new_interval)

        # 更新题目 SM-2 字段
        q.ease_factor = new_ef
        q.interval_days = new_interval
        q.review_count = new_count
        q.next_review_at = next_review_at
        await session.flush()

        # 记录复习日志
        await _rrepo.create_log(
            session,
            user_id=user_id,
            question_id=question_id,
            score=score,
            prev_ease_factor=prev_ef,
            new_ease_factor=new_ef,
            prev_interval=prev_interval,
            new_interval=new_interval,
        )

        return ScoreOut(
            question_id=question_id,
            score=score,
            new_ease_factor=new_ef,
            new_interval_days=new_interval,
            new_review_count=new_count,
            next_review_at=next_review_at,
        )

    async def get_stats(
        self, session: AsyncSession, user_id: str
    ) -> ReviewStatsOut:
        stats = await _rrepo.get_stats(session, user_id)
        return ReviewStatsOut(**stats)
```

- [ ] **Step 4: 实现 review.py 路由**

```python
# backend/api/v1/endpoints/review.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_session
from backend.core.security import get_current_user
from backend.models.user import User
from backend.schemas.common import ApiResponse
from backend.schemas.review import ReviewQueueOut, ReviewStatsOut, ScoreOut, ScoreRequest
from backend.services.review_service import ReviewService

router = APIRouter(prefix="/review", tags=["review"])
_svc = ReviewService()


@router.get("/queue", response_model=ApiResponse[ReviewQueueOut])
async def get_review_queue(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[ReviewQueueOut]:
    result = await _svc.get_queue(session, current_user.id)
    return ApiResponse(data=result)


@router.post("/{question_id}/score", response_model=ApiResponse[ScoreOut])
async def submit_score(
    question_id: str,
    body: ScoreRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[ScoreOut]:
    result = await _svc.submit_score(session, question_id, current_user.id, body.score)
    return ApiResponse(data=result)


@router.get("/stats", response_model=ApiResponse[ReviewStatsOut])
async def get_review_stats(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[ReviewStatsOut]:
    result = await _svc.get_stats(session, current_user.id)
    return ApiResponse(data=result)
```

- [ ] **Step 5: 更新 router.py**

```python
# backend/api/v1/router.py
from fastapi import APIRouter
from backend.api.v1.endpoints.auth import router as auth_router
from backend.api.v1.endpoints.questions_recognize import router as recognize_router
from backend.api.v1.endpoints.questions import router as questions_router
from backend.api.v1.endpoints.review import router as review_router

v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(auth_router)
v1_router.include_router(recognize_router)
v1_router.include_router(questions_router)
v1_router.include_router(review_router)
```

- [ ] **Step 6: 运行测试**

```bash
cd /workshop/ypjh/backend && uv run pytest tests/api/test_review.py -v
```

Expected: `4 passed`

- [ ] **Step 7: 运行全套测试**

```bash
cd /workshop/ypjh/backend && uv run pytest -v
```

Expected: 全部通过

- [ ] **Step 8: Commit**

```bash
git add backend/core/sm2.py backend/services/review_service.py backend/api/v1/endpoints/review.py backend/api/v1/router.py backend/tests/api/test_review.py
git commit -m "feat: SM-2 review API (queue/score/stats) with 5-level scoring (REQ-S1~S4)"
```
