# AI 题目解析 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 拍照识别题目时，AI 同步生成答案解析、知识点、考查要点、出错原因，持久化到 Question 表，在详情页展示。

**Architecture:** 扩展现有 Bedrock prompt 输出 `analysis` 对象；`recognition_service.py` 从 raw JSON 中提取 analysis（不修改 MCP 工具）；`RecognitionResult` 内部类和 `QuestionCandidateOut` schema 新增 `analysis` 字段；Question 模型加 JSON 字段，repository 保存；前端 types / mock / detail page / upload page 全链路更新。

**Tech Stack:** FastAPI + SQLAlchemy 2 async + SQLite JSON column + AWS Bedrock Claude Haiku + Vue 3 + TypeScript + Tailwind CSS v3

## Global Constraints

- R2: analysis 缺失或格式错误 → null，不得报错，不得中断识别流程
- R3: analysis 作为 dict | None 存储，禁止裸字符串
- is_question=false 时 analysis=null
- MOCK_BEDROCK=true 时 mock 返回固定 MOCK_ANALYSIS（仅 mock_scenario="clear" 时有 analysis，其他 scenario 返回 null）
- analysis 字段全链路可选/nullable；null 时前端 AI 解析卡片不显示
- 不新增 API 端点；analysis 随现有 confirm 流程（POST /questions）保存
- 新密码最少 8 位（与本 feature 无关，保留已有规则）

---

## 文件变更清单

| 操作 | 文件 |
|------|------|
| 修改 | `backend/models/question.py` |
| 修改 | `backend/schemas/recognition.py` |
| 修改 | `backend/schemas/question.py` |
| 修改 | `backend/prompts/recognize_question.txt` |
| 修改 | `backend/services/recognition_service.py` |
| 修改 | `backend/repositories/question_repository.py` |
| 修改 | `frontend/src/types/index.ts` |
| 修改 | `frontend/src/api/mock/questions.mock.ts` |
| 修改 | `frontend/src/pages/QuestionDetailPage.vue` |
| 修改 | `frontend/src/pages/UploadPage.vue` |
| 修改 | `frontend/src/composables/useQuestions.ts` |

---

### Task 1: 后端 model + schemas（analysis 字段）

**Files:**
- Modify: `backend/models/question.py`
- Modify: `backend/schemas/recognition.py`
- Modify: `backend/schemas/question.py`
- Test: `backend/tests/test_analysis_schema.py`（新建）

**Interfaces:**
- Produces:
  - `Question.analysis: Mapped[dict | None]`（JSON column）
  - `AnalysisOut(explanation, knowledge_points, key_examination, error_reason)` Pydantic model
  - `QuestionCandidateOut.analysis: AnalysisOut | None`
  - `QuestionCreate.analysis: dict | None`
  - `QuestionOut.analysis: dict | None`

- [ ] **Step 1: 写失败测试**

新建 `backend/tests/test_analysis_schema.py`：

```python
import pytest
from pydantic import ValidationError
from backend.schemas.recognition import AnalysisOut, QuestionCandidateOut
from backend.schemas.question import QuestionCreate, QuestionOut
from datetime import datetime


def test_analysis_out_valid():
    a = AnalysisOut(
        explanation="解题过程",
        knowledge_points=["三角函数", "象限"],
        key_examination="考查象限判断",
        error_reason="忽略负号",
    )
    assert a.explanation == "解题过程"
    assert a.knowledge_points == ["三角函数", "象限"]


def test_analysis_out_missing_field():
    with pytest.raises(ValidationError):
        AnalysisOut(explanation="x", knowledge_points=[], key_examination="y")
        # error_reason missing → ValidationError


def test_candidate_out_with_analysis():
    c = QuestionCandidateOut(
        content="题目",
        correct_answer="答案",
        confidence=0.9,
        analysis=AnalysisOut(
            explanation="解析",
            knowledge_points=["知识点"],
            key_examination="考查",
            error_reason="原因",
        ),
    )
    assert c.analysis is not None
    assert c.analysis.error_reason == "原因"


def test_candidate_out_analysis_none():
    c = QuestionCandidateOut(content="题目", correct_answer="答案", confidence=0.8)
    assert c.analysis is None


def test_question_create_with_analysis():
    q = QuestionCreate(
        content="题目",
        correct_answer="答案",
        analysis={"explanation": "x", "knowledge_points": [], "key_examination": "y", "error_reason": "z"},
    )
    assert q.analysis is not None


def test_question_create_analysis_none():
    q = QuestionCreate(content="题目", correct_answer="答案")
    assert q.analysis is None
```

- [ ] **Step 2: 运行，确认失败**

```bash
cd /workshop/ypjh && backend/.venv/bin/pytest backend/tests/test_analysis_schema.py -v
```

预期：FAILED（AnalysisOut 未定义）

- [ ] **Step 3: 修改 `backend/models/question.py`，加 analysis 字段**

在 `deleted_at` 行之前加：

```python
from sqlalchemy import JSON
```

在 `last_reviewed_at` 行之后、`created_at` 行之前加：

```python
analysis: Mapped[dict | None] = mapped_column(JSON, default=None)
```

完整文件：

```python
from datetime import datetime

from sqlalchemy import JSON, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[str] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(index=True)
    subject: Mapped[str | None] = mapped_column(default=None)
    question_type: Mapped[str | None] = mapped_column(default=None)
    content: Mapped[str]
    correct_answer: Mapped[str]
    wrong_answer: Mapped[str | None] = mapped_column(default=None)
    note: Mapped[str | None] = mapped_column(default=None)
    confidence: Mapped[float] = mapped_column(default=0.0)
    image_key: Mapped[str | None] = mapped_column(default=None)
    original_filename: Mapped[str | None] = mapped_column(default=None)
    status: Mapped[str] = mapped_column(default="pending_review")
    ease_factor: Mapped[float] = mapped_column(default=2.5)
    review_count: Mapped[int] = mapped_column(default=0)
    interval_days: Mapped[int] = mapped_column(default=1)
    next_review_at: Mapped[datetime | None] = mapped_column(default=None)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(default=None)
    analysis: Mapped[dict | None] = mapped_column(JSON, default=None)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(default=None)
```

- [ ] **Step 4: 修改 `backend/schemas/recognition.py`，加 AnalysisOut + analysis 字段**

完整替换文件内容：

```python
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class AnalysisOut(BaseModel):
    explanation: str
    knowledge_points: list[str]
    key_examination: str
    error_reason: str


class QuestionCandidateOut(BaseModel):
    content: str
    correct_answer: str
    wrong_answer: str | None = None
    confidence: float
    subject: str | None = None
    question_type: str | None = None
    image_url: str | None = None  # R23: presigned URL, never raw S3 key
    analysis: AnalysisOut | None = None


class RecognitionResultOut(BaseModel):
    status: Literal["high_confidence", "pending_review", "error"]
    candidate: QuestionCandidateOut | None = None
    error_hint: str | None = None
    error_code: str | None = None
```

- [ ] **Step 5: 修改 `backend/schemas/question.py`，加 analysis 字段**

在 `QuestionCreate` 末尾加：
```python
analysis: dict | None = None
```

在 `QuestionOut` 的字段列表末尾（`updated_at` 之后）加：
```python
analysis: dict | None = None
```

完整文件：

```python
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
    analysis: dict | None = None


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
    analysis: dict | None = None

    model_config = {"from_attributes": True}


class QuestionListOut(BaseModel):
    items: list[QuestionOut]
    total: int
    limit: int
    offset: int
```

- [ ] **Step 6: 运行测试，确认通过**

```bash
cd /workshop/ypjh && backend/.venv/bin/pytest backend/tests/test_analysis_schema.py -v
```

预期：6 tests passed

- [ ] **Step 7: 运行完整测试套件，确认无回归**

```bash
cd /workshop/ypjh && backend/.venv/bin/pytest backend/tests/ -v --tb=short 2>&1 | tail -20
```

预期：全部已有测试通过（新加字段为 optional，不影响现有测试）

- [ ] **Step 8: SQLite 数据库迁移（为现有 wrongbook.db 加列）**

```bash
cd /workshop/ypjh && python3 -c "
import sqlite3
conn = sqlite3.connect('wrongbook.db')
try:
    conn.execute('ALTER TABLE questions ADD COLUMN analysis TEXT')
    conn.commit()
    print('Migration OK')
except sqlite3.OperationalError as e:
    print(f'Skip (already exists or other): {e}')
conn.close()
"
```

- [ ] **Step 9: Commit**

```bash
git add backend/models/question.py \
        backend/schemas/recognition.py \
        backend/schemas/question.py \
        backend/tests/test_analysis_schema.py
git commit -m "feat: add analysis field to Question model and schemas (AnalysisOut, QuestionCreate, QuestionOut)"
```

---

### Task 2: 后端 prompt + service + repository

**Files:**
- Modify: `backend/prompts/recognize_question.txt`
- Modify: `backend/services/recognition_service.py`
- Modify: `backend/repositories/question_repository.py`
- Test: `backend/tests/test_recognition_analysis.py`（新建）

**Interfaces:**
- Consumes:
  - `AnalysisOut` from `backend.schemas.recognition` (Task 1)
  - `QuestionCandidateOut.analysis` (Task 1)
  - `Question.analysis` (Task 1)
  - `QuestionCreate.analysis` (Task 1)
- Produces:
  - `RecognitionService.recognize()` → `RecognitionResult` 含 `analysis: dict | None`
  - `RecognitionService.recognize_upload()` → `RecognitionResultOut` 的 `candidate.analysis` 填充
  - `QuestionRepository.create()` 保存 `analysis`

- [ ] **Step 1: 写失败测试**

新建 `backend/tests/test_recognition_analysis.py`：

```python
import pytest
from backend.services.recognition_service import RecognitionService


def test_mock_clear_has_analysis():
    svc = RecognitionService(mock_scenario="clear")
    result = svc.recognize(b"fake", user_id="u1", image_key="test.jpg")
    assert result.status in ("high_confidence", "pending_review")
    assert result.analysis is not None
    assert "explanation" in result.analysis
    assert "knowledge_points" in result.analysis
    assert isinstance(result.analysis["knowledge_points"], list)
    assert "key_examination" in result.analysis
    assert "error_reason" in result.analysis


def test_mock_non_question_no_analysis():
    svc = RecognitionService(mock_scenario="non_question")
    result = svc.recognize(b"fake", user_id="u1", image_key="test.jpg")
    assert result.status == "error"
    assert result.analysis is None


def test_mock_blurry_no_analysis():
    svc = RecognitionService(mock_scenario="blurry")
    result = svc.recognize(b"fake", user_id="u1", image_key="test.jpg")
    # blurry scenario has no analysis key in mock response
    assert result.analysis is None


def test_recognize_upload_mock_analysis():
    from unittest.mock import patch, MagicMock
    svc = RecognitionService(mock_scenario="clear")
    with patch("backend.services.recognition_service.validate_image_bytes", return_value="jpg"), \
         patch("backend.services.recognition_service.fix_exif_orientation", side_effect=lambda x: x), \
         patch("backend.services.recognition_service.upload_image", return_value="u1/original/abc.jpg"), \
         patch("backend.services.recognition_service.generate_presigned_url", return_value="https://s3.example.com/img"):
        result = svc.recognize_upload(b"\xff\xd8\xff" + b"\x00" * 100, "u1", "test.jpg")
    assert result.candidate is not None
    assert result.candidate.analysis is not None
    assert result.candidate.analysis.explanation != ""
```

- [ ] **Step 2: 运行，确认失败**

```bash
cd /workshop/ypjh && backend/.venv/bin/pytest backend/tests/test_recognition_analysis.py -v
```

预期：FAILED（`result.analysis` 属性不存在）

- [ ] **Step 3: 修改 `backend/prompts/recognize_question.txt`**

完整替换文件内容：

```
你是一个专业的题目识别助手。请分析图片中的题目，严格按以下 JSON 格式返回结果，不要添加任何额外文字：

{
  "content": "印刷体题目正文（不含手写内容）",
  "correct_answer": "正确答案",
  "wrong_answer": "学生手写的错误答案（如有，否则为 null）",
  "subject": "学科（语文/数学/英语/物理/化学/生物/历史/地理/政治，识别不出为 null）",
  "question_type": "题型（single/multiple/fill/essay）",
  "confidence": 0.0到1.0之间的浮点数,
  "has_error_mark": true或false（图片中是否有红叉/圈/×/✗等错误标记）,
  "has_figure": true或false（是否含几何图/电路图/表格等图形化内容）,
  "is_question": true或false（图片是否包含题目内容）,
  "analysis": {
    "explanation": "详细解题过程和答案解析，2-4句，针对 correct_answer 展开",
    "knowledge_points": ["涉及的核心知识点，1-3个，每个不超过10字"],
    "key_examination": "这道题核心考查的能力或概念，1句话",
    "error_reason": "学生做错这类题的典型原因，1-2句"
  }
}

注意：
1. content 只包含印刷体题目，手写内容统一放入 wrong_answer
2. 数学公式保留 LaTeX 格式，如 $\frac{1}{2}$
3. 如果图片不是题目（风景/自拍等），is_question 设为 false，其他字段可为 null，analysis 整体设为 null
4. confidence 反映你对识别结果的把握程度
5. 如果图片模糊无法分析，analysis 整体设为 null
6. knowledge_points 必须是字符串数组，不能是单个字符串
```

- [ ] **Step 4: 修改 `backend/services/recognition_service.py`**

**4a. 在 `MOCK_RESPONSES` 之后（`class RecognitionResult` 之前）加入 MOCK_ANALYSIS 常量：**

```python
MOCK_ANALYSIS: dict = {
    "explanation": "根据第二象限的三角函数符号规则，sin>0 而 cos<0，代入勾股定理得 cos²θ=1-9/25=16/25，取负值得 cosθ=-4/5。",
    "knowledge_points": ["三角函数", "第二象限符号", "勾股定理"],
    "key_examination": "考查三角函数在各象限的符号判断能力",
    "error_reason": "学生常忽略象限限制，直接取正值，未考虑 cos 在第二象限为负。",
}
```

**4b. 修改 `RecognitionResult.__init__`，加 `analysis` 参数：**

```python
class RecognitionResult:
    """识别结果，包含状态和候选题目。"""

    def __init__(
        self,
        status: str,
        candidate: QuestionCandidate | None = None,
        error_hint: str | None = None,
        image_key: str | None = None,
        analysis: dict | None = None,
    ) -> None:
        self.status = status
        self.candidate = candidate
        self.error_hint = error_hint
        self.image_key = image_key
        self.analysis = analysis
```

**4c. 在 `MOCK_RESPONSES` 的 `"clear"` 条目中加 analysis：**

```python
MOCK_RESPONSES: dict[str, dict[str, Any]] = {
    "clear": {
        "content": "已知 f(x) = x² + 2x + 1，求 f(3) 的值。",
        "correct_answer": "16",
        "confidence": 0.92,
        "subject": "数学",
        "question_type": "fill",
        "analysis": {
            "explanation": "将 x=3 代入 f(x)=x²+2x+1，得 f(3)=9+6+1=16。",
            "knowledge_points": ["二次函数求值", "代入法"],
            "key_examination": "考查函数值的计算能力",
            "error_reason": "常见错误是漏算某一项或符号出错，应逐项代入后求和。",
        },
    },
    "blurry": {
        "content": "模糊识别结果",
        "correct_answer": "不确定",
        "confidence": 0.45,
    },
    "empty": {
        "content": "",
        "correct_answer": "",
    },
    "non_question": {
        "content": "",
        "correct_answer": "",
        "confidence": 0.0,
        "is_question": False,
    },
}
```

**4d. 在 `recognize()` 方法中，在 `# Step 3: R2` 之前提取 analysis：**

在 `# REQ-28: 非题目图片` 的返回之后、`# Step 3: R2` 之前插入：

```python
        # 提取 analysis（R2 扩展：缺失或格式错误 → null，不中断流程）
        raw_analysis = raw.get("analysis")
        analysis: dict | None = None
        if isinstance(raw_analysis, dict):
            required = ("explanation", "knowledge_points", "key_examination", "error_reason")
            if all(k in raw_analysis for k in required) and isinstance(raw_analysis.get("knowledge_points"), list):
                analysis = {
                    "explanation": str(raw_analysis["explanation"]),
                    "knowledge_points": [str(k) for k in raw_analysis["knowledge_points"] if isinstance(k, str)],
                    "key_examination": str(raw_analysis["key_examination"]),
                    "error_reason": str(raw_analysis["error_reason"]),
                }
```

**4e. 在 `recognize()` 的两处 return 语句中加 `analysis=analysis`：**

```python
        if is_high_confidence(candidate):
            return RecognitionResult(
                status="high_confidence",
                candidate=candidate,
                image_key=key,
                analysis=analysis,
            )
        else:
            return RecognitionResult(
                status="pending_review",
                candidate=candidate,
                error_hint=f"识别置信度 {candidate.confidence:.0%}，请手动核对",
                image_key=key,
                analysis=analysis,
            )
```

**4f. 在 `recognize_upload()` 中，将 analysis 传入 `QuestionCandidateOut`：**

找到创建 `candidate_out` 的代码块，修改为：

```python
        candidate_out = None
        if inner.candidate:
            from backend.schemas.recognition import AnalysisOut
            analysis_out = None
            if inner.analysis is not None:
                try:
                    analysis_out = AnalysisOut(**inner.analysis)
                except Exception:
                    analysis_out = None
            candidate_out = QuestionCandidateOut(
                content=inner.candidate.content,
                correct_answer=inner.candidate.correct_answer,
                wrong_answer=inner.candidate.wrong_answer,
                confidence=inner.candidate.confidence,
                subject=inner.candidate.subject,
                question_type=inner.candidate.question_type,
                image_url=generate_presigned_url(key),  # R23
                analysis=analysis_out,
            )
```

- [ ] **Step 5: 修改 `backend/repositories/question_repository.py`，保存 analysis**

在 `create()` 方法的 `Question(...)` 构造中加 `analysis=data.analysis`：

```python
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
            next_review_at=datetime.utcnow(),
            analysis=data.analysis,
        )
        session.add(q)
        await session.flush()
        return q
```

- [ ] **Step 6: 运行新测试，确认通过**

```bash
cd /workshop/ypjh && backend/.venv/bin/pytest backend/tests/test_recognition_analysis.py -v
```

预期：4 tests passed

- [ ] **Step 7: 运行完整测试套件，确认无回归**

```bash
cd /workshop/ypjh && backend/.venv/bin/pytest backend/tests/ -v --tb=short 2>&1 | tail -20
```

预期：全部已有测试通过

- [ ] **Step 8: Commit**

```bash
git add backend/prompts/recognize_question.txt \
        backend/services/recognition_service.py \
        backend/repositories/question_repository.py \
        backend/tests/test_recognition_analysis.py
git commit -m "feat: recognition service extracts analysis from Bedrock response and saves to Question"
```

---

### Task 3: 前端（types + mock + detail page + upload page）

**Files:**
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/api/mock/questions.mock.ts`
- Modify: `frontend/src/pages/QuestionDetailPage.vue`
- Modify: `frontend/src/pages/UploadPage.vue`
- Modify: `frontend/src/composables/useQuestions.ts`

**Interfaces:**
- Consumes:
  - `AnalysisOut` shape: `{ explanation, knowledge_points, key_examination, error_reason }` (Task 1)
  - `QuestionCandidateOut.analysis` in API response (Task 2)
  - `Question.analysis` in Question response (Task 1)
- Produces: 完整前端 analysis 链路

- [ ] **Step 1: 修改 `frontend/src/types/index.ts`，加 Analysis 类型**

在 `User` 接口之前加：

```typescript
export interface Analysis {
  explanation: string
  knowledge_points: string[]
  key_examination: string
  error_reason: string
}
```

在 `Question` 接口的 `updated_at: string` 之后加：

```typescript
  analysis: Analysis | null
```

在 `RecognitionResult` 的 `candidate` 类型内部（`image_key: string | null` 之后）加：

```typescript
    analysis: Analysis | null
```

完整 `types/index.ts`：

```typescript
export interface Analysis {
  explanation: string
  knowledge_points: string[]
  key_examination: string
  error_reason: string
}

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
  analysis: Analysis | null
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
    analysis: Analysis | null
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

export interface ProfileStats {
  totalQuestions: number
  dueCount: number
  reviewedToday: number
}
```

- [ ] **Step 2: 修改 `frontend/src/api/mock/questions.mock.ts`，加 analysis**

**2a.** 在 `MOCK_QUESTIONS` 的 `q-1` 条目中加（`updated_at` 行之后，逗号之前）：

```typescript
    analysis: {
      explanation: '根据第二象限的三角函数符号规则，sin>0 而 cos<0，由勾股定理 cos²θ=1-sin²θ=1-9/25=16/25，取负值得 cosθ=-4/5。',
      knowledge_points: ['三角函数', '第二象限符号', '勾股定理'],
      key_examination: '考查三角函数在各象限的符号判断能力',
      error_reason: '学生常忽略象限限制，直接取正值，未考虑 cos 在第二象限为负。',
    },
```

**2b.** 在 `q-2` 条目中加 `analysis: null`（`updated_at` 行之后）。

**2c.** 在 `mockQuestions.create()` 中，给新建的题目加 `analysis: data.analysis ?? null`。

**2d.** 在 `mockQuestions.recognize()` 的 `candidate` 对象中加：

```typescript
          analysis: {
            explanation: '将 x=2 代入 f(x)=2x²-3x+1，得 f(2)=2×4-6+1=3。注意 2x² 展开后系数为 2。',
            knowledge_points: ['二次函数求值', '代入计算'],
            key_examination: '考查多项式函数的代入求值能力',
            error_reason: '常见错误是将 2x² 误算为 (2x)²=4x²，导致结果偏大。',
          },
```

完整替换后的 `questions.mock.ts`：

```typescript
import type { ApiResponse, Analysis, Question, QuestionList, RecognitionResult } from '@/types'

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
    analysis: {
      explanation: '根据第二象限的三角函数符号规则，sin>0 而 cos<0，由勾股定理 cos²θ=1-sin²θ=1-9/25=16/25，取负值得 cosθ=-4/5。',
      knowledge_points: ['三角函数', '第二象限符号', '勾股定理'],
      key_examination: '考查三角函数在各象限的符号判断能力',
      error_reason: '学生常忽略象限限制，直接取正值，未考虑 cos 在第二象限为负。',
    },
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
    analysis: null,
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
      analysis: data.analysis ?? null,
    }
    MOCK_QUESTIONS.push(q)
    return { data: q, error: null }
  },
  async recognize(_file: File): Promise<ApiResponse<RecognitionResult>> {
    await new Promise(r => setTimeout(r, 1200))
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
          analysis: {
            explanation: '将 x=2 代入 f(x)=2x²-3x+1，得 f(2)=2×4-6+1=3。注意 2x² 展开后系数为 2。',
            knowledge_points: ['二次函数求值', '代入计算'],
            key_examination: '考查多项式函数的代入求值能力',
            error_reason: '常见错误是将 2x² 误算为 (2x)²=4x²，导致结果偏大。',
          },
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

- [ ] **Step 3: 修改 `frontend/src/composables/useQuestions.ts`，透传 analysis**

`confirmAndSave` 已接受 `Partial<Question>` 类型，`analysis` 字段会自动透传。
唯一需要确认的是 `useQuestions.ts` 使用 `Parameters<typeof mockQuestions.create>[0]` 作为类型——这个类型是 `Partial<Question>`，`analysis` 字段已在 Step 1 加入 `Question`，所以无需修改 `useQuestions.ts`。

验证：
```bash
cd /workshop/ypjh/frontend && grep -n "confirmAndSave" src/composables/useQuestions.ts
```

预期看到 `mockQuestions.create(data)` 和 `questionsApi.create(data)` 调用，类型已覆盖。

- [ ] **Step 4: 修改 `frontend/src/pages/UploadPage.vue`，在 confirmAndSave 时传入 analysis**

找到 `onConfirm` 函数中的 `confirmAndSave({...})` 调用，加入 `analysis` 字段：

```typescript
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
      analysis: recognitionResult.value.candidate.analysis ?? null,
    })
    toast?.show('录题成功！', 'success')
    router.push('/questions')
  } finally {
    saving.value = false
  }
}
```

- [ ] **Step 5: 修改 `frontend/src/pages/QuestionDetailPage.vue`，加 AI 解析卡片**

在 `<!-- 统计信息 -->` 区块之前（即 `question.note` 区块和统计区块之间），加入 AI 解析卡片。

完整替换 `QuestionDetailPage.vue`：

```vue
<!-- frontend/src/pages/QuestionDetailPage.vue -->
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { IS_MOCK, mockQuestions } from '@/api/mock'
import { questionsApi } from '@/api/endpoints/questions'
import type { Question } from '@/types'

const route = useRoute()
const question = ref<Question | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)

onMounted(async () => {
  try {
    const id = route.params.id as string
    if (IS_MOCK) {
      const resp = await mockQuestions.get(id)
      if (resp.error) {
        error.value = resp.error.message || '题目不存在'
      } else {
        question.value = resp.data
      }
    } else {
      const resp = await questionsApi.get(id)
      question.value = resp.data.data
    }
  } catch {
    error.value = '加载失败，请返回重试'
  } finally {
    loading.value = false
  }
})

const TYPE_LABELS: Record<string, string> = {
  multiple_choice: '选择题',
  fill: '填空题',
  short_answer: '简答题',
  calculation: '计算题',
}
</script>

<template>
  <div class="min-h-screen bg-gray-50 pb-20">
    <!-- 顶部标题栏 -->
    <header class="bg-white border-b sticky top-0 z-10">
      <div class="max-w-2xl mx-auto px-4 py-3 flex items-center gap-3">
        <button @click="$router.back()" class="text-gray-400 hover:text-gray-600 transition-colors">
          ←
        </button>
        <h2 class="font-semibold text-gray-900">错题详情</h2>
      </div>
    </header>

    <main class="max-w-2xl mx-auto px-4 py-4 space-y-4">
      <!-- 加载中 -->
      <div v-if="loading" class="space-y-3">
        <div class="h-6 bg-gray-200 rounded animate-pulse w-1/3"></div>
        <div class="h-32 bg-gray-200 rounded animate-pulse"></div>
        <div class="h-20 bg-gray-200 rounded animate-pulse"></div>
      </div>

      <!-- 加载失败 -->
      <div v-else-if="error" class="text-center py-16 text-gray-400">
        <div class="text-4xl mb-3">⚠️</div>
        <p>{{ error }}</p>
      </div>

      <!-- 内容 -->
      <template v-else-if="question">
        <!-- 标签行 -->
        <div class="flex flex-wrap gap-2">
          <span v-if="question.subject"
            class="text-xs px-2 py-0.5 rounded-full bg-blue-50 text-blue-600 font-medium">
            {{ question.subject }}
          </span>
          <span v-if="question.question_type && TYPE_LABELS[question.question_type]"
            class="text-xs px-2 py-0.5 rounded-full bg-purple-50 text-purple-600 font-medium">
            {{ TYPE_LABELS[question.question_type] }}
          </span>
          <span :class="[
            'text-xs px-2 py-0.5 rounded-full font-medium',
            question.status === 'confirmed'
              ? 'bg-green-50 text-green-600'
              : 'bg-yellow-50 text-yellow-600'
          ]">
            {{ question.status === 'confirmed' ? '已确认' : '待确认' }}
          </span>
        </div>

        <!-- 图片 -->
        <div v-if="question.image_url" class="bg-white rounded-2xl overflow-hidden shadow-sm">
          <img :src="question.image_url" alt="题目图片"
            class="w-full object-contain bg-gray-50 max-h-72" loading="lazy">
        </div>

        <!-- 题目内容 -->
        <div class="bg-white rounded-2xl shadow-sm p-5">
          <p class="text-xs text-gray-400 mb-2">题目内容</p>
          <p class="font-serif text-gray-800 text-base leading-relaxed whitespace-pre-wrap">
            {{ question.content }}
          </p>
        </div>

        <!-- 答案区 -->
        <div class="bg-white rounded-2xl shadow-sm p-5 space-y-4">
          <div>
            <p class="text-xs text-gray-400 mb-1.5">正确答案</p>
            <p class="text-green-700 font-medium leading-relaxed">{{ question.correct_answer }}</p>
          </div>
          <div v-if="question.wrong_answer" class="border-t border-gray-100 pt-4">
            <p class="text-xs text-gray-400 mb-1.5">我的错误</p>
            <p class="text-red-500 leading-relaxed">{{ question.wrong_answer }}</p>
          </div>
          <div v-if="question.note" class="border-t border-gray-100 pt-4">
            <p class="text-xs text-gray-400 mb-1.5">笔记</p>
            <p class="text-gray-600 italic leading-relaxed">{{ question.note }}</p>
          </div>
        </div>

        <!-- AI 解析卡片 -->
        <div v-if="question.analysis" class="bg-white rounded-2xl shadow-sm p-5 space-y-4">
          <h3 class="font-semibold text-gray-800 flex items-center gap-2">
            <span>💡</span> AI 解析
          </h3>

          <!-- 答案解析 -->
          <div>
            <p class="text-xs text-gray-400 mb-1">答案解析</p>
            <p class="text-sm text-gray-700 leading-relaxed">{{ question.analysis.explanation }}</p>
          </div>

          <!-- 知识点 -->
          <div>
            <p class="text-xs text-gray-400 mb-1.5">涉及知识点</p>
            <div class="flex flex-wrap gap-1.5">
              <span
                v-for="kp in question.analysis.knowledge_points"
                :key="kp"
                class="text-xs px-2 py-0.5 bg-blue-50 text-blue-600 rounded-full"
              >
                {{ kp }}
              </span>
            </div>
          </div>

          <!-- 考查要点 -->
          <div>
            <p class="text-xs text-gray-400 mb-1">考查要点</p>
            <p class="text-sm text-amber-700 leading-relaxed">{{ question.analysis.key_examination }}</p>
          </div>

          <!-- 为什么会出错 -->
          <div>
            <p class="text-xs text-gray-400 mb-1">为什么会出错</p>
            <p class="text-sm text-red-600 leading-relaxed">{{ question.analysis.error_reason }}</p>
          </div>
        </div>

        <!-- 统计信息 -->
        <div class="bg-white rounded-2xl shadow-sm p-5">
          <p class="text-xs text-gray-400 mb-3">复习记录</p>
          <div class="grid grid-cols-3 gap-4 text-center">
            <div>
              <p class="text-xl font-bold text-gray-800">{{ question.review_count }}</p>
              <p class="text-xs text-gray-400 mt-0.5">复习次数</p>
            </div>
            <div>
              <p class="text-xl font-bold text-gray-800">{{ question.interval_days }}</p>
              <p class="text-xs text-gray-400 mt-0.5">复习间隔(天)</p>
            </div>
            <div>
              <p class="text-xl font-bold text-gray-800">{{ question.ease_factor.toFixed(1) }}</p>
              <p class="text-xs text-gray-400 mt-0.5">难度系数</p>
            </div>
          </div>
        </div>
      </template>
    </main>
  </div>
</template>
```

- [ ] **Step 6: 运行 TypeScript 类型检查**

```bash
cd /workshop/ypjh/frontend && npm run type-check 2>&1 | tail -10
```

预期：无错误输出（vue-tsc --build 成功）

- [ ] **Step 7: 手动验证 mock 模式**

在 VITE_MOCK=true 模式下：
1. 进入"错题"列表，点击数学题（q-1）→ 详情页底部显示"💡 AI 解析"卡片，含解析/知识点/考查要点/出错原因
2. 点击英语题（q-2）→ 详情页无 AI 解析卡片（analysis=null）
3. 进入"上传"页，选图片识别后，确认录入 → 新题目在详情页有 AI 解析

- [ ] **Step 8: Commit**

```bash
git add frontend/src/types/index.ts \
        frontend/src/api/mock/questions.mock.ts \
        frontend/src/pages/QuestionDetailPage.vue \
        frontend/src/pages/UploadPage.vue \
        frontend/src/composables/useQuestions.ts
git commit -m "feat: frontend AI analysis — types, mock data, detail page card, upload flow"
```
