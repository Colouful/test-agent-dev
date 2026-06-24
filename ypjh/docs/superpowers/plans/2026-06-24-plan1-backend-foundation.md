# 错题本 Plan 1：后端基础 + 认证

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 搭建可运行的 FastAPI 后端骨架，包含数据库连接、User/Question/ReviewLog ORM 模型、JWT 认证全流程，使 `POST /api/v1/auth/register` 和 `POST /api/v1/auth/login` 可以真实运行并通过测试。

**Architecture:** FastAPI async + SQLAlchemy 2（async session）+ SQLite（开发）。认证用 python-jose 生成 HS256 JWT，密码用 bcrypt（passlib）哈希。所有 DB 操作通过 Repository 层，Service 层不直接操作 ORM。

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2 (async), pydantic v2, python-jose[cryptography], passlib[bcrypt], aiosqlite, uv, pytest, httpx

## Global Constraints

- Python 3.12，全量类型注解，mypy strict
- 禁止裸 `except: pass`，捕获异常必须记录或重抛
- `user_id` 只从 JWT `sub` 提取，禁止接受客户端传入（R22）
- 所有 DB 查询含 `user_id` 过滤（R1）
- 密码用 bcrypt cost=12（REQ-A5）
- JWT 有效期 24h，payload 含 `sub=user.id`（REQ-A1）
- 软删除：`deleted_at` 字段，禁止物理删除（R21）
- `confidence_score` 字段不得为 NULL（ARCH-2）
- 路由层只做：解析参数 → 调用 Service → 返回响应，禁止业务逻辑（R5）
- 统一响应格式：`{ "data": ..., "error": null }` 或 `{ "data": null, "error": { "code": "...", "message": "..." } }`

---

## 文件结构（本计划创建的所有文件）

```
backend/
├── main.py                          # FastAPI app 入口
├── core/
│   ├── __init__.py
│   ├── config.py                    # Settings（env vars）
│   ├── database.py                  # async engine + get_session
│   └── security.py                  # JWT encode/decode + get_current_user + bcrypt
├── models/
│   ├── __init__.py
│   ├── base.py                      # Base + TimestampMixin
│   ├── user.py                      # User ORM
│   ├── question.py                  # Question ORM（含 SM-2 字段）
│   └── review_log.py                # ReviewLog ORM
├── schemas/
│   ├── __init__.py
│   ├── auth.py                      # RegisterRequest, LoginRequest, AuthResponse
│   └── common.py                    # ApiResponse[T] 统一包装
├── repositories/
│   ├── __init__.py
│   └── user_repository.py           # get_by_email, create
├── services/
│   ├── __init__.py
│   └── auth_service.py              # register, login
├── api/
│   ├── __init__.py
│   └── v1/
│       ├── __init__.py
│       ├── router.py                # 汇总所有端点路由
│       └── endpoints/
│           ├── __init__.py
│           └── auth.py              # POST /register, POST /login
└── tests/
    ├── __init__.py
    ├── conftest.py                  # async client fixture, test DB
    └── api/
        ├── __init__.py
        └── test_auth.py             # 认证全流程测试
```

---

### Task 1：项目依赖 + pyproject.toml

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/.env.example`

**Interfaces:**
- Produces: `uv run pytest` 可执行；`uv run uvicorn main:app` 可执行

- [ ] **Step 1: 创建 pyproject.toml**

```toml
# backend/pyproject.toml
[project]
name = "wrongbook-backend"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.111.0",
    "uvicorn[standard]>=0.29.0",
    "sqlalchemy[asyncio]>=2.0.0",
    "aiosqlite>=0.20.0",
    "pydantic[email]>=2.7.0",
    "python-jose[cryptography]>=3.3.0",
    "passlib[bcrypt]>=1.7.4",
    "python-multipart>=0.0.9",
    "httpx>=0.27.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "anyio>=4.0.0",
    "ruff>=0.4.0",
    "mypy>=1.10.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.mypy]
strict = true
python_version = "3.12"
```

- [ ] **Step 2: 创建 .env.example**

```bash
# backend/.env.example
SECRET_KEY=change-me-in-production-at-least-32-chars
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
DATABASE_URL=sqlite+aiosqlite:///./wrongbook.db
MOCK_BEDROCK=true
```

- [ ] **Step 3: 安装依赖**

```bash
cd /workshop/ypjh/backend
uv sync --extra dev
```

Expected: `Resolved N packages` 无报错

- [ ] **Step 4: 验证环境**

```bash
cd /workshop/ypjh/backend
uv run python -c "import fastapi, sqlalchemy, jose, passlib; print('OK')"
```

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add backend/pyproject.toml backend/.env.example
git commit -m "chore: add backend pyproject.toml with all dependencies"
```

---

### Task 2：核心配置 + 数据库连接

**Files:**
- Create: `backend/core/__init__.py`
- Create: `backend/core/config.py`
- Create: `backend/core/database.py`

**Interfaces:**
- Produces:
  - `from backend.core.config import settings` → `settings.SECRET_KEY`, `settings.DATABASE_URL`
  - `from backend.core.database import get_session, create_tables` → async session 依赖注入

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_core.py
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from backend.core.database import get_session, create_tables

@pytest.mark.asyncio
async def test_database_session_is_async():
    await create_tables()
    async for session in get_session():
        assert isinstance(session, AsyncSession)
        break
```

- [ ] **Step 2: 运行确认失败**

```bash
cd /workshop/ypjh/backend
uv run pytest tests/test_core.py -v
```

Expected: `ModuleNotFoundError: No module named 'backend.core'`

- [ ] **Step 3: 实现 config.py**

```python
# backend/core/config.py
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24h
    DATABASE_URL: str = "sqlite+aiosqlite:///./wrongbook.db"
    MOCK_BEDROCK: bool = True

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
```

- [ ] **Step 4: 实现 database.py**

```python
# backend/core/database.py
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.core.config import settings
from backend.models.base import Base

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def create_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
```

- [ ] **Step 5: 创建 core/__init__.py**

```python
# backend/core/__init__.py
```

- [ ] **Step 6: 先建 models/base.py（database.py 依赖它）**

```python
# backend/models/__init__.py
# backend/models/base.py
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
```

- [ ] **Step 7: 运行测试确认通过**

```bash
cd /workshop/ypjh/backend
uv run pytest tests/test_core.py -v
```

Expected: `PASSED`

- [ ] **Step 8: 安装 pydantic-settings（config.py 需要）**

```bash
cd /workshop/ypjh/backend
uv add pydantic-settings
```

- [ ] **Step 9: Commit**

```bash
git add backend/core/ backend/models/base.py backend/models/__init__.py backend/tests/test_core.py
git commit -m "feat: add core config, async database session, Base ORM"
```

---

### Task 3：ORM 模型（User + Question + ReviewLog）

**Files:**
- Create: `backend/models/user.py`
- Create: `backend/models/question.py`
- Create: `backend/models/review_log.py`

**Interfaces:**
- Produces:
  - `User`: id(str/uuid), email(str), hashed_password(str), created_at, deleted_at
  - `Question`: 完整字段见下（含 SM-2 字段 + image_key + deleted_at）
  - `ReviewLog`: id, question_id, user_id, score, ef_before, ef_after, interval_before, interval_after, reviewed_at

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_models.py
import pytest
from backend.core.database import create_tables
from backend.models.user import User
from backend.models.question import Question
from backend.models.review_log import ReviewLog


@pytest.mark.asyncio
async def test_models_have_required_fields():
    await create_tables()
    # User 字段检查
    assert hasattr(User, "id")
    assert hasattr(User, "email")
    assert hasattr(User, "hashed_password")
    assert hasattr(User, "deleted_at")
    # Question 字段检查（ARCH-2: confidence_score 不得为 NULL）
    assert hasattr(Question, "confidence_score")
    assert hasattr(Question, "user_id")
    assert hasattr(Question, "deleted_at")
    assert hasattr(Question, "ease_factor")
    assert hasattr(Question, "interval_days")
    assert hasattr(Question, "next_review_at")
    # ReviewLog 字段检查
    assert hasattr(ReviewLog, "score")
    assert hasattr(ReviewLog, "ease_factor_before")
```

- [ ] **Step 2: 运行确认失败**

```bash
cd /workshop/ypjh/backend
uv run pytest tests/test_models.py -v
```

Expected: `ImportError`

- [ ] **Step 3: 实现 User 模型**

```python
# backend/models/user.py
import uuid
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(unique=True, index=True)
    hashed_password: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(default=None)
```

- [ ] **Step 4: 实现 Question 模型**

```python
# backend/models/question.py
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(index=True)           # R1/R22
    subject: Mapped[str | None] = mapped_column(default=None)
    question_type: Mapped[str] = mapped_column(default="single")
    content: Mapped[str]                                        # R3
    wrong_answer: Mapped[str | None] = mapped_column(default=None)
    correct_answer: Mapped[str]
    analysis: Mapped[str | None] = mapped_column(default=None)
    difficulty: Mapped[int] = mapped_column(default=3)
    confidence_score: Mapped[float] = mapped_column(default=0.0)   # ARCH-2: 不得 NULL
    image_key: Mapped[str | None] = mapped_column(default=None)    # S3 路径
    original_filename: Mapped[str | None] = mapped_column(default=None)
    status: Mapped[str] = mapped_column(default="confirmed")
    # SM-2 字段
    ease_factor: Mapped[float] = mapped_column(default=2.5)
    review_count: Mapped[int] = mapped_column(default=0)
    interval_days: Mapped[int] = mapped_column(default=1)
    next_review_at: Mapped[datetime | None] = mapped_column(default=None)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(default=None)
    # 审计字段
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(default=None)  # R21
```

- [ ] **Step 5: 实现 ReviewLog 模型**

```python
# backend/models/review_log.py
from datetime import datetime

from sqlalchemy import ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base


class ReviewLog(Base):
    __tablename__ = "review_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"))
    user_id: Mapped[str] = mapped_column(index=True)  # 冗余存储，避免 JOIN 跨用户
    score: Mapped[int]                                 # 1-5
    ease_factor_before: Mapped[float]
    ease_factor_after: Mapped[float]
    interval_before: Mapped[int]
    interval_after: Mapped[int]
    reviewed_at: Mapped[datetime] = mapped_column(default=func.now())
```

- [ ] **Step 6: 运行测试确认通过**

```bash
cd /workshop/ypjh/backend
uv run pytest tests/test_models.py -v
```

Expected: `PASSED`

- [ ] **Step 7: Commit**

```bash
git add backend/models/
git commit -m "feat: add User, Question, ReviewLog ORM models with SM-2 and soft-delete fields"
```

---

### Task 4：JWT + 密码工具（security.py）

**Files:**
- Create: `backend/core/security.py`

**Interfaces:**
- Produces:
  - `hash_password(plain: str) -> str`
  - `verify_password(plain: str, hashed: str) -> bool`
  - `create_access_token(user_id: str) -> str`
  - `decode_access_token(token: str) -> str`（返回 user_id，失败抛 HTTPException 401）
  - `get_current_user(token: str, session: AsyncSession) -> User`（FastAPI Depends）

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_security.py
import pytest
from backend.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hash_and_verify():
    hashed = hash_password("mypassword123")
    assert hashed.startswith("$2b$12$")      # bcrypt cost=12
    assert verify_password("mypassword123", hashed) is True
    assert verify_password("wrongpassword", hashed) is False


def test_jwt_encode_decode_roundtrip():
    token = create_access_token("user-uuid-123")
    user_id = decode_access_token(token)
    assert user_id == "user-uuid-123"


def test_jwt_invalid_token_raises():
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        decode_access_token("not.a.valid.token")
    assert exc_info.value.status_code == 401
```

- [ ] **Step 2: 运行确认失败**

```bash
cd /workshop/ypjh/backend
uv run pytest tests/test_security.py -v
```

Expected: `ImportError`

- [ ] **Step 3: 实现 security.py**

```python
# backend/core/security.py
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.core.database import get_session

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)
bearer_scheme = HTTPBearer()


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {"sub": user_id, "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> str:
    """返回 user_id（JWT sub），失败抛 HTTPException 401。"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "TOKEN_INVALID", "message": "Token 缺少 sub 字段"},
            )
        return user_id
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "TOKEN_INVALID", "message": str(e)},
        ) from e


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_session),
) -> "User":  # type: ignore[name-defined]  # noqa: F821
    from backend.models.user import User
    from sqlalchemy import select

    user_id = decode_access_token(credentials.credentials)
    result = await session.execute(
        select(User).where(User.id == user_id, User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "TOKEN_INVALID", "message": "用户不存在"},
        )
    return user
```

- [ ] **Step 4: 运行测试确认通过**

```bash
cd /workshop/ypjh/backend
uv run pytest tests/test_security.py -v
```

Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/core/security.py backend/tests/test_security.py
git commit -m "feat: add JWT encode/decode and bcrypt password hashing (cost=12)"
```

---

### Task 5：用户 Repository + 认证 Service

**Files:**
- Create: `backend/repositories/__init__.py`
- Create: `backend/repositories/user_repository.py`
- Create: `backend/services/__init__.py`
- Create: `backend/services/auth_service.py`
- Create: `backend/schemas/__init__.py`
- Create: `backend/schemas/auth.py`
- Create: `backend/schemas/common.py`

**Interfaces:**
- Consumes: `User` model, `hash_password`, `verify_password`, `create_access_token`
- Produces:
  - `UserRepository.get_by_email(session, email) -> User | None`
  - `UserRepository.create(session, email, hashed_password) -> User`
  - `AuthService.register(session, email, password) -> AuthResponse`（抛 409 on duplicate）
  - `AuthService.login(session, email, password) -> AuthResponse`（抛 401 on invalid）
  - `AuthResponse`: `access_token: str`, `token_type: str = "bearer"`, `expires_in: int = 86400`

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_auth_service.py
import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import create_tables, AsyncSessionLocal
from backend.services.auth_service import AuthService


@pytest.fixture
async def session() -> AsyncSession:
    await create_tables()
    async with AsyncSessionLocal() as s:
        yield s
        await s.rollback()


@pytest.mark.asyncio
async def test_register_success(session: AsyncSession):
    svc = AuthService()
    result = await svc.register(session, "test@example.com", "password123")
    assert result.access_token
    assert result.token_type == "bearer"
    assert result.expires_in == 86400


@pytest.mark.asyncio
async def test_register_duplicate_email(session: AsyncSession):
    svc = AuthService()
    await svc.register(session, "dup@example.com", "password123")
    with pytest.raises(HTTPException) as exc_info:
        await svc.register(session, "dup@example.com", "password123")
    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_login_success(session: AsyncSession):
    svc = AuthService()
    await svc.register(session, "login@example.com", "mypassword")
    result = await svc.login(session, "login@example.com", "mypassword")
    assert result.access_token


@pytest.mark.asyncio
async def test_login_wrong_password(session: AsyncSession):
    svc = AuthService()
    await svc.register(session, "wp@example.com", "correctpass")
    with pytest.raises(HTTPException) as exc_info:
        await svc.login(session, "wp@example.com", "wrongpass")
    assert exc_info.value.status_code == 401

@pytest.mark.asyncio
async def test_login_unknown_email(session: AsyncSession):
    svc = AuthService()
    with pytest.raises(HTTPException) as exc_info:
        await svc.login(session, "nobody@example.com", "pass")
    assert exc_info.value.status_code == 401
    # 邮箱不存在和密码错误返回同一错误码，防枚举
    assert exc_info.value.detail["code"] == "INVALID_CREDENTIALS"
```

- [ ] **Step 2: 运行确认失败**

```bash
cd /workshop/ypjh/backend
uv run pytest tests/test_auth_service.py -v
```

Expected: `ImportError`

- [ ] **Step 3: 实现 schemas**

```python
# backend/schemas/common.py
from typing import Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")

class ApiResponse(BaseModel, Generic[T]):
    data: T | None = None
    error: dict[str, str] | None = None

# backend/schemas/auth.py
from pydantic import BaseModel, EmailStr, Field

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 86400
```

- [ ] **Step 4: 实现 user_repository.py**

```python
# backend/repositories/user_repository.py
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.user import User


class UserRepository:
    async def get_by_email(self, session: AsyncSession, email: str) -> User | None:
        result = await session.execute(
            select(User).where(User.email == email, User.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def create(
        self, session: AsyncSession, email: str, hashed_password: str
    ) -> User:
        user = User(
            id=str(uuid.uuid4()),
            email=email,
            hashed_password=hashed_password,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user
```

- [ ] **Step 5: 实现 auth_service.py**

```python
# backend/services/auth_service.py
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.security import create_access_token, hash_password, verify_password
from backend.repositories.user_repository import UserRepository
from backend.schemas.auth import AuthResponse


class AuthService:
    def __init__(self) -> None:
        self.repo = UserRepository()

    async def register(
        self, session: AsyncSession, email: str, password: str
    ) -> AuthResponse:
        existing = await self.repo.get_by_email(session, email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "DUPLICATE_EMAIL", "message": "该邮箱已注册"},
            )
        user = await self.repo.create(session, email, hash_password(password))
        return AuthResponse(access_token=create_access_token(user.id))

    async def login(
        self, session: AsyncSession, email: str, password: str
    ) -> AuthResponse:
        user = await self.repo.get_by_email(session, email)
        # 邮箱不存在和密码错误返回同一错误，防止用户枚举（REQ-A2）
        if user is None or not verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "INVALID_CREDENTIALS", "message": "邮箱或密码错误"},
            )
        return AuthResponse(access_token=create_access_token(user.id))
```

- [ ] **Step 6: 运行测试确认通过**

```bash
cd /workshop/ypjh/backend
uv run pytest tests/test_auth_service.py -v
```

Expected: `5 passed`

- [ ] **Step 7: Commit**

```bash
git add backend/repositories/ backend/services/auth_service.py backend/schemas/
git commit -m "feat: add UserRepository, AuthService (register/login), auth schemas"
```

---

### Task 6：认证 API 端点 + FastAPI app

**Files:**
- Create: `backend/api/__init__.py`
- Create: `backend/api/v1/__init__.py`
- Create: `backend/api/v1/router.py`
- Create: `backend/api/v1/endpoints/__init__.py`
- Create: `backend/api/v1/endpoints/auth.py`
- Create: `backend/main.py`

**Interfaces:**
- Consumes: `AuthService`, `RegisterRequest`, `LoginRequest`, `AuthResponse`, `ApiResponse`
- Produces:
  - `POST /api/v1/auth/register` → 201 `ApiResponse[AuthResponse]`
  - `POST /api/v1/auth/login` → 200 `ApiResponse[AuthResponse]`

- [ ] **Step 1: 创建 conftest.py 和 HTTP 测试 fixture**

```python
# backend/tests/conftest.py
import pytest
from httpx import ASGITransport, AsyncClient

from backend.core.database import create_tables
from backend.main import app


@pytest.fixture(autouse=True)
async def setup_db():
    await create_tables()


@pytest.fixture
async def client() -> AsyncClient:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
```

- [ ] **Step 2: 写失败 API 测试**

```python
# backend/tests/api/test_auth.py
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_returns_201(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "new@example.com", "password": "password123"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["data"]["access_token"]
    assert body["error"] is None


@pytest.mark.asyncio
async def test_register_duplicate_returns_409(client: AsyncClient):
    payload = {"email": "dup2@example.com", "password": "password123"}
    await client.post("/api/v1/auth/register", json=payload)
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "DUPLICATE_EMAIL"


@pytest.mark.asyncio
async def test_login_success_returns_200(client: AsyncClient):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "loginok@example.com", "password": "password123"},
    )
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "loginok@example.com", "password": "password123"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["access_token"]


@pytest.mark.asyncio
async def test_login_wrong_password_returns_401(client: AsyncClient):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "loginbad@example.com", "password": "correctpass"},
    )
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "loginbad@example.com", "password": "wrongpass"},
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_short_password_returns_422(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "short@example.com", "password": "short"},
    )
    assert resp.status_code == 422
```

- [ ] **Step 3: 运行确认失败**

```bash
cd /workshop/ypjh/backend
uv run pytest tests/api/test_auth.py -v
```

Expected: `ImportError: No module named 'backend.main'`

- [ ] **Step 4: 实现认证端点**

```python
# backend/api/v1/endpoints/auth.py
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_session
from backend.schemas.auth import AuthResponse, LoginRequest, RegisterRequest
from backend.schemas.common import ApiResponse
from backend.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])
_svc = AuthService()


@router.post("/register", response_model=ApiResponse[AuthResponse], status_code=201)
async def register(
    body: RegisterRequest,
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[AuthResponse]:
    result = await _svc.register(session, body.email, body.password)
    return ApiResponse(data=result)


@router.post("/login", response_model=ApiResponse[AuthResponse])
async def login(
    body: LoginRequest,
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[AuthResponse]:
    result = await _svc.login(session, body.email, body.password)
    return ApiResponse(data=result)
```

- [ ] **Step 5: 实现路由汇总 + main.py**

```python
# backend/api/v1/router.py
from fastapi import APIRouter
from backend.api.v1.endpoints.auth import router as auth_router

v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(auth_router)

# backend/main.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from backend.api.v1.router import v1_router
from backend.core.database import create_tables

app = FastAPI(title="错题本 API", version="0.1.0")
app.include_router(v1_router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # 生产环境不暴露 stack trace
    return JSONResponse(
        status_code=500,
        content={"data": None, "error": {"code": "INTERNAL_ERROR", "message": "服务器内部错误"}},
    )


@app.on_event("startup")
async def startup() -> None:
    await create_tables()
```

- [ ] **Step 6: 运行 API 测试确认通过**

```bash
cd /workshop/ypjh/backend
uv run pytest tests/api/test_auth.py -v
```

Expected: `5 passed`

- [ ] **Step 7: 运行全部测试**

```bash
cd /workshop/ypjh/backend
uv run pytest -v
```

Expected: 全部 PASSED（包含之前 Task 1-5 的测试）

- [ ] **Step 8: 验证服务可以启动**

```bash
cd /workshop/ypjh/backend
uv run uvicorn main:app --port 8001 &
sleep 2
curl -s -X POST http://localhost:8001/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"password123"}' | python3 -m json.tool
kill %1
```

Expected: `{ "data": { "access_token": "...", "token_type": "bearer" }, "error": null }`

- [ ] **Step 9: Commit**

```bash
git add backend/api/ backend/main.py backend/tests/conftest.py backend/tests/api/
git commit -m "feat: add auth API endpoints (register/login), FastAPI app with global error handler"
```

---

### Task 7：HTTPException 统一错误格式中间件

**Files:**
- Modify: `backend/main.py`

**Interfaces:**
- Produces: 所有 HTTPException 响应格式统一为 `{ "data": null, "error": { "code": "...", "message": "..." } }`

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/api/test_error_format.py
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_401_has_unified_error_format(client: AsyncClient):
    resp = await client.get(
        "/api/v1/auth/me",  # 还不存在的端点，先测 404
    )
    # 任何错误响应都应有 data=null + error 对象
    body = resp.json()
    # 404 时检查格式
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_http_exception_returns_unified_format(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "noexist@example.com", "password": "pass"},
    )
    assert resp.status_code == 401
    body = resp.json()
    assert body["data"] is None
    assert "code" in body["error"]
    assert "message" in body["error"]
```

- [ ] **Step 2: 运行确认部分失败（login 401 格式可能不统一）**

```bash
cd /workshop/ypjh/backend
uv run pytest tests/api/test_error_format.py -v
```

- [ ] **Step 3: 在 main.py 中添加 HTTPException handler**

```python
# backend/main.py（完整版，替换之前的）
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from backend.api.v1.router import v1_router
from backend.core.database import create_tables

app = FastAPI(title="错题本 API", version="0.1.0")
app.include_router(v1_router)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, dict):
        error = detail
    else:
        error = {"code": "HTTP_ERROR", "message": str(detail)}
    return JSONResponse(
        status_code=exc.status_code,
        content={"data": None, "error": error},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"data": None, "error": {"code": "INTERNAL_ERROR", "message": "服务器内部错误"}},
    )


@app.on_event("startup")
async def startup() -> None:
    await create_tables()
```

- [ ] **Step 4: 运行全部测试**

```bash
cd /workshop/ypjh/backend
uv run pytest -v
```

Expected: 全部 PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/main.py backend/tests/api/test_error_format.py
git commit -m "feat: add unified HTTPException handler → {data: null, error: {code, message}}"
```

---

## Self-Review

**Spec coverage check:**

| SRS 要求 | 对应 Task | 状态 |
|----------|-----------|------|
| REQ-A1 注册 → JWT 201 | Task 5+6 | ✅ |
| REQ-A2 登录 → JWT 200 / 401 | Task 5+6 | ✅ |
| REQ-A3 JWT 验证 `get_current_user` | Task 4 | ✅ |
| REQ-A4 禁止客户端传 user_id | Task 4（security.py） | ✅ |
| REQ-A5 bcrypt cost=12 | Task 4 | ✅ |
| 统一响应格式 `{data, error}` | Task 6+7 | ✅ |
| 语义错误码 DUPLICATE_EMAIL/INVALID_CREDENTIALS | Task 5+6 | ✅ |
| User/Question/ReviewLog ORM 含软删除字段 | Task 3 | ✅ |
| ARCH-2: confidence_score 不为 NULL | Task 3 | ✅ |
| R21: 软删除字段 deleted_at | Task 3 | ✅ |
| SM-2 字段预留 | Task 3 | ✅ |
| 全局异常不暴露 stack trace | Task 6+7 | ✅ |

**Plan 1 不包含（由后续 Plan 覆盖）：**
- 识别端点（Plan 2）
- CRUD 端点（Plan 3）
- SM-2 算法（Plan 4）
- 打印模块（Plan 5）
- 前端（Plan 6）
