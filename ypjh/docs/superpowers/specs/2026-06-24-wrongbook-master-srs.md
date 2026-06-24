# 错题本 Master SRS — 需求规格说明书（主文档）

**版本**：1.1  
**日期**：2026-06-24  
**作者**：Workshop Participant  
**状态**：已批准，可用于 design

> **给 AI 的阅读指引**：本文档是单一权威来源。读完本文档，你应该能回答：
> 整个 app 有哪些模块、每个模块的输入/输出/边界条件、数据长什么样、API 签名是什么、哪些事绝对不能做。
> 识别模块的完整规格在 `spec/recognize/requirements.md`，本文只做摘要 + 指针。

---

## 目录

1. [产品定位](#1-产品定位)
2. [系统上下文](#2-系统上下文)
3. [数据模型（权威）](#3-数据模型权威)
4. [API 合约概览](#4-api-合约概览)
5. [模块一：认证](#5-模块一认证)
6. [模块二：识别](#6-模块二识别摘要--指针)
7. [模块三：错题 CRUD](#7-模块三错题-crud)
8. [模块四：SM-2 复习](#8-模块四sm-2-复习)
9. [模块五：打印排版](#9-模块五打印排版)
10. [非功能性需求](#10-非功能性需求)
11. [全局约束（不得违反）](#11-全局约束不得违反)
12. [AI 实现指引](#12-ai-实现指引)
13. [前端行为规格（EARS）](#13-前端行为规格ears)

---

## 1. 产品定位

### 1.1 为什么存在

学生做错题本的真正障碍是**整理成本**，不是懒惰。拍照→手抄→分类→复习提醒，每步都要人工。错题本用 AI 识别消灭"拍照→录入"这一步，学生只需确认一次，后续复习自动推送。

### 1.2 目标用户

中学生、大学生、备考人员。**初期个人使用**，无多用户协作需求。

### 1.3 成功标准（MVP）

走通完整闭环：**上传图片 → AI 识别 → 用户确认 → 入库 → 列表查看 → 复习推送 → 打分 → 下次推送**。

### 1.4 功能范围

| 模块 | 优先级 | 本 SRS 覆盖 |
|------|--------|------------|
| 认证（注册/登录/JWT）| P0 | ✅ 第 5 节 |
| 拍照识别 | P0 | ✅ 第 6 节（详细规格在 `spec/recognize/requirements.md`）|
| 错题 CRUD | P0 | ✅ 第 7 节 |
| SM-2 复习推荐 | P1 | ✅ 第 8 节 |
| 打印排版 | P2 | ✅ 第 9 节 |

### 1.5 非目标（AI 不得自行添加）

- 缓存层（Redis 等）
- 多用户协作 / 分享功能
- 实时 WebSocket 推送（MVP 用同步 HTTP）
- 批量导入（非拍照方式）
- 社交功能（点赞/评论）
- 管理后台
- 真实 Bedrock 接入（MVP 用 `MOCK_BEDROCK=true`）

---

## 2. 系统上下文

### 2.1 参与者

| 参与者 | 类型 | 说明 |
|--------|------|------|
| 学生用户 | 主用户 | 注册、登录、拍照上传、确认、复习、打分 |
| AWS Bedrock | 外部系统 | 图片内容识别（非确定性 AI 输出） |
| AWS S3 | 外部系统 | 原始图片持久化存储 |
| 错题本后端 | 本系统 | FastAPI，处理所有业务逻辑 |
| 错题本前端 | 消费方 | Vue 3，展示结果，触发用户操作 |

### 2.2 系统边界

```
┌─────────────────────────────────────────────────────────┐
│                     错题本后端（本系统）                    │
│                                                          │
│  [认证模块] ←──JWT──→ [所有受保护端点]                      │
│                                                          │
│  [识别模块] ←──bytes──→ [S3] ←──key──→ [Bedrock]          │
│                                                          │
│  [CRUD 模块] ←──EARS 规格──→ [SQLite/DynamoDB]            │
│                                                          │
│  [复习模块] ←──SM-2 算法──→ [Question 记录]                │
│                                                          │
│  [打印模块] ←──Question 列表──→ [HTML 渲染引擎]             │
└─────────────────────────────────────────────────────────┘
         ↑                              ↑
    [Vue 3 前端]                   [AWS 外部服务]
```

### 2.3 技术栈（实现约束）

| 层 | 技术 | 版本约束 |
|---|---|---|
| 后端框架 | FastAPI | Python 3.12，async |
| ORM | SQLAlchemy 2 | async session |
| 数据校验 | Pydantic v2 | — |
| 认证 | JWT（python-jose） | HS256，24h 有效期 |
| 数据库（开发）| SQLite | — |
| 数据库（生产）| DynamoDB | 表名 `cuotiben-questions` |
| 前端框架 | Vue 3 | `<script setup lang="ts">` |
| 状态管理 | Pinia | — |
| HTTP 客户端 | Axios | interceptor 注入 Bearer token |
| Mock 切换 | `MOCK_BEDROCK` 环境变量 | 默认 `true` |

---

## 3. 数据模型（权威）

> 本节是唯一权威数据模型定义。其他文档如有冲突，以本节为准。

### 3.1 User

```python
class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(primary_key=True)        # UUID v4
    email: Mapped[str] = mapped_column(unique=True, index=True)
    hashed_password: Mapped[str]                              # bcrypt，cost ≥ 12
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(default=None)
```

### 3.2 Question

```python
class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(index=True)          # 来自 JWT sub，严格隔离（R1/R22）
    subject: Mapped[str | None]                               # 白名单：语文/数学/英语/物理/化学/生物/历史/地理/政治
    question_type: Mapped[str]                                # single/multiple/fill/essay
    content: Mapped[str]                                      # 结构化存储，禁止裸字符串（R3）
    wrong_answer: Mapped[str | None]                          # 学生手写答案（分离存储，R11）
    correct_answer: Mapped[str]
    analysis: Mapped[str | None]
    difficulty: Mapped[int] = mapped_column(default=3)        # 1-5
    confidence_score: Mapped[float] = mapped_column(default=0.0)  # 不得为 NULL（ARCH-2）
    image_key: Mapped[str | None]                             # S3 路径：{user_id}/original/{uuid}.{ext}
    original_filename: Mapped[str | None]                     # 原始文件名，不入 S3 路径（R18）
    status: Mapped[str] = mapped_column(default="confirmed")  # confirmed / pending_review / superseded
    # SM-2 字段
    ease_factor: Mapped[float] = mapped_column(default=2.5)
    review_count: Mapped[int] = mapped_column(default=0)
    interval_days: Mapped[int] = mapped_column(default=1)     # 当前复习间隔（天）
    next_review_at: Mapped[datetime | None]                   # NULL = 从未复习过
    last_reviewed_at: Mapped[datetime | None]
    # 审计字段
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(default=None)  # 软删除（R21）
```

### 3.3 ReviewLog（复习记录，只追加不修改）

```python
class ReviewLog(Base):
    __tablename__ = "review_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"))
    user_id: Mapped[str] = mapped_column(index=True)          # 冗余存储，避免 JOIN 时跨用户泄露
    score: Mapped[int]                                        # 1-5，SM-2 评分
    ease_factor_before: Mapped[float]                         # 记录变更前值，用于调试
    ease_factor_after: Mapped[float]
    interval_before: Mapped[int]
    interval_after: Mapped[int]
    reviewed_at: Mapped[datetime] = mapped_column(default=func.now())
```

### 3.4 PrintJob（打印任务，无需持久化，内存生成）

```python
class PrintJob(BaseModel):           # Pydantic，不入库
    question_ids: list[int]          # 用户选择的题目 ID 列表
    layout: str                      # "card"（卡片）/ "list"（列表）/ "compact"（紧凑）
    include_answer: bool = False     # 是否在打印版中显示答案
    include_analysis: bool = False
```

### 3.5 状态流转

```
Question.status 合法值与流转：

  [识别返回]
  high_confidence ──用户确认──→ confirmed
  pending_review  ──用户确认──→ confirmed
  pending_review  ──用户拒绝──→ (丢弃，不入库)
  error           ──────────→ (丢弃，不入库)

  [已入库后]
  confirmed ──重新识别，用户确认新结果──→ superseded（旧记录）
  confirmed ──软删除──→ deleted_at = now()（status 不变，查询过滤）
  confirmed ──用户编辑──→ confirmed（updated_at 更新）
```

---

## 4. API 合约概览

> 所有端点以 `/api/v1/` 开头，所有受保护端点需要 `Authorization: Bearer <token>` header。

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| POST | `/api/v1/auth/register` | 否 | 注册 |
| POST | `/api/v1/auth/login` | 否 | 登录，返回 JWT |
| POST | `/api/v1/questions/recognize` | 是 | 上传图片 → 识别候选（不入库）|
| POST | `/api/v1/questions` | 是 | 确认识别结果入库 / 手动创建 |
| GET | `/api/v1/questions` | 是 | 错题列表（分页 + 过滤）|
| GET | `/api/v1/questions/{id}` | 是 | 错题详情 |
| PATCH | `/api/v1/questions/{id}` | 是 | 更新错题字段 |
| DELETE | `/api/v1/questions/{id}` | 是 | 软删除 |
| GET | `/api/v1/review/queue` | 是 | 获取今日待复习题目 |
| POST | `/api/v1/review/{id}/score` | 是 | 提交复习评分（1-5）|
| GET | `/api/v1/review/stats` | 是 | 复习统计（今日/累计）|
| POST | `/api/v1/print/preview` | 是 | 生成打印预览 HTML |

### 4.1 统一响应格式

**成功**：
```json
{ "data": { ... }, "error": null }
```

**失败**：
```json
{ "data": null, "error": { "code": "SEMANTIC_CODE", "message": "用户可读描述" } }
```

**语义错误码（全量）**：

| code | HTTP | 触发场景 |
|------|------|---------|
| `INVALID_CREDENTIALS` | 401 | 登录密码错误 |
| `TOKEN_EXPIRED` | 401 | JWT 过期 |
| `TOKEN_INVALID` | 401 | JWT 格式/签名错误 |
| `DUPLICATE_EMAIL` | 409 | 注册时邮箱已存在 |
| `FORBIDDEN` | 403 | 访问他人资源（R1）|
| `NOT_FOUND` | 404 | 资源不存在或已软删除 |
| `INVALID_FILE_TYPE` | 415 | Magic Bytes 校验失败（R16）|
| `FILE_TOO_LARGE` | 413 | 超过 20MB（R17）|
| `OCR_FAILED` | 200 | Bedrock 识别失败（业务错误，不用 5xx）|
| `OCR_FORMAT_ERROR` | 200 | Bedrock 返回非法 JSON（REQ-29）|
| `OCR_RATE_LIMITED` | 200 | Bedrock 429/503 重试后仍失败（REQ-30）|
| `INVALID_SCORE` | 422 | 复习评分不在 [1,5] 范围 |
| `VALIDATION_ERROR` | 422 | Pydantic 校验失败 |

---

## 5. 模块一：认证

### 5.1 EARS 规格

**REQ-A1**（用户注册）  
When 用户提交合法邮箱和密码（密码 ≥ 8 位），  
the system shall 创建 User 记录（`id=uuid4()`，`hashed_password=bcrypt(password, rounds=12)`），  
并返回 JWT token（有效期 24h，payload 含 `sub=user.id`）。

**验收标准**：
- [ ] 注册成功 → HTTP 201，响应含 `access_token`
- [ ] 密码在 DB 中为 bcrypt 哈希，不存明文
- [ ] 不同用户注册相同邮箱 → HTTP 409，`code="DUPLICATE_EMAIL"`
- [ ] 密码 < 8 位 → HTTP 422，`code="VALIDATION_ERROR"`

---

**REQ-A2**（用户登录）  
When 用户提交已注册邮箱和正确密码，  
the system shall 验证 bcrypt 哈希，返回新 JWT token（有效期 24h）。

**验收标准**：
- [ ] 登录成功 → HTTP 200，响应含 `access_token`、`token_type="bearer"`
- [ ] 密码错误 → HTTP 401，`code="INVALID_CREDENTIALS"`（不区分"邮箱不存在"和"密码错误"，防枚举）
- [ ] 邮箱不存在 → 同上，HTTP 401，`code="INVALID_CREDENTIALS"`

---

**REQ-A3**（JWT 验证）  
While 用户访问任何受保护端点，  
the system shall 从 `Authorization: Bearer <token>` 提取并验证 JWT，  
从 `sub` 字段提取 `user_id`，注入到所有下游调用。

**验收标准**：
- [ ] 缺少 token → HTTP 401，`code="TOKEN_INVALID"`
- [ ] token 已过期 → HTTP 401，`code="TOKEN_EXPIRED"`
- [ ] token 签名错误 → HTTP 401，`code="TOKEN_INVALID"`
- [ ] 有效 token → `current_user.id` 等于 JWT `sub` 字段值

---

**REQ-A4**（禁止客户端传入 user_id）  
While 后端处理任何业务请求，  
the system shall 不接受 query string、request body 或自定义 header 中的 `user_id` 参数，  
所有 `user_id` 值必须从已验证 JWT 的 `sub` 字段提取。

**验收标准**：
- [ ] 请求 body 含 `user_id` 字段 → 忽略该字段，以 JWT sub 为准
- [ ] 路由函数签名中无 `user_id: str = Query(...)` 或 `user_id: str = Body(...)`

---

**REQ-A5**（密码安全存储）  
When 系统存储用户密码，  
the system shall 使用 bcrypt（cost factor = 12）哈希，  
不得以任何形式存储明文密码或可逆加密密码。

**验收标准**：
- [ ] `User.hashed_password` 以 `$2b$12$` 开头
- [ ] 登录验证使用 `bcrypt.checkpw()`，不做字符串比较

---

### 5.2 认证接口签名

```python
# POST /api/v1/auth/register
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 86400  # 秒

# POST /api/v1/auth/login
class LoginRequest(BaseModel):
    email: EmailStr
    password: str
```

---

## 6. 模块二：识别（摘要 + 指针）

> **完整规格**：`spec/recognize/requirements.md`（REQ-1 ~ REQ-30，版本 1.3）
> 本节只做摘要，实现时必须以原文为准。

### 6.1 识别主线（一句话）

`POST /api/v1/questions/recognize` → Magic Bytes 校验 → S3 上传（EXIF 修正）→ Bedrock 识别（最多重试 2 次）→ Schema 校验 → 状态决策 → 返回 `RecognitionResultOut`（不入库）。

### 6.2 识别接口签名

```python
# 请求：multipart/form-data
# image: UploadFile（JPEG/PNG/HEIC，≤ 20MB）

class QuestionCandidateOut(BaseModel):
    content: str
    correct_answer: str
    wrong_answer: str | None
    confidence: float                # [0.0, 1.0]
    subject: str | None              # 学科白名单内或 None
    question_type: str | None
    image_key: str                   # S3 路径

class RecognitionResultOut(BaseModel):
    status: Literal["high_confidence", "pending_review", "error"]
    candidate: QuestionCandidateOut | None
    error_hint: str | None
    error_code: str | None           # 语义错误码
```

### 6.3 关键边界（必须实现，详见原文）

| REQ | 边界 | 致命性 |
|-----|------|--------|
| REQ-6 | confidence 缺失 → 0.0，不得默认 1.0 | ★★★★★ |
| REQ-27 | EXIF 旋转修正，送 Bedrock 前执行 | ★★★★★ |
| REQ-29 | Bedrock 返回非法 JSON → error，不得 500 | ★★★★★ |
| REQ-14 | 手写答案 → wrong_answer，不混入 content | ★★★★★ |
| REQ-21 | Magic Bytes 校验，不信 Content-Type | ★★★★★ |
| REQ-30 | 429/503 指数退避重试最多 2 次 | ★★★★☆ |
| REQ-28 | 非题目图片 → error，不进入确认流程 | ★★★★☆ |

---

## 7. 模块三：错题 CRUD

### 7.1 EARS 规格

**REQ-C1**（错题列表）  
When 已认证用户请求错题列表，  
the system shall 返回该用户的错题列表（分页，默认每页 20 条），自动过滤 `deleted_at IS NULL`，  
支持 `subject`、`difficulty`、`status` 过滤参数。

**验收标准**：
- [ ] 响应包含 `items: list[QuestionListItemOut]`、`total`、`page`、`page_size`
- [ ] 不返回其他用户的题目（R1）
- [ ] 不返回已软删除的题目
- [ ] `subject=数学` 过滤 → 只返回数学题
- [ ] 空列表时返回 `{ "data": { "items": [], "total": 0 } }`，不返回 404

---

**REQ-C2**（错题详情）  
When 已认证用户请求某条错题详情，  
the system shall 返回完整 Question 对象，图片字段替换为预签名 URL（有效期 ≤ 1h）。

**验收标准**：
- [ ] 响应含 `image_url`（预签名 URL）和 `image_url_expires_at`（ISO 8601），不含原始 S3 路径（R23）
- [ ] 访问他人题目 → HTTP 403，`code="FORBIDDEN"`（R1）
- [ ] 访问已软删除题目 → HTTP 404，`code="NOT_FOUND"`
- [ ] `image_key` 为 None 时，`image_url` 字段为 None

---

**REQ-C3**（创建错题 — 确认识别结果）  
When 已认证用户提交识别候选结果确认，  
the system shall 创建 Question 记录（`status="confirmed"`），  
初始化 SM-2 参数（`ease_factor=2.5`，`interval_days=1`，`next_review_at=now()+1d`），  
返回 HTTP 201 和新记录 ID。

**验收标准**：
- [ ] 入库记录 `user_id` 等于 JWT sub（R1）
- [ ] 入库记录 `confidence_score` 不为 NULL（ARCH-2）
- [ ] `content` 不为裸 JSON 字符串（R3）
- [ ] 入库后 `next_review_at` 在 23h~25h 后
- [ ] 二次识别同一 `image_key`：旧记录 `status` 改为 `superseded`（REQ-19）

---

**REQ-C4**（手动创建错题）  
When 已认证用户手动填写题目内容（不经过识别）并提交，  
the system shall 创建 Question 记录（`confidence_score=0.0`，`image_key=None`），  
`status="confirmed"`。

**验收标准**：
- [ ] `content` 和 `correct_answer` 必填，缺失 → HTTP 422
- [ ] `subject` 必须在白名单内或为 None，否则 → HTTP 422
- [ ] 创建成功 → HTTP 201

---

**REQ-C5**（更新错题）  
When 已认证用户更新自己的错题字段，  
the system shall 校验并持久化变更，更新 `updated_at`，  
不得修改 `user_id`、`confidence_score`、`image_key`（这三个字段只读）。

**验收标准**：
- [ ] 更新他人题目 → HTTP 403
- [ ] `subject` 更新为白名单外值 → HTTP 422
- [ ] 可更新字段：`content`、`correct_answer`、`wrong_answer`、`analysis`、`difficulty`、`subject`、`question_type`
- [ ] 不可更新字段更新请求 → 静默忽略（不报错，不生效）

---

**REQ-C6**（软删除错题）  
When 已认证用户删除自己的错题，  
the system shall 设置 `deleted_at = now()`，不执行物理删除，  
返回 HTTP 204。

**验收标准**：
- [ ] 删除后 DB 记录仍存在，`deleted_at` 非 None
- [ ] 删除后列表和详情均不可见（R21）
- [ ] 删除他人题目 → HTTP 403
- [ ] 重复删除已删除题目 → HTTP 404

---

**REQ-C7**（空占位符保护）  
If `content` 为占位符（`"（识别内容为空）"`）且 `image_key` 为 None，  
the system shall 拒绝入库，返回 HTTP 422，`code="VALIDATION_ERROR"`。

**验收标准**：
- [ ] content=占位符 且 image_key=None → 422，不创建记录
- [ ] content=占位符 但 image_key 有值 → 允许入库（图片本身是有效信息）

---

### 7.2 CRUD 接口签名

```python
class QuestionCreate(BaseModel):
    content: str = Field(min_length=1)
    correct_answer: str = Field(min_length=1)
    wrong_answer: str | None = None
    analysis: str | None = None
    subject: str | None = None
    question_type: str = "single"
    difficulty: int = Field(default=3, ge=1, le=5)
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    image_key: str | None = None
    original_filename: str | None = None

class QuestionUpdate(BaseModel):  # 所有字段可选，PATCH 语义
    content: str | None = None
    correct_answer: str | None = None
    wrong_answer: str | None = None
    analysis: str | None = None
    subject: str | None = None
    question_type: str | None = None
    difficulty: int | None = Field(default=None, ge=1, le=5)

class QuestionOut(BaseModel):
    id: int
    user_id: str
    subject: str | None
    question_type: str
    content: str
    wrong_answer: str | None
    correct_answer: str
    analysis: str | None
    difficulty: int
    confidence_score: float
    image_url: str | None            # 预签名 URL，非 S3 路径
    image_url_expires_at: str | None # ISO 8601
    status: str
    ease_factor: float
    review_count: int
    interval_days: int
    next_review_at: datetime | None
    created_at: datetime
    updated_at: datetime

class QuestionListItemOut(BaseModel):  # 列表视图，字段精简
    id: int
    subject: str | None
    question_type: str
    content: str                     # 截断 100 字
    difficulty: int
    status: str
    next_review_at: datetime | None
    created_at: datetime

class QuestionListOut(BaseModel):
    items: list[QuestionListItemOut]
    total: int
    page: int
    page_size: int
```

---

## 8. 模块四：SM-2 复习

### 8.1 算法规格（标准 SM-2）

**评分含义**（1-5 分，用户看到的标签）：

| 分值 | 标签 | 内部含义 |
|------|------|---------|
| 1 | 完全不会 | 完全遗忘，从未见过 |
| 2 | 模糊记得 | 看到答案后才想起 |
| 3 | 困难但想起来了 | 正确但很吃力 |
| 4 | 犹豫后答对 | 正确，有轻微迟疑 |
| 5 | 完全掌握 | 流畅正确，无迟疑 |

**SM-2 计算公式**（每次复习后执行）：

```python
def calculate_next_review(score: int, ease_factor: float, 
                           interval_days: int, review_count: int
                           ) -> tuple[float, int, int]:
    """
    返回：(new_ease_factor, new_interval_days, new_review_count)
    """
    if score < 3:  # 失败：重置间隔
        new_review_count = 0
        new_interval = 1
        new_ef = ease_factor  # 失败不降低 EF，只重置间隔
    else:  # 成功：按 SM-2 公式递进
        new_review_count = review_count + 1
        if new_review_count == 1:
            new_interval = 1
        elif new_review_count == 2:
            new_interval = 6
        else:
            new_interval = round(interval_days * ease_factor)
        
        # EF 调整公式
        new_ef = ease_factor + (0.1 - (5 - score) * (0.08 + (5 - score) * 0.02))
        new_ef = max(1.3, new_ef)  # EF 下限 1.3，防无限递减
    
    return new_ef, new_interval, new_review_count
```

### 8.2 EARS 规格

**REQ-S1**（复习队列）  
When 已认证用户请求复习队列，  
the system shall 返回 `next_review_at <= now()` 且 `status="confirmed"` 且 `deleted_at IS NULL` 的题目列表，  
按 `next_review_at` 升序排列（最"过期"的最优先）。

**验收标准**：
- [ ] 只返回当前用户的题目（R1）
- [ ] `next_review_at > now()` 的题目不出现在队列中
- [ ] `next_review_at = None`（从未复习过）的题目出现在队列中（新题优先）
- [ ] 已软删除题目不出现在队列
- [ ] 队列为空时返回 `{ "items": [], "message": "暂无待复习题目，今日任务已完成！" }`

---

**REQ-S2**（提交复习评分）  
When 已认证用户对某题提交复习评分（1-5 分），  
the system shall 执行 SM-2 算法更新 `ease_factor`、`interval_days`、`review_count`，  
设置 `next_review_at = now() + new_interval_days`，  
创建 ReviewLog 记录，返回更新后的复习参数。

**验收标准**：
- [ ] 评分 1-2（失败）→ `interval_days = 1`，`review_count = 0`，`next_review_at ≈ 明天`
- [ ] 评分 3-5（成功）→ `interval_days` 按 SM-2 递增，`review_count += 1`
- [ ] `ease_factor` 不低于 1.3
- [ ] ReviewLog 记录包含变更前后的 EF 和 interval（用于调试）
- [ ] 评分 0 或 6 → HTTP 422，`code="INVALID_SCORE"`
- [ ] 提交他人题目评分 → HTTP 403（R1）

---

**REQ-S3**（SM-2 初始化）  
When 一条 Question 首次入库（confirmed），  
the system shall 初始化：`ease_factor=2.5`，`interval_days=1`，`review_count=0`，  
`next_review_at = now() + 1 day`。

**验收标准**：
- [ ] 新入库题目自动出现在明天的复习队列中
- [ ] 所有 SM-2 字段有有效初始值，无 NULL

---

**REQ-S4**（复习统计）  
When 已认证用户请求复习统计，  
the system shall 返回：今日已完成复习数、今日待复习总数、累计复习次数、当前连续复习天数。

**验收标准**：
- [ ] 统计只包含当前用户数据（R1）
- [ ] 连续复习天数：如果昨天有复习记录则 +1，否则归零

---

### 8.3 复习接口签名

```python
# GET /api/v1/review/queue
class ReviewQueueOut(BaseModel):
    items: list[QuestionListItemOut]
    total: int
    message: str | None              # 队列为空时的提示

# POST /api/v1/review/{id}/score
class ReviewScoreRequest(BaseModel):
    score: int = Field(ge=1, le=5)

class ReviewScoreResponse(BaseModel):
    question_id: int
    score: int
    ease_factor_after: float
    interval_days_after: int
    next_review_at: datetime
    review_count: int

# GET /api/v1/review/stats
class ReviewStatsOut(BaseModel):
    today_completed: int
    today_total: int
    total_reviews: int
    streak_days: int
```

---

## 9. 模块五：打印排版

### 9.1 EARS 规格

**REQ-P1**（打印预览生成）  
When 已认证用户选择若干题目并提交打印请求，  
the system shall 生成一份可打印的 HTML 文档，包含选中题目的完整内容，  
在 5 秒内返回。

**验收标准**：
- [ ] 响应为 `Content-Type: text/html`
- [ ] HTML 包含所有选中题目，按题目 ID 顺序排列
- [ ] 响应时间 P95 ≤ 5s（题目数 ≤ 50）
- [ ] 只能打印当前用户自己的题目（R1）：请求中含他人题目 ID → 过滤掉，不报错

---

**REQ-P2**（数学公式打印渲染）  
When 打印题目中包含 LaTeX 公式，  
the system shall 在 HTML 中嵌入 KaTeX 离线渲染资源，  
确保打印时公式正确显示，不依赖网络加载。

**验收标准**：
- [ ] HTML 中包含 KaTeX CSS/JS（内联或 CDN 链接均可，但打印环境需无网络可用）
- [ ] `$\frac{1}{2}$` 等 LaTeX 标记在 HTML 预览中正确渲染为数学符号

---

**REQ-P3**（图形题目打印）  
When 打印的题目含 `image_key`（几何图/电路图），  
the system shall 在 HTML 中嵌入图片预签名 URL，  
并标注"（图片有效期 1 小时，请尽快打印）"提示。

**验收标准**：
- [ ] HTML 中含 `<img src="<presigned_url>">` 标签
- [ ] 图片旁有有效期提示文字
- [ ] `image_key = None` 的题目不生成 `<img>` 标签

---

**REQ-P4**（打印布局选项）  
When 用户选择打印布局，  
the system shall 支持三种布局：
- `card`：每题一张卡片，含边框，适合剪切
- `list`：题目列表，紧凑排列，适合 A4 打印
- `compact`：双栏布局，节省纸张

**验收标准**：
- [ ] 三种布局均输出合法 HTML
- [ ] `card` 布局每题有明确分隔（`page-break-inside: avoid`）

---

**REQ-P5**（答案显示控制）  
When 用户选择是否在打印版中显示答案，  
the system shall 根据 `include_answer` 参数决定是否在题目下方展示 `correct_answer` 和 `analysis`。

**验收标准**：
- [ ] `include_answer=false`（默认）→ 打印 HTML 中不含答案和解析
- [ ] `include_answer=true` → 打印 HTML 中含答案，用分隔线与题目区分

---

### 9.2 打印接口签名

```python
# POST /api/v1/print/preview
class PrintRequest(BaseModel):
    question_ids: list[int] = Field(min_length=1, max_length=50)
    layout: Literal["card", "list", "compact"] = "card"
    include_answer: bool = False
    include_analysis: bool = False

# 响应：Content-Type: text/html，直接返回 HTML 字符串
# 不是 JSON 响应
```

---

## 10. 非功能性需求

### 10.1 性能

| 指标 | 目标值 | 说明 |
|------|--------|------|
| 认证接口 P95 | ≤ 300ms | 含 bcrypt 验证 |
| CRUD 接口 P95 | ≤ 500ms | 查询/创建/删除 |
| 识别接口 P95 | ≤ 10s | 含 S3 + Bedrock（无重试）|
| 识别接口 P95（含重试）| ≤ 15s | 最多 2 次重试 +3s |
| 复习队列 P95 | ≤ 500ms | 含 SM-2 计算 |
| 打印预览 P95 | ≤ 5s | ≤ 50 题 |
| 并发上传 MVP | ≥ 10 并发 | 超出排队，不崩溃 |
| 单文件上限 | 20MB | 超出 413 |

### 10.2 安全

| 要求 | 规则 | 验收 |
|------|------|------|
| 用户隔离 | R1 | 所有查询含 `user_id` 过滤，BOLA 测试（两用户互访）|
| JWT 来源 | R22 | `user_id` 只从 JWT sub 提取，不接受客户端传入 |
| 密码存储 | REQ-A5 | bcrypt cost=12，不存明文 |
| 文件类型 | R16 | Magic Bytes 校验 |
| 文件大小 | R17 | Content-Length 前置检查 |
| S3 访问 | R23 | 预签名 URL，bucket 禁公开访问 |
| 原图保护 | R19 | original/ 路径只写一次 |
| 软删除 | R21 | 无物理删除 |
| 生产错误响应 | — | 不暴露 stack trace，只返回语义错误码 |

### 10.3 可测试性

- `MOCK_BEDROCK=true`（默认）：识别测试不调真实 Bedrock
- `VITE_USE_MOCK=true`（默认）：前端不依赖后端启动
- 所有识别测试：只断言结构/契约，不断言具体文字（REQ-20）
- 每个模块有独立单元测试，不需要 E2E 即可验证业务逻辑

---

## 11. 全局约束（不得违反）

> 以下约束来自 `rules/personal.md` R1-R24，这里是执行摘要。完整规则和触发条件见 `rules/ears-triggers.md`。

| ID | 级别 | 约束 |
|----|------|------|
| R1 | MUST | 所有 DB 查询含 `user_id` 过滤，禁止 BOLA |
| R2 | MUST | Bedrock confidence 缺失 → 0.0，不得默认 1.0 |
| R3 | MUST | 题目结构化存储，禁止裸字符串入库 |
| R4 | MUST | confidence < 0.7 → `pending_review`，不直接入库 |
| R10 | MUST | 无错误标记图片 → `pending_review` |
| R11 | MUST | 手写答案存 `wrong_answer`，不混入 `content` |
| R12 | MUST | 含图形题目强制保留 `image_key` |
| R16 | MUST | Magic Bytes 校验，拒绝非图片文件 |
| R17 | MUST | 20MB 上限，在读取内容前检查 |
| R18 | MUST | UUID 重命名，原始文件名存 `original_filename` |
| R19 | MUST | S3 `original/` 路径只写一次，不可覆盖删除 |
| R20 | MUST | S3 key 格式：`{user_id}/original/{uuid}.{ext}` |
| R21 | MUST | 软删除，禁止物理删除 Question 记录 |
| R22 | MUST | `user_id` 从 JWT sub 提取，拒绝客户端传入 |
| R23 | MUST | 图片以预签名 URL 下发，有效期 ≤ 1h |
| R24 | MUST | Bedrock prompt 放 `backend/prompts/`，不硬编码 |

---

## 12. AI 实现指引

> 给实现本 SRS 的 AI Agent 的直接指令。

### 实现顺序（依赖关系决定）

```
Task 1: 认证模块（User 模型 + JWT）         # 其他所有模块依赖它
Task 2: Question 模型 + 数据库迁移          # CRUD 和识别都依赖它
Task 3: 识别模块后端                        # 依赖 Task 1+2
Task 4: CRUD 模块                           # 依赖 Task 1+2
Task 5: SM-2 复习模块                       # 依赖 Task 4
Task 6: 打印模块                            # 依赖 Task 4
Task 7: 前端（与 Task 3-6 并行，使用 mock）
Task 8: 前后端联调
```

### 每个 Task 开始前必读

1. `rules/ears-triggers.md` — 扫描本次修改涉及哪些触发条件
2. `PRODUCT.md` — 确认功能在范围内，不加非目标功能
3. `IMPROVEMENT.md` — 检查历史踩坑，不重复犯同样的错误

### 代码架构要求

```
backend/
├── prompts/                    # R24：Bedrock prompt 文件
│   └── recognize_question.txt
├── core/
│   ├── config.py               # Settings，env vars
│   ├── database.py             # async engine + get_session
│   └── security.py            # JWT encode/decode + get_current_user
├── models/
│   ├── base.py
│   ├── user.py
│   ├── question.py
│   └── review_log.py
├── schemas/
│   ├── auth.py
│   ├── question.py
│   ├── recognition.py
│   ├── review.py
│   └── print_.py
├── repositories/               # 所有 DB 操作，所有查询含 user_id（R1/ARCH-3）
│   ├── user_repository.py
│   ├── question_repository.py
│   └── review_repository.py
├── services/
│   ├── auth_service.py
│   ├── question_service.py
│   ├── recognition_service.py  # 已有，已符合规格
│   ├── review_service.py       # SM-2 算法
│   └── print_service.py
└── api/v1/endpoints/
    ├── auth.py
    ├── questions.py
    ├── review.py
    └── print_.py
```

### 测试要求

每个模块至少包含：
- **认证**：注册成功/重复邮箱/登录成功/密码错误/JWT 过期
- **识别**：已在 `backend/tests/test_recognition_service.py`（10 个，不重复写）
- **CRUD**：列表分页/学科过滤/跨用户403/软删除/详情含预签名URL
- **SM-2**：评分1-5的interval计算/EF下限1.3/连续失败重置/初始化参数
- **打印**：三种布局/含LaTeX题/含图片题/答案控制

**禁止**：任何测试中断言 Bedrock 识别的具体文字内容（REQ-20）。

---

## 13. 前端行为规格（EARS）

> 本节覆盖 Vue 3 前端的核心行为约束。技术栈：Vue 3 `<script setup lang="ts">` + Pinia + Vue Router v4 + Axios。
> 状态管理约定：组件通过 Composable（`useXxx.ts`）或 Pinia Store 获取数据，`<template>` 中不直接调用 API（R7）。

### 13.1 全局约束（前端）

| 约束 | 规则 | 说明 |
|------|------|------|
| Token 存储 | — | JWT 存 `localStorage`，key=`wrongbook_token` |
| 自动注入 | — | Axios interceptor 在每个请求头注入 `Authorization: Bearer <token>` |
| 401 处理 | — | Axios response interceptor 拦截 401 → 清除 token → 跳转 `/login` |
| Mock 切换 | — | `VITE_USE_MOCK=true` 时所有 API 调用返回 mock 数据，不发真实请求 |
| 禁止 `any` | — | TypeScript strict，禁止 `any`，用 `unknown` + 类型守卫 |
| 禁止直接调 API | R7 | 组件内不得出现 `questionsApi.xxx()` 直接调用 |
| 数学公式渲染 | R13 | 含 LaTeX 的字段用 KaTeX 渲染，不显示原始 `$...$` 字符串 |
| 图片展示 | R23 | 只使用后端下发的 `image_url`（预签名），不拼 S3 路径 |

### 13.2 页面结构

| 路由 | 页面组件 | 认证保护 |
|------|---------|---------|
| `/login` | `LoginPage.vue` | 否（已登录跳 `/`）|
| `/register` | `RegisterPage.vue` | 否 |
| `/` | `HomePage.vue`（错题列表）| 是 |
| `/upload` | `UploadPage.vue`（拍照识别）| 是 |
| `/questions/:id` | `QuestionDetailPage.vue` | 是 |
| `/review` | `ReviewPage.vue` | 是 |
| `/print` | `PrintPage.vue` | 是 |

---

### 13.3 EARS 规格

#### 认证页面

**REQ-F1**（未登录访问保护页面）
If 用户访问需要认证的路由时 `localStorage.getItem("wrongbook_token")` 为空，
the system shall 重定向到 `/login`，并在登录成功后跳回原目标路由。

**验收标准**：
- [ ] 直接访问 `/` → 重定向到 `/login?redirect=/`
- [ ] 登录成功后跳转到 `redirect` 参数指定的路由
- [ ] 已登录用户访问 `/login` → 重定向到 `/`

---

**REQ-F2**（登录表单提交）
When 用户填写邮箱和密码并提交登录，
the system shall 调用 `POST /api/v1/auth/login`，成功后存储 token 并跳转到目标页面，
失败时在表单下方展示错误提示，不清空密码输入框。

**验收标准**：
- [ ] 登录成功 → `localStorage.wrongbook_token` 有值，跳转到 `/`
- [ ] 401 响应 → 表单下方显示"邮箱或密码错误"，密码框不清空
- [ ] 网络错误 → Toast 提示"网络异常，请重试"
- [ ] 提交时按钮 loading 状态，防重复提交

---

**REQ-F3**（注册表单验证）
When 用户填写注册信息，
the system shall 在本地校验密码 ≥ 8 位、两次密码一致，
不得在本地校验通过前发送请求。

**验收标准**：
- [ ] 密码 < 8 位 → 本地提示"密码至少 8 位"，不发请求
- [ ] 两次密码不一致 → 本地提示"两次密码不一致"，不发请求
- [ ] 409 响应 → 表单提示"该邮箱已注册"
- [ ] 注册成功 → 自动登录（存 token）并跳转 `/`

---

#### 上传识别页面

**REQ-F4**（图片上传 UX 约束）
When 用户选择或拖拽图片文件，
the system shall 在上传前本地校验文件类型（JPEG/PNG/HEIC）和大小（≤ 20MB），
不符合时展示错误提示，不发起上传请求。

**验收标准**：
- [ ] 选择 `.txt` 文件 → 提示"请上传 JPEG、PNG 或 HEIC 格式的图片"
- [ ] 选择 > 20MB 文件 → 提示"图片大小不能超过 20MB"
- [ ] 合法文件 → 展示预览缩略图，激活上传按钮

---

**REQ-F5**（识别状态机）
While 用户在上传识别页面操作，
the system shall 维护以下状态机，每个状态有对应的 UI 表现：

```
idle         → 显示上传区域（DropZone）
uploading    → 显示进度条 + "正在上传..."，禁用上传按钮
recognizing  → 显示 spinner + "AI 识别中..."
confirming   → 显示 RecognitionPreview 确认卡
saving       → 显示 "保存中..."，禁用确认按钮
done         → Toast "保存成功" + 跳转到题目详情页
error        → 显示 error_hint + 重试按钮，回到 idle
```

**验收标准**：
- [ ] 每个状态下非当前操作的 UI 元素被禁用或隐藏
- [ ] `status=error` → 显示 `error_hint`，显示"重试"按钮，点击回到 `idle`
- [ ] 页面刷新时状态重置为 `idle`（不持久化上传状态）

---

**REQ-F6**（高置信度 vs 低置信度确认卡差异展示）
If 识别结果 `status == "high_confidence"`，
the system shall 在确认卡顶部展示绿色标签"识别置信度高"，字段预填，用户可直接确认。

If 识别结果 `status == "pending_review"`，
the system shall 在确认卡顶部展示黄色警告"识别不确定，请仔细核对"，
所有字段可编辑，确认按钮文字改为"确认后保存"（非"直接保存"）。

**验收标准**：
- [ ] `high_confidence` → 绿色标签 `.badge-green`，置信度百分比显示
- [ ] `pending_review` → 黄色警告 `.badge-yellow`，`error_hint` 显示在卡片内
- [ ] 两种状态下所有字段均可编辑（用户可修正识别错误）
- [ ] 学科字段为 `None` 时显示"请选择学科"下拉框，必选后才能确认

---

**REQ-F7**（确认卡中的图片展示）
If 识别结果含 `image_key`（非 None），
the system shall 在确认卡右侧展示题目原图（使用 `image_url` 预签名 URL），
图片加载失败时显示占位符"图片加载失败"。

**验收标准**：
- [ ] `image_url` 非空 → `<img>` 标签展示原图
- [ ] `image_url` 为空 → 不渲染 `<img>` 标签
- [ ] 图片加载失败（onerror）→ 显示"图片加载失败"占位文字

---

#### 错题列表页面

**REQ-F8**（错题列表展示）
When 用户进入首页，
the system shall 加载并展示当前用户的错题列表（默认第 1 页，20 条/页），
按创建时间降序排列。

**验收标准**：
- [ ] 列表含题目摘要（内容前 50 字）、学科标签、难度星级、创建时间
- [ ] 空列表时显示"暂无错题，去拍照上传第一道题吧"引导文案
- [ ] 下拉到底部自动加载下一页（无限滚动）或显示分页控件
- [ ] 学科/难度过滤切换时重新请求（不在前端过滤缓存数据）

---

**REQ-F9**（错题详情页）
When 用户点击某道错题，
the system shall 展示题目全部字段，数学公式用 KaTeX 渲染，
含图片时展示原图（使用 `image_url`）。

**验收标准**：
- [ ] `content`/`correct_answer` 中的 `$...$` 内容通过 KaTeX 渲染为数学符号
- [ ] `image_url` 非空 → 展示原图，支持点击放大
- [ ] `image_url_expires_at` 过期（距当前时间 < 60s）→ 自动调用接口刷新 URL
- [ ] 编辑按钮 → 跳转到编辑模式（字段变为可编辑输入框，PATCH 保存）
- [ ] 删除按钮 → 弹确认对话框，确认后软删除，跳回列表页

---

#### 复习页面

**REQ-F10**（复习队列展示）
When 用户进入复习页面，
the system shall 加载今日待复习题目队列，展示第一道题，
隐藏答案和解析，仅展示题目正文和图片。

**验收标准**：
- [ ] 进入页面默认隐藏 `correct_answer` 和 `analysis`
- [ ] 队列为空 → 展示"今日任务已完成 🎉"，显示今日完成数
- [ ] 显示当前题目序号（如"第 3/12 题"）

---

**REQ-F11**（翻转答案 + 提交评分）
When 用户点击"查看答案"，
the system shall 显示 `correct_answer` 和 `analysis`，并展示 5 个评分按钮（标准 SM-2 标签）。

When 用户点击评分按钮（1-5 分），
the system shall 提交 `POST /api/v1/review/{id}/score`，成功后自动加载下一道题。

**评分按钮标签**：
| 分值 | 显示文字 | 颜色 |
|------|---------|------|
| 1 | 完全不会 | 红色 |
| 2 | 模糊记得 | 橙色 |
| 3 | 困难想起 | 黄色 |
| 4 | 犹豫答对 | 浅绿 |
| 5 | 完全掌握 | 绿色 |

**验收标准**：
- [ ] 答案默认隐藏，点击"查看答案"后才显示
- [ ] 评分提交中按钮 loading，防重复点击
- [ ] 提交成功 → 显示下一题（如果有）或"今日完成"页
- [ ] 提交失败 → Toast 提示"提交失败，请重试"，按钮恢复可点击

---

**REQ-F12**（复习统计展示）
When 用户查看复习统计，
the system shall 展示：今日已完成 / 今日待复习总数 / 连续复习天数。

**验收标准**：
- [ ] 统计数据与 `GET /api/v1/review/stats` 响应一致
- [ ] 连续天数展示"🔥 连续 N 天"，N=0 时不显示火焰图标

---

#### 打印页面

**REQ-F13**（题目选择 + 打印配置）
When 用户进入打印页面，
the system shall 展示错题列表（多选），用户选择题目后配置打印选项（布局/是否含答案），
预览按钮触发 `POST /api/v1/print/preview`。

**验收标准**：
- [ ] 最多选择 50 道题，超出时禁用更多选择并提示"最多选择 50 道"
- [ ] 未选择任何题目时"预览"按钮禁用
- [ ] 预览成功 → 在新标签页打开 HTML 内容（`window.open`）
- [ ] 含图片的题目预览中显示"图片有效期 1 小时，请尽快打印"提示

---

### 13.4 Mock 策略（`VITE_USE_MOCK=true`）

| API 模块 | Mock 文件位置 | 说明 |
|---------|-------------|------|
| 认证 | `src/api/__mocks__/auth.ts` | 固定返回成功 token |
| 识别 | `src/api/__mocks__/recognition.ts` | 返回 `high_confidence` 和 `pending_review` 两种场景 |
| 错题 CRUD | `src/api/__mocks__/questions.ts` | 本地 `ref([])` 模拟增删改查 |
| 复习 | `src/api/__mocks__/review.ts` | 返回固定队列，评分后移到下一题 |
| 打印 | `src/api/__mocks__/print.ts` | 返回固定 HTML 字符串 |

**Mock 切换实现约定**：

```typescript
// src/api/questions.ts
import { VITE_USE_MOCK } from '@/config'

export const questionsApi = VITE_USE_MOCK
  ? await import('./__mocks__/questions')
  : await import('./questions.real')
```

**验收标准**：
- [ ] `VITE_USE_MOCK=true` 时，前端完整功能可运行，无任何网络请求
- [ ] `VITE_USE_MOCK=false` 时，所有 API 调用发往 `VITE_API_BASE_URL`

---

### 13.5 前端测试要求（Vitest）

每个组件至少包含：
- `RecognitionPreview.test.ts`：`high_confidence` 绿色标签 / `pending_review` 黄色警告 / 确认按钮 emit / 评分按钮禁用状态
- `QuestionCard.test.ts`：字段渲染 / LaTeX 公式标记存在 / 空 image_url 不渲染 img
- `UploadDropzone.test.ts`：拖拽触发 / 超大文件本地拒绝 / 非图片格式本地拒绝
- `ReviewCard.test.ts`：答案默认隐藏 / 点击显示 / 5 个评分按钮渲染
- `useRecognition.test.ts`：状态机流转（idle→uploading→recognizing→confirming→done）

**禁止**：在前端测试中断言 Bedrock 识别的具体文字内容。
