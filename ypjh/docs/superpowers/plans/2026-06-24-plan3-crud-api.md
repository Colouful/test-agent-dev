# 错题本 Plan 3：题目 CRUD API

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 `/api/v1/questions` 完整 CRUD，含软删除、预签名 URL、用户隔离、分页。

**Architecture:** `QuestionRepository` 封装全部 DB 操作（含 user_id 过滤 + deleted_at 过滤）；`QuestionService` 调 Repository + 生成预签名 URL；路由层只做解析→调 Service→返回。

**Tech Stack:** FastAPI, SQLAlchemy 2 async, `python-multipart`, 已有 `s3_client.generate_presigned_url`

**前置条件:** Plan 1（models/question.py、get_current_user）+ Plan 2（recognition_service、s3_client）均已完成

## Global Constraints

- 所有查询必须带 `user_id` 过滤（R1）—— 禁止跨用户访问（BOLA）
- 软删除（R21）：DELETE 操作设 `deleted_at=now()`，不执行 `session.delete()`
- 响应中不暴露 S3 原始路径（R23）：含 image_key 的响应必须附 presigned URL
- `user_id` 从 JWT sub 提取（R22），路由函数不接受客户端传 user_id
- 分页默认 `limit=20, offset=0`，最大 `limit=100`

---

## 文件结构

```
backend/
├── repositories/
│   └── question_repository.py   # 所有 DB 操作（含 user_id 过滤）
├── schemas/
│   └── question.py              # QuestionCreate, QuestionUpdate, QuestionOut, QuestionListOut
├── services/
│   └── question_service.py      # 业务逻辑（presign + CRUD 编排）
└── api/v1/endpoints/
    └── questions.py             # GET/POST/PATCH/DELETE 路由
tests/api/
└── test_questions.py
```

---

### Task 1：Pydantic Schemas

**Files:**
- Create: `backend/schemas/question.py`

**Interfaces:**
- Produces:
  - `QuestionCreate`: content, correct_answer, wrong_answer?, subject?, question_type?, image_key?, confidence?, original_filename?
  - `QuestionUpdate`: 所有字段均可选
  - `QuestionOut`: 含 id, status, image_url?, image_url_expires_at?, created_at, next_review_at 等
  - `QuestionListOut`: items: list[QuestionOut], total: int, limit: int, offset: int

- [ ] **Step 1: 写 schema 单元测试**

```python
# backend/tests/test_question_schema.py
from backend.schemas.question import QuestionCreate, QuestionListOut, QuestionOut, QuestionUpdate


def test_question_create_minimal():
    q = QuestionCreate(content="题目", correct_answer="答案")
    assert q.wrong_answer is None
    assert q.subject is None


def test_question_create_full():
    q = QuestionCreate(
        content="题目",
        correct_answer="答案",
        wrong_answer="错误答案",
        subject="数学",
        question_type="single",
        image_key="user1/original/abc.jpg",
        confidence=0.9,
        original_filename="photo.jpg",
    )
    assert q.confidence == 0.9


def test_question_update_all_optional():
    # 空更新不报错
    u = QuestionUpdate()
    assert u.content is None


def test_question_out_has_image_url_fields():
    fields = QuestionOut.model_fields
    assert "image_url" in fields
    assert "image_url_expires_at" in fields
    # S3 原始 key 不在响应中暴露
    assert "image_key" not in fields


def test_question_list_out_structure():
    fields = QuestionListOut.model_fields
    assert "items" in fields
    assert "total" in fields
    assert "limit" in fields
    assert "offset" in fields
```

- [ ] **Step 2: 运行确认失败**

```bash
cd /workshop/ypjh/backend && uv run pytest tests/test_question_schema.py -v
```

Expected: `ImportError`

- [ ] **Step 3: 实现 question.py**

```python
# backend/schemas/question.py
from __future__ import annotations
from datetime import datetime
from typing import Literal
from pydantic import BaseModel


class QuestionCreate(BaseModel):
    content: str
    correct_answer: str
    wrong_answer: str | None = None
    subject: str | None = None
    question_type: str | None = None
    image_key: str | None = None
    confidence: float | None = None
    original_filename: str | None = None


class QuestionUpdate(BaseModel):
    content: str | None = None
    correct_answer: str | None = None
    wrong_answer: str | None = None
    subject: str | None = None
    question_type: str | None = None
    status: Literal["pending_review", "confirmed"] | None = None
    note: str | None = None


class QuestionOut(BaseModel):
    id: str
    user_id: str
    content: str
    correct_answer: str
    wrong_answer: str | None
    subject: str | None
    question_type: str | None
    status: str
    confidence: float | None
    note: str | None
    image_url: str | None
    image_url_expires_at: datetime | None
    ease_factor: float
    interval_days: int
    review_count: int
    next_review_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class QuestionListOut(BaseModel):
    items: list[QuestionOut]
    total: int
    limit: int
    offset: int
```

- [ ] **Step 4: 运行测试**

```bash
cd /workshop/ypjh/backend && uv run pytest tests/test_question_schema.py -v
```

Expected: `5 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/schemas/question.py backend/tests/test_question_schema.py
git commit -m "feat: add Question CRUD schemas (QuestionCreate/Update/Out/ListOut)"
```

---

### Task 2：QuestionRepository

**Files:**
- Create: `backend/repositories/question_repository.py`

**Interfaces:**
- Consumes: `AsyncSession`, `Question` ORM model
- Produces:
  - `create(session, user_id, data: QuestionCreate) -> Question`
  - `get_by_id(session, question_id, user_id) -> Question | None`
  - `list_by_user(session, user_id, limit, offset) -> tuple[list[Question], int]`
  - `update(session, question, data: QuestionUpdate) -> Question`
  - `soft_delete(session, question) -> None`

- [ ] **Step 1: 写 repository 测试**

```python
# backend/tests/test_question_repository.py
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.repositories.question_repository import QuestionRepository
from backend.schemas.question import QuestionCreate, QuestionUpdate


@pytest.mark.asyncio
async def test_create_question(session: AsyncSession):
    repo = QuestionRepository()
    q = await repo.create(session, "user-1", QuestionCreate(
        content="1+1=?", correct_answer="2"
    ))
    assert q.id is not None
    assert q.user_id == "user-1"
    assert q.deleted_at is None
    assert q.ease_factor == 2.5
    assert q.interval_days == 1


@pytest.mark.asyncio
async def test_get_by_id_user_isolation(session: AsyncSession):
    repo = QuestionRepository()
    q = await repo.create(session, "user-1", QuestionCreate(
        content="题目", correct_answer="答案"
    ))
    # 跨用户查询返回 None（R1）
    result = await repo.get_by_id(session, q.id, "user-2")
    assert result is None
    # 正确用户可以找到
    result = await repo.get_by_id(session, q.id, "user-1")
    assert result is not None


@pytest.mark.asyncio
async def test_list_by_user_excludes_deleted(session: AsyncSession):
    repo = QuestionRepository()
    q1 = await repo.create(session, "user-1", QuestionCreate(
        content="题目1", correct_answer="A"
    ))
    q2 = await repo.create(session, "user-1", QuestionCreate(
        content="题目2", correct_answer="B"
    ))
    await repo.soft_delete(session, q2)

    items, total = await repo.list_by_user(session, "user-1", limit=10, offset=0)
    assert total == 1
    assert items[0].id == q1.id


@pytest.mark.asyncio
async def test_soft_delete_sets_deleted_at(session: AsyncSession):
    repo = QuestionRepository()
    q = await repo.create(session, "user-1", QuestionCreate(
        content="题目", correct_answer="答案"
    ))
    await repo.soft_delete(session, q)
    assert q.deleted_at is not None


@pytest.mark.asyncio
async def test_update_question(session: AsyncSession):
    repo = QuestionRepository()
    q = await repo.create(session, "user-1", QuestionCreate(
        content="原内容", correct_answer="答案"
    ))
    updated = await repo.update(session, q, QuestionUpdate(content="新内容"))
    assert updated.content == "新内容"
```

- [ ] **Step 2: 运行确认失败**

```bash
cd /workshop/ypjh/backend && uv run pytest tests/test_question_repository.py -v
```

- [ ] **Step 3: 实现 question_repository.py**

```python
# backend/repositories/question_repository.py
from __future__ import annotations
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.question import Question
from backend.schemas.question import QuestionCreate, QuestionUpdate


class QuestionRepository:

    async def create(
        self, session: AsyncSession, user_id: str, data: QuestionCreate
    ) -> Question:
        q = Question(
            id=str(uuid.uuid4()),
            user_id=user_id,
            content=data.content,
            correct_answer=data.correct_answer,
            wrong_answer=data.wrong_answer,
            subject=data.subject,
            question_type=data.question_type,
            image_key=data.image_key,
            confidence=data.confidence,
            original_filename=data.original_filename,
            status="confirmed",
            ease_factor=2.5,
            interval_days=1,
            review_count=0,
        )
        session.add(q)
        await session.flush()
        return q

    async def get_by_id(
        self, session: AsyncSession, question_id: str, user_id: str
    ) -> Question | None:
        stmt = (
            select(Question)
            .where(
                Question.id == question_id,
                Question.user_id == user_id,  # R1: 用户隔离
                Question.deleted_at.is_(None),  # R21: 软删除过滤
            )
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_user(
        self,
        session: AsyncSession,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Question], int]:
        base = select(Question).where(
            Question.user_id == user_id,  # R1
            Question.deleted_at.is_(None),  # R21
        )
        count_stmt = select(func.count()).select_from(base.subquery())
        total: int = (await session.execute(count_stmt)).scalar_one()
        items_stmt = base.order_by(Question.created_at.desc()).limit(limit).offset(offset)
        items = list((await session.execute(items_stmt)).scalars().all())
        return items, total

    async def update(
        self, session: AsyncSession, question: Question, data: QuestionUpdate
    ) -> Question:
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(question, field, value)
        question.updated_at = datetime.now(timezone.utc)
        await session.flush()
        return question

    async def soft_delete(
        self, session: AsyncSession, question: Question
    ) -> None:
        question.deleted_at = datetime.now(timezone.utc)
        await session.flush()
```

- [ ] **Step 4: 运行测试**

```bash
cd /workshop/ypjh/backend && uv run pytest tests/test_question_repository.py -v
```

Expected: `5 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/repositories/question_repository.py backend/tests/test_question_repository.py
git commit -m "feat: QuestionRepository with user isolation, soft delete, pagination (R1/R21)"
```

---

### Task 3：QuestionService（含 presign）

**Files:**
- Create: `backend/services/question_service.py`

**Interfaces:**
- Consumes: `QuestionRepository`, `generate_presigned_url`
- Produces:
  - `get_list(session, user_id, limit, offset) -> QuestionListOut`
  - `get_one(session, question_id, user_id) -> QuestionOut`
  - `create(session, user_id, data) -> QuestionOut`
  - `update(session, question_id, user_id, data) -> QuestionOut`
  - `delete(session, question_id, user_id) -> None`

- [ ] **Step 1: 写 service 测试**

```python
# backend/tests/test_question_service.py
import os, pytest
os.environ["MOCK_BEDROCK"] = "true"

from sqlalchemy.ext.asyncio import AsyncSession
from backend.services.question_service import QuestionService
from backend.schemas.question import QuestionCreate, QuestionUpdate


@pytest.mark.asyncio
async def test_create_returns_out_schema(session: AsyncSession):
    svc = QuestionService()
    out = await svc.create(session, "user-1", QuestionCreate(
        content="题目", correct_answer="答案"
    ))
    assert out.id is not None
    assert out.image_url is None      # 无图片时为 None


@pytest.mark.asyncio
async def test_create_with_image_returns_presigned_url(session: AsyncSession):
    svc = QuestionService()
    out = await svc.create(session, "user-1", QuestionCreate(
        content="题目", correct_answer="答案",
        image_key="user-1/original/abc.jpg",
    ))
    # R23: 响应包含 presigned URL，不暴露原始 S3 路径
    assert out.image_url is not None
    assert out.image_url.startswith("https://")
    assert out.image_url_expires_at is not None
    assert "user-1/original/abc.jpg" not in (out.image_url or "")


@pytest.mark.asyncio
async def test_get_one_not_found_raises(session: AsyncSession):
    from fastapi import HTTPException
    svc = QuestionService()
    with pytest.raises(HTTPException) as exc_info:
        await svc.get_one(session, "nonexistent-id", "user-1")
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_then_not_found(session: AsyncSession):
    from fastapi import HTTPException
    svc = QuestionService()
    out = await svc.create(session, "user-1", QuestionCreate(
        content="题目", correct_answer="答案"
    ))
    await svc.delete(session, out.id, "user-1")
    with pytest.raises(HTTPException):
        await svc.get_one(session, out.id, "user-1")
```

- [ ] **Step 2: 运行确认失败**

```bash
cd /workshop/ypjh/backend && uv run pytest tests/test_question_service.py -v
```

- [ ] **Step 3: 实现 question_service.py**

```python
# backend/services/question_service.py
from __future__ import annotations
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.s3_client import generate_presigned_url
from backend.repositories.question_repository import QuestionRepository
from backend.schemas.question import (
    QuestionCreate,
    QuestionListOut,
    QuestionOut,
    QuestionUpdate,
)

_repo = QuestionRepository()
_PRESIGN_EXPIRES = 3600  # R23: ≤1h


def _to_out(question) -> QuestionOut:
    image_url = None
    image_url_expires_at = None
    if question.image_key:
        image_url = generate_presigned_url(question.image_key, _PRESIGN_EXPIRES)
        image_url_expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=_PRESIGN_EXPIRES
        )
    return QuestionOut(
        id=question.id,
        user_id=question.user_id,
        content=question.content,
        correct_answer=question.correct_answer,
        wrong_answer=question.wrong_answer,
        subject=question.subject,
        question_type=question.question_type,
        status=question.status,
        confidence=question.confidence,
        note=question.note,
        image_url=image_url,
        image_url_expires_at=image_url_expires_at,
        ease_factor=question.ease_factor,
        interval_days=question.interval_days,
        review_count=question.review_count,
        next_review_at=question.next_review_at,
        created_at=question.created_at,
        updated_at=question.updated_at,
    )


class QuestionService:

    async def get_list(
        self,
        session: AsyncSession,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> QuestionListOut:
        items, total = await _repo.list_by_user(session, user_id, limit, offset)
        return QuestionListOut(
            items=[_to_out(q) for q in items],
            total=total,
            limit=limit,
            offset=offset,
        )

    async def get_one(
        self, session: AsyncSession, question_id: str, user_id: str
    ) -> QuestionOut:
        q = await _repo.get_by_id(session, question_id, user_id)
        if q is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail={"code": "NOT_FOUND", "message": "题目不存在"})
        return _to_out(q)

    async def create(
        self, session: AsyncSession, user_id: str, data: QuestionCreate
    ) -> QuestionOut:
        q = await _repo.create(session, user_id, data)
        return _to_out(q)

    async def update(
        self,
        session: AsyncSession,
        question_id: str,
        user_id: str,
        data: QuestionUpdate,
    ) -> QuestionOut:
        q = await _repo.get_by_id(session, question_id, user_id)
        if q is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail={"code": "NOT_FOUND", "message": "题目不存在"})
        updated = await _repo.update(session, q, data)
        return _to_out(updated)

    async def delete(
        self, session: AsyncSession, question_id: str, user_id: str
    ) -> None:
        q = await _repo.get_by_id(session, question_id, user_id)
        if q is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail={"code": "NOT_FOUND", "message": "题目不存在"})
        await _repo.soft_delete(session, q)
```

- [ ] **Step 4: 运行测试**

```bash
cd /workshop/ypjh/backend && uv run pytest tests/test_question_service.py -v
```

Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/services/question_service.py backend/tests/test_question_service.py
git commit -m "feat: QuestionService with presigned URL generation (R23)"
```

---

### Task 4：Questions API 路由

**Files:**
- Create: `backend/api/v1/endpoints/questions.py`
- Modify: `backend/api/v1/router.py`（添加 questions_router）

**Interfaces:**
- Produces:
  - `GET /api/v1/questions` → `ApiResponse[QuestionListOut]`
  - `POST /api/v1/questions` → `ApiResponse[QuestionOut]` 201
  - `GET /api/v1/questions/{id}` → `ApiResponse[QuestionOut]`
  - `PATCH /api/v1/questions/{id}` → `ApiResponse[QuestionOut]`
  - `DELETE /api/v1/questions/{id}` → 204

- [ ] **Step 1: 写 API 集成测试**

```python
# backend/tests/api/test_questions.py
import pytest
from httpx import AsyncClient


async def _get_token(client: AsyncClient, email: str) -> str:
    await client.post("/api/v1/auth/register",
        json={"email": email, "password": "password123"})
    resp = await client.post("/api/v1/auth/login",
        json={"email": email, "password": "password123"})
    return resp.json()["data"]["access_token"]


@pytest.mark.asyncio
async def test_create_question(client: AsyncClient):
    token = await _get_token(client, "q1@test.com")
    resp = await client.post(
        "/api/v1/questions",
        json={"content": "1+1=?", "correct_answer": "2"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["id"] is not None
    assert data["content"] == "1+1=?"


@pytest.mark.asyncio
async def test_list_questions_user_isolation(client: AsyncClient):
    token1 = await _get_token(client, "q2@test.com")
    token2 = await _get_token(client, "q3@test.com")
    await client.post("/api/v1/questions",
        json={"content": "user1题目", "correct_answer": "A"},
        headers={"Authorization": f"Bearer {token1}"})
    resp = await client.get("/api/v1/questions",
        headers={"Authorization": f"Bearer {token2}"})
    assert resp.json()["data"]["total"] == 0  # R1: 隔离


@pytest.mark.asyncio
async def test_delete_soft_delete(client: AsyncClient):
    token = await _get_token(client, "q4@test.com")
    create = await client.post("/api/v1/questions",
        json={"content": "题目", "correct_answer": "答案"},
        headers={"Authorization": f"Bearer {token}"})
    qid = create.json()["data"]["id"]

    del_resp = await client.delete(f"/api/v1/questions/{qid}",
        headers={"Authorization": f"Bearer {token}"})
    assert del_resp.status_code == 204

    # 软删除后查询返回 404
    get_resp = await client.get(f"/api/v1/questions/{qid}",
        headers={"Authorization": f"Bearer {token}"})
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_update_question(client: AsyncClient):
    token = await _get_token(client, "q5@test.com")
    create = await client.post("/api/v1/questions",
        json={"content": "原内容", "correct_answer": "答案"},
        headers={"Authorization": f"Bearer {token}"})
    qid = create.json()["data"]["id"]

    patch = await client.patch(f"/api/v1/questions/{qid}",
        json={"content": "新内容"},
        headers={"Authorization": f"Bearer {token}"})
    assert patch.status_code == 200
    assert patch.json()["data"]["content"] == "新内容"
```

- [ ] **Step 2: 运行确认失败**

```bash
cd /workshop/ypjh/backend && uv run pytest tests/api/test_questions.py -v
```

- [ ] **Step 3: 实现 questions.py 路由**

```python
# backend/api/v1/endpoints/questions.py
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_session
from backend.core.security import get_current_user
from backend.models.user import User
from backend.schemas.common import ApiResponse
from backend.schemas.question import (
    QuestionCreate,
    QuestionListOut,
    QuestionOut,
    QuestionUpdate,
)
from backend.services.question_service import QuestionService

router = APIRouter(prefix="/questions", tags=["questions"])
_svc = QuestionService()


@router.get("", response_model=ApiResponse[QuestionListOut])
async def list_questions(
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[QuestionListOut]:
    result = await _svc.get_list(session, current_user.id, limit, offset)
    return ApiResponse(data=result)


@router.post("", response_model=ApiResponse[QuestionOut], status_code=201)
async def create_question(
    body: QuestionCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[QuestionOut]:
    result = await _svc.create(session, current_user.id, body)
    return ApiResponse(data=result)


@router.get("/{question_id}", response_model=ApiResponse[QuestionOut])
async def get_question(
    question_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[QuestionOut]:
    result = await _svc.get_one(session, question_id, current_user.id)
    return ApiResponse(data=result)


@router.patch("/{question_id}", response_model=ApiResponse[QuestionOut])
async def update_question(
    question_id: str,
    body: QuestionUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[QuestionOut]:
    result = await _svc.update(session, question_id, current_user.id, body)
    return ApiResponse(data=result)


@router.delete("/{question_id}", status_code=204)
async def delete_question(
    question_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    await _svc.delete(session, question_id, current_user.id)
```

- [ ] **Step 4: 更新 router.py**

```python
# backend/api/v1/router.py
from fastapi import APIRouter
from backend.api.v1.endpoints.auth import router as auth_router
from backend.api.v1.endpoints.questions_recognize import router as recognize_router
from backend.api.v1.endpoints.questions import router as questions_router

v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(auth_router)
v1_router.include_router(recognize_router)
v1_router.include_router(questions_router)
```

- [ ] **Step 5: 运行测试**

```bash
cd /workshop/ypjh/backend && uv run pytest tests/api/test_questions.py -v
```

Expected: `4 passed`

- [ ] **Step 6: 运行全套测试**

```bash
cd /workshop/ypjh/backend && uv run pytest -v
```

Expected: 全部通过

- [ ] **Step 7: Commit**

```bash
git add backend/api/v1/endpoints/questions.py backend/api/v1/router.py backend/tests/api/test_questions.py
git commit -m "feat: Questions CRUD API with soft delete, presigned URLs, user isolation (R1/R21/R23)"
```
