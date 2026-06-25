# 富解析功能 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 扩展现有 analysis JSON 字段，将 4 字段简单解析升级为：分步解析、分层知识点、结构化错因+改进建议、常见错误、同类练习题，并在 QuestionDetailPage 分层展示。

**Architecture:** 扩展 Bedrock prompt 一次返回新结构；后端 `AnalysisOut` 替换为 5 个子 Pydantic 模型；`recognition_service` 更新 required key 检查；前端 `Analysis` 类型扩展，`QuestionDetailPage` AI 解析卡片分层渲染，兼容旧格式数据。

**Tech Stack:** FastAPI + Pydantic v2 + SQLAlchemy 2 async + SQLite(JSON) + AWS Bedrock Claude Haiku + Vue 3 + TypeScript + Tailwind CSS v3

## Global Constraints

- R2: analysis 缺失或格式不合法 → null，不报错，不中断识别流程
- R3: analysis 是 dict | None，禁止裸字符串
- 不新增 API 端点；analysis 随现有 confirm 流程保存
- 旧数据兼容：`analysis` 含旧字段（`explanation` 存在）时前端降级渲染，不报错
- MOCK_BEDROCK=true 时返回固定 mock analysis（新结构）
- is_question=false 时 analysis=null
- `error_analysis.type` 必须是以下之一：知识缺失、概念混淆、条件遗漏、计算错误、解题方法错误
- `solution_steps` 至少 1 步，不超过 5 步
- `practice_questions` 生成 1 道同类练习题
- `knowledge_points` 各数组可为空数组 []，不能省略 key

---

## 文件变更清单

| 操作 | 文件 | 说明 |
|------|------|------|
| 修改 | `backend/prompts/recognize_question.txt` | 替换 analysis 对象为新结构 |
| 修改 | `backend/schemas/recognition.py` | 新增 5 个子模型，替换 AnalysisOut |
| 修改 | `backend/services/recognition_service.py` | 更新 mock + required key 检查 |
| 修改 | `backend/tests/test_analysis_schema.py` | 更新 schema 测试 |
| 修改 | `backend/tests/test_recognition_analysis.py` | 更新 mock analysis 断言 |
| 修改 | `frontend/src/types/index.ts` | 扩展 Analysis 接口 |
| 修改 | `frontend/src/api/mock/questions.mock.ts` | 更新 mock 数据为新结构 |
| 修改 | `frontend/src/pages/QuestionDetailPage.vue` | 分层 AI 解析卡片 |

---

### Task 1: 后端 schema + prompt（新 AnalysisOut 结构）

**Files:**
- Modify: `backend/schemas/recognition.py`
- Modify: `backend/prompts/recognize_question.txt`
- Modify: `backend/tests/test_analysis_schema.py`

**Interfaces:**
- Produces:
  - `SolutionStep(step: int, title: str, content: str)`
  - `KnowledgePoints(core: list[str], prerequisite: list[str], related: list[str])`
  - `ErrorAnalysis(type: str, reason: str, improvement: list[str])`
  - `PracticeQuestion(content: str, answer: str, explanation: str)`
  - `AnalysisOut(solution_summary, solution_steps, knowledge_points, key_examination, error_analysis, common_mistakes, practice_questions)`
  - `QuestionCandidateOut.analysis: AnalysisOut | None = None` （不变）

- [ ] **Step 1: 写失败测试**

替换 `backend/tests/test_analysis_schema.py` 全部内容：

```python
import pytest
from pydantic import ValidationError
from backend.schemas.recognition import (
    AnalysisOut, SolutionStep, KnowledgePoints,
    ErrorAnalysis, PracticeQuestion, QuestionCandidateOut,
)
from backend.schemas.question import QuestionCreate, QuestionOut
from datetime import datetime


def test_solution_step_valid():
    s = SolutionStep(step=1, title="判断增减性", content="k>0，图像上升")
    assert s.step == 1
    assert s.title == "判断增减性"


def test_knowledge_points_defaults():
    kp = KnowledgePoints(core=["一次函数"])
    assert kp.prerequisite == []
    assert kp.related == []


def test_error_analysis_valid():
    ea = ErrorAnalysis(type="条件遗漏", reason="忽略截距条件", improvement=["先看 k 再看 b"])
    assert ea.type == "条件遗漏"
    assert len(ea.improvement) == 1


def test_practice_question_valid():
    pq = PracticeQuestion(content="已知 y=2x-1，图像在哪些象限？", answer="一三四象限", explanation="k>0上升，b<0截距负")
    assert pq.answer == "一三四象限"


def test_analysis_out_valid():
    a = AnalysisOut(
        solution_summary="先看 k 再看 b",
        solution_steps=[SolutionStep(step=1, title="判断增减性", content="k>0上升")],
        knowledge_points=KnowledgePoints(core=["一次函数"]),
        key_examination="考查 k、b 对图像的影响",
        error_analysis=ErrorAnalysis(type="条件遗漏", reason="忽略截距", improvement=["看截距"]),
    )
    assert a.solution_summary == "先看 k 再看 b"
    assert len(a.solution_steps) == 1
    assert a.common_mistakes == []
    assert a.practice_questions == []


def test_analysis_out_missing_required():
    with pytest.raises(ValidationError):
        AnalysisOut(
            solution_summary="思路",
            solution_steps=[],
            knowledge_points=KnowledgePoints(core=[]),
            # key_examination 缺失 → ValidationError
            error_analysis=ErrorAnalysis(type="计算错误", reason="x", improvement=[]),
        )


def test_candidate_out_with_new_analysis():
    a = AnalysisOut(
        solution_summary="代入计算",
        solution_steps=[SolutionStep(step=1, title="代入", content="x=3 代入得 16")],
        knowledge_points=KnowledgePoints(core=["函数求值"]),
        key_examination="考查代入求值",
        error_analysis=ErrorAnalysis(type="计算错误", reason="漏算", improvement=["逐项代入"]),
        practice_questions=[PracticeQuestion(content="求 f(2)", answer="3", explanation="代入得 3")],
    )
    c = QuestionCandidateOut(content="题目", correct_answer="答案", confidence=0.9, analysis=a)
    assert c.analysis is not None
    assert c.analysis.key_examination == "考查代入求值"
    assert len(c.analysis.practice_questions) == 1


def test_candidate_out_analysis_none():
    c = QuestionCandidateOut(content="题目", correct_answer="答案", confidence=0.8)
    assert c.analysis is None


def test_question_create_with_analysis():
    q = QuestionCreate(
        content="题目",
        correct_answer="答案",
        analysis={
            "solution_summary": "思路",
            "solution_steps": [{"step": 1, "title": "步骤", "content": "内容"}],
            "knowledge_points": {"core": ["知识点"], "prerequisite": [], "related": []},
            "key_examination": "考查",
            "error_analysis": {"type": "计算错误", "reason": "出错", "improvement": []},
        },
    )
    assert q.analysis is not None


def test_question_create_analysis_none():
    q = QuestionCreate(content="题目", correct_answer="答案")
    assert q.analysis is None
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd /workshop/ypjh/backend && source .venv/bin/activate && python -m pytest tests/test_analysis_schema.py -v 2>&1 | tail -20
```

预期：多个 `ImportError` 或 `ValidationError` 失败，因为 `SolutionStep` 等类型尚未定义。

- [ ] **Step 3: 替换 `backend/schemas/recognition.py`**

```python
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class SolutionStep(BaseModel):
    step: int
    title: str
    content: str


class KnowledgePoints(BaseModel):
    core: list[str] = []
    prerequisite: list[str] = []
    related: list[str] = []


class ErrorAnalysis(BaseModel):
    type: str
    reason: str
    improvement: list[str] = []


class PracticeQuestion(BaseModel):
    content: str
    answer: str
    explanation: str


class AnalysisOut(BaseModel):
    solution_summary: str
    solution_steps: list[SolutionStep]
    knowledge_points: KnowledgePoints
    key_examination: str
    error_analysis: ErrorAnalysis
    common_mistakes: list[str] = []
    practice_questions: list[PracticeQuestion] = []


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

- [ ] **Step 4: 替换 `backend/prompts/recognize_question.txt`**

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
    "solution_summary": "一句话解题思路，不超过30字",
    "solution_steps": [
      { "step": 1, "title": "步骤标题（5字以内）", "content": "具体推导过程，1-2句" },
      { "step": 2, "title": "步骤标题", "content": "推导过程" }
    ],
    "knowledge_points": {
      "core": ["本题直接考查的知识点，1-2个，每个不超过12字"],
      "prerequisite": ["解题前置知识，0-3个，每个不超过12字"],
      "related": ["可延伸的关联知识，0-3个，每个不超过12字"]
    },
    "key_examination": "本题核心考查的能力或概念，1句话",
    "error_analysis": {
      "type": "错误类型（知识缺失/概念混淆/条件遗漏/计算错误/解题方法错误 之一）",
      "reason": "学生出错的具体原因，1-2句",
      "improvement": ["具体可执行的改进建议，1-3条"]
    },
    "common_mistakes": ["该类题学生常见错误，1-2条"],
    "practice_questions": [
      {
        "content": "同类练习题题目内容",
        "answer": "答案",
        "explanation": "简短解析，1-2句"
      }
    ]
  }
}

注意：
1. content 只包含印刷体题目，手写内容统一放入 wrong_answer
2. 数学公式保留 LaTeX 格式，如 $\frac{1}{2}$
3. 如果图片不是题目（风景/自拍等），is_question 设为 false，analysis 整体设为 null
4. confidence 反映你对识别结果的把握程度
5. 如果图片模糊无法分析，analysis 整体设为 null
6. solution_steps 至少 1 步，不超过 5 步
7. knowledge_points 各数组可为空数组 []，但不能省略 core/prerequisite/related 三个 key
8. error_analysis.type 必须是：知识缺失、概念混淆、条件遗漏、计算错误、解题方法错误 之一
9. practice_questions 生成 1 道同类练习题
```

- [ ] **Step 5: 运行测试确认通过**

```bash
cd /workshop/ypjh/backend && source .venv/bin/activate && python -m pytest tests/test_analysis_schema.py -v 2>&1 | tail -20
```

预期：`10 passed`

- [ ] **Step 6: Commit**

```bash
cd /workshop/ypjh && git add backend/schemas/recognition.py backend/prompts/recognize_question.txt backend/tests/test_analysis_schema.py
git commit -m "feat: expand AnalysisOut to rich structure — solution steps, layered knowledge, error analysis, practice questions"
```

---

### Task 2: recognition_service mock + 提取逻辑 + 测试

**Files:**
- Modify: `backend/services/recognition_service.py`
- Modify: `backend/tests/test_recognition_analysis.py`

**Interfaces:**
- Consumes: `AnalysisOut`, `SolutionStep`, `KnowledgePoints`, `ErrorAnalysis`, `PracticeQuestion` from Task 1
- Produces: `RecognitionResult.analysis` dict 使用新结构的 required keys

- [ ] **Step 1: 写失败测试**

替换 `backend/tests/test_recognition_analysis.py` 全部内容：

```python
import pytest
from backend.services.recognition_service import RecognitionService


def test_mock_clear_has_new_analysis():
    """MOCK 'clear' scenario 必须返回新格式 analysis（含 solution_summary 等）"""
    svc = RecognitionService(mock_scenario="clear")
    result = svc.recognize(b"fake", user_id="u1", image_key="test.jpg")
    assert result.status in ("high_confidence", "pending_review")
    assert result.analysis is not None
    # 新必填字段
    assert "solution_summary" in result.analysis
    assert "solution_steps" in result.analysis
    assert isinstance(result.analysis["solution_steps"], list)
    assert len(result.analysis["solution_steps"]) >= 1
    assert "knowledge_points" in result.analysis
    kp = result.analysis["knowledge_points"]
    assert isinstance(kp, dict)
    assert "core" in kp and "prerequisite" in kp and "related" in kp
    assert "key_examination" in result.analysis
    assert "error_analysis" in result.analysis
    ea = result.analysis["error_analysis"]
    assert "type" in ea and "reason" in ea and "improvement" in ea


def test_mock_clear_has_practice_questions():
    svc = RecognitionService(mock_scenario="clear")
    result = svc.recognize(b"fake", user_id="u1", image_key="test.jpg")
    assert result.analysis is not None
    pqs = result.analysis.get("practice_questions", [])
    assert isinstance(pqs, list)
    assert len(pqs) >= 1
    pq = pqs[0]
    assert "content" in pq and "answer" in pq and "explanation" in pq


def test_mock_non_question_no_analysis():
    svc = RecognitionService(mock_scenario="non_question")
    result = svc.recognize(b"fake", user_id="u1", image_key="test.jpg")
    assert result.status == "error"
    assert result.analysis is None


def test_mock_blurry_no_analysis():
    svc = RecognitionService(mock_scenario="blurry")
    result = svc.recognize(b"fake", user_id="u1", image_key="test.jpg")
    assert result.analysis is None


def test_analysis_missing_required_key_returns_null():
    """analysis dict 缺少 solution_summary 时应返回 null（R2）"""
    from unittest.mock import patch
    svc = RecognitionService(mock_scenario="clear")
    bad_analysis = {
        # solution_summary 缺失
        "solution_steps": [{"step": 1, "title": "步骤", "content": "内容"}],
        "knowledge_points": {"core": [], "prerequisite": [], "related": []},
        "key_examination": "考查",
        "error_analysis": {"type": "计算错误", "reason": "出错", "improvement": []},
    }
    broken_response = {
        "content": "题目", "correct_answer": "答案", "confidence": 0.9,
        "subject": "数学", "question_type": "fill", "analysis": bad_analysis,
    }
    with patch.object(svc, "_call_bedrock", return_value=broken_response):
        result = svc.recognize(b"fake", user_id="u1", image_key="test.jpg")
    assert result.analysis is None


def test_recognize_upload_mock_has_new_analysis():
    from unittest.mock import patch
    svc = RecognitionService(mock_scenario="clear")
    with patch("backend.services.recognition_service.validate_image_bytes", return_value="jpg"), \
         patch("backend.services.recognition_service.fix_exif_orientation", side_effect=lambda x: x), \
         patch("backend.services.recognition_service.upload_image", return_value="u1/original/abc.jpg"), \
         patch("backend.services.recognition_service.generate_presigned_url", return_value="https://s3.example.com/img"):
        result = svc.recognize_upload(b"\xff\xd8\xff" + b"\x00" * 100, "u1", "test.jpg")
    assert result.candidate is not None
    assert result.candidate.analysis is not None
    assert result.candidate.analysis.solution_summary != ""
    assert len(result.candidate.analysis.solution_steps) >= 1
    assert len(result.candidate.analysis.practice_questions) >= 1
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd /workshop/ypjh/backend && source .venv/bin/activate && python -m pytest tests/test_recognition_analysis.py -v 2>&1 | tail -20
```

预期：`test_mock_clear_has_new_analysis` 等失败，因为 mock 仍是旧结构。

- [ ] **Step 3: 更新 `recognition_service.py` 中 MOCK_RESPONSES["clear"] 的 analysis**

找到 `MOCK_RESPONSES` 字典中的 `"clear"` 条目，将其 `"analysis"` 值替换为：

```python
"analysis": {
    "solution_summary": "将 x=3 代入 f(x)=x²+2x+1，逐项计算后求和",
    "solution_steps": [
        {"step": 1, "title": "代入 x=3", "content": "将 x=3 代入，得 f(3)=3²+2×3+1"},
        {"step": 2, "title": "逐项计算", "content": "9+6+1=16，所以 f(3)=16"},
    ],
    "knowledge_points": {
        "core": ["二次函数求值", "代入法"],
        "prerequisite": ["多项式运算"],
        "related": ["函数定义域", "值域"],
    },
    "key_examination": "考查多项式函数代入求值的计算能力",
    "error_analysis": {
        "type": "计算错误",
        "reason": "学生常将 x²+2x+1 中的 x² 误算为 (x+1)²，导致结果偏差",
        "improvement": ["代入时逐项展开写清楚", "计算后代回原式验证"],
    },
    "common_mistakes": [
        "将 x²+2x+1 直接因式分解为 (x+1)² 后代入，跳过展开步骤",
        "漏算常数项 +1",
    ],
    "practice_questions": [
        {
            "content": "已知 g(x)=x²-4x+3，求 g(5) 的值。",
            "answer": "8",
            "explanation": "将 x=5 代入：25-20+3=8",
        }
    ],
},
```

- [ ] **Step 4: 更新 `recognize()` 方法中的 analysis 提取/验证逻辑**

找到 `recognize()` 方法中以下代码段（提取 analysis 的部分）：

```python
        raw_analysis = raw.pop("analysis", None)
        analysis: dict | None = None
        if isinstance(raw_analysis, dict):
            required = ("explanation", "knowledge_points", "key_examination", "error_reason")
            if all(k in raw_analysis for k in required) and isinstance(raw_analysis.get("knowledge_points"), list):
                analysis = {
                    "explanation": str(raw_analysis["explanation"]),
                    "knowledge_points": [str(k) for k in raw_analysis["knowledge_points"]],
                    "key_examination": str(raw_analysis["key_examination"]),
                    "error_reason": str(raw_analysis["error_reason"]),
                }
```

替换为：

```python
        raw_analysis = raw.pop("analysis", None)
        analysis: dict | None = None
        if isinstance(raw_analysis, dict):
            required_new = ("solution_summary", "solution_steps", "knowledge_points",
                            "key_examination", "error_analysis")
            if all(k in raw_analysis for k in required_new):
                try:
                    from backend.schemas.recognition import AnalysisOut
                    validated = AnalysisOut.model_validate(raw_analysis)
                    analysis = validated.model_dump()
                except Exception as exc:
                    logging.warning("AnalysisOut validation failed: %s", exc)
                    analysis = None
```

- [ ] **Step 5: 更新 `recognize_upload()` 中的 `AnalysisOut` 构建**

找到 `recognize_upload()` 中构建 `analysis_out` 的代码（大约如下）：

```python
                    analysis_out = AnalysisOut(**inner.analysis)
```

确认这段代码不变——因为 `inner.analysis` 已经是 `AnalysisOut` 实例（`recognize()` 返回的 `analysis` dict 通过 `model_dump()` 序列化，`recognize_upload` 重新用 `AnalysisOut(**inner.analysis)` 构建）。

实际检查 `recognize_upload` 中的逻辑：

```bash
grep -n "analysis_out\|AnalysisOut" /workshop/ypjh/backend/services/recognition_service.py
```

如果看到：
```python
analysis_out = AnalysisOut(**inner.analysis) if inner.analysis else None
```
则保持不变，因为 `inner.analysis` 是通过 `model_dump()` 得到的 dict，`AnalysisOut(**dict)` 可以正常构建。

- [ ] **Step 6: 运行全套测试确认通过**

```bash
cd /workshop/ypjh/backend && source .venv/bin/activate && python -m pytest tests/test_recognition_analysis.py tests/test_analysis_schema.py -v 2>&1 | tail -25
```

预期：全部通过。

- [ ] **Step 7: 运行完整测试套件**

```bash
cd /workshop/ypjh/backend && source .venv/bin/activate && python -m pytest tests/ -q 2>&1 | tail -10
```

预期：88+ passed（旧测试不因本次改动回归）

- [ ] **Step 8: Commit**

```bash
cd /workshop/ypjh && git add backend/services/recognition_service.py backend/tests/test_recognition_analysis.py
git commit -m "feat: update recognition_service to extract and validate new rich analysis structure"
```

---

### Task 3: 前端 types + mock + QuestionDetailPage 分层渲染

**Files:**
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/api/mock/questions.mock.ts`
- Modify: `frontend/src/pages/QuestionDetailPage.vue`

**Interfaces:**
- Consumes: 新的 `AnalysisOut` 结构（Task 1 定义）

- [ ] **Step 1: 更新 `frontend/src/types/index.ts`**

将现有 `Analysis` 接口替换为：

```typescript
export interface SolutionStep {
  step: number
  title: string
  content: string
}

export interface KnowledgePoints {
  core: string[]
  prerequisite: string[]
  related: string[]
}

export interface ErrorAnalysis {
  type: string
  reason: string
  improvement: string[]
}

export interface PracticeQuestion {
  content: string
  answer: string
  explanation: string
}

export interface Analysis {
  // 新格式字段
  solution_summary?: string
  solution_steps?: SolutionStep[]
  knowledge_points?: KnowledgePoints | string[]
  key_examination?: string
  error_analysis?: ErrorAnalysis
  common_mistakes?: string[]
  practice_questions?: PracticeQuestion[]
  // 旧格式兼容字段（已有数据可能含这些 key）
  explanation?: string
  error_reason?: string
}
```

其余接口（`User`, `Question`, `RecognitionResult` 等）不变——`analysis: Analysis | null` 字段类型保持，`Analysis` 接口扩展后自动兼容。

- [ ] **Step 2: 更新 `frontend/src/api/mock/questions.mock.ts`**

将 `MOCK_QUESTIONS` 中 `q-1` 的 `analysis` 替换为新结构，`q-2` 保持 `analysis: null`。

将 `mockQuestions.recognize()` 的 `candidate.analysis` 替换为新结构。

完整替换后的文件：

```typescript
import type { ApiResponse, Analysis, Question, QuestionList, RecognitionResult } from '@/types'

let _idCounter = 1

const MOCK_ANALYSIS_RICH: Analysis = {
  solution_summary: '根据第二象限符号规则，sin>0 而 cos<0，用勾股定理求 cos',
  solution_steps: [
    { step: 1, title: '确定象限', content: 'θ∈(0,π) 且 sinθ>0，θ 在第一或第二象限' },
    { step: 2, title: '应用勾股', content: 'cos²θ=1-sin²θ=1-9/25=16/25' },
    { step: 3, title: '确定符号', content: 'θ 在第二象限，cosθ<0，取负值得 cosθ=-4/5' },
  ],
  knowledge_points: {
    core: ['三角函数', '第二象限符号'],
    prerequisite: ['勾股定理', '象限定义'],
    related: ['正弦定理', '余弦定理'],
  },
  key_examination: '考查三角函数在各象限的符号判断及勾股定理应用',
  error_analysis: {
    type: '条件遗漏',
    reason: '学生常忽略象限限制，直接取正值，未考虑 cos 在第二象限为负',
    improvement: ['判断三角函数值先确认角所在象限', '取平方根后根据象限确定正负号'],
  },
  common_mistakes: [
    '只应用勾股定理取正值，忽略象限符号',
    '将 θ∈(0,π) 理解为第一象限',
  ],
  practice_questions: [
    {
      content: '已知 cosα=-3/5，α∈(π/2, π)，求 sinα 的值。',
      answer: 'sinα=4/5',
      explanation: '第二象限 sin>0，由 sin²α=1-9/25=16/25，取正值得 4/5',
    },
  ],
}

const MOCK_RECOGNIZE_ANALYSIS: Analysis = {
  solution_summary: '将 x=2 代入 f(x)=2x²-3x+1，逐项计算后求和',
  solution_steps: [
    { step: 1, title: '代入 x=2', content: '将 x=2 代入，得 f(2)=2×4-3×2+1' },
    { step: 2, title: '逐项计算', content: '8-6+1=3，所以 f(2)=3' },
  ],
  knowledge_points: {
    core: ['二次函数求值', '代入法'],
    prerequisite: ['多项式运算'],
    related: ['函数定义域'],
  },
  key_examination: '考查多项式函数代入求值的计算能力',
  error_analysis: {
    type: '计算错误',
    reason: '常见错误是将 2x² 误算为 (2x)²=4x²，导致结果偏大',
    improvement: ['代入时逐项展开写清楚', '计算后代回原式验证'],
  },
  common_mistakes: [
    '将 2x² 错误展开为 (2x)²',
    '漏算常数项',
  ],
  practice_questions: [
    {
      content: '已知 g(x)=x²-4x+3，求 g(5) 的值。',
      answer: '8',
      explanation: '将 x=5 代入：25-20+3=8',
    },
  ],
}

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
    analysis: MOCK_ANALYSIS_RICH,
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
          analysis: MOCK_RECOGNIZE_ANALYSIS,
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

- [ ] **Step 3: 替换 `frontend/src/pages/QuestionDetailPage.vue` 的 AI 解析卡片**

找到现有的 AI 解析卡片（`<!-- AI 解析卡片 -->` 注释到对应 `</div>`），整体替换为：

```vue
<!-- AI 解析卡片 -->
<div v-if="question.analysis" class="bg-white rounded-2xl shadow-sm p-5 space-y-5">
  <h3 class="font-semibold text-gray-800 flex items-center gap-2">
    <span>💡</span> AI 解析
  </h3>

  <!-- 新格式：解题思路 -->
  <div v-if="question.analysis.solution_summary" class="bg-gray-50 rounded-lg p-3">
    <p class="text-xs text-gray-400 mb-1">解题思路</p>
    <p class="text-sm text-gray-700 leading-relaxed">{{ question.analysis.solution_summary }}</p>
  </div>
  <!-- 旧格式降级 -->
  <div v-else-if="question.analysis.explanation" class="bg-gray-50 rounded-lg p-3">
    <p class="text-xs text-gray-400 mb-1">答案解析</p>
    <p class="text-sm text-gray-700 leading-relaxed">{{ question.analysis.explanation }}</p>
  </div>

  <!-- 分步解析 -->
  <div v-if="question.analysis.solution_steps && question.analysis.solution_steps.length">
    <p class="text-xs text-gray-400 mb-2">分步解析</p>
    <div class="space-y-2">
      <div
        v-for="step in question.analysis.solution_steps"
        :key="step.step"
        class="flex gap-3 items-start"
      >
        <span class="shrink-0 w-6 h-6 rounded-full bg-primary-100 text-primary-600
                     text-xs font-bold flex items-center justify-center mt-0.5">
          {{ step.step }}
        </span>
        <div>
          <p class="text-sm font-medium text-gray-700">{{ step.title }}</p>
          <p class="text-sm text-gray-500 leading-relaxed mt-0.5">{{ step.content }}</p>
        </div>
      </div>
    </div>
  </div>

  <!-- 知识点 -->
  <div v-if="question.analysis.knowledge_points">
    <p class="text-xs text-gray-400 mb-1.5">涉及知识点</p>
    <!-- 新格式：分层知识点 -->
    <template v-if="!Array.isArray(question.analysis.knowledge_points)">
      <div class="flex flex-wrap gap-1.5">
        <span
          v-for="kp in (question.analysis.knowledge_points as any).core"
          :key="'core-'+kp"
          class="text-xs px-2 py-0.5 bg-blue-50 text-blue-600 rounded-full"
        >{{ kp }}</span>
        <span
          v-for="kp in (question.analysis.knowledge_points as any).prerequisite"
          :key="'pre-'+kp"
          class="text-xs px-2 py-0.5 bg-gray-100 text-gray-500 rounded-full"
        >前置: {{ kp }}</span>
        <span
          v-for="kp in (question.analysis.knowledge_points as any).related"
          :key="'rel-'+kp"
          class="text-xs px-2 py-0.5 bg-green-50 text-green-600 rounded-full"
        >关联: {{ kp }}</span>
      </div>
    </template>
    <!-- 旧格式降级：list[str] -->
    <template v-else>
      <div class="flex flex-wrap gap-1.5">
        <span
          v-for="kp in (question.analysis.knowledge_points as string[])"
          :key="kp"
          class="text-xs px-2 py-0.5 bg-blue-50 text-blue-600 rounded-full"
        >{{ kp }}</span>
      </div>
    </template>
  </div>

  <!-- 考查要点 -->
  <div v-if="question.analysis.key_examination">
    <p class="text-xs text-gray-400 mb-1">考查要点</p>
    <p class="text-sm text-amber-700 leading-relaxed">{{ question.analysis.key_examination }}</p>
  </div>

  <!-- 错因分析（新格式） -->
  <div v-if="question.analysis.error_analysis">
    <p class="text-xs text-gray-400 mb-2">错因分析</p>
    <div class="space-y-2">
      <span class="inline-block text-xs px-2 py-0.5 bg-red-50 text-red-600 rounded-full font-medium">
        {{ question.analysis.error_analysis.type }}
      </span>
      <p class="text-sm text-red-600 leading-relaxed">{{ question.analysis.error_analysis.reason }}</p>
      <div v-if="question.analysis.error_analysis.improvement.length" class="space-y-1 pt-1">
        <p class="text-xs text-gray-400">改进建议</p>
        <p
          v-for="(tip, i) in question.analysis.error_analysis.improvement"
          :key="i"
          class="text-sm text-green-700 leading-relaxed flex gap-1.5"
        >
          <span class="shrink-0">✓</span>{{ tip }}
        </p>
      </div>
    </div>
  </div>
  <!-- 旧格式降级：error_reason -->
  <div v-else-if="question.analysis.error_reason">
    <p class="text-xs text-gray-400 mb-1">为什么会出错</p>
    <p class="text-sm text-red-600 leading-relaxed">{{ question.analysis.error_reason }}</p>
  </div>

  <!-- 常见错误 -->
  <div v-if="question.analysis.common_mistakes && question.analysis.common_mistakes.length">
    <p class="text-xs text-gray-400 mb-1.5">常见错误</p>
    <div class="space-y-1">
      <div
        v-for="(m, i) in question.analysis.common_mistakes"
        :key="i"
        class="text-sm text-yellow-700 bg-yellow-50 border-l-2 border-yellow-400 px-3 py-1.5 rounded-r-lg"
      >
        ⚠️ {{ m }}
      </div>
    </div>
  </div>

  <!-- 举一反三 -->
  <div v-if="question.analysis.practice_questions && question.analysis.practice_questions.length">
    <p class="text-xs text-gray-400 mb-2">📝 举一反三</p>
    <div
      v-for="(pq, i) in question.analysis.practice_questions"
      :key="i"
      class="border border-gray-200 rounded-xl p-4 space-y-3"
    >
      <p class="text-sm text-gray-800 leading-relaxed whitespace-pre-wrap">{{ pq.content }}</p>
      <PracticeAnswerToggle :answer="pq.answer" :explanation="pq.explanation" />
    </div>
  </div>
</div>
```

注意：`PracticeAnswerToggle` 是一个内联子组件，在同一文件 `<script setup>` 中用 `defineComponent` 定义（见 Step 4）。

- [ ] **Step 4: 在 `QuestionDetailPage.vue` 的 `<script setup>` 中添加 `PracticeAnswerToggle` 组件和 `showAnswers` 状态**

在现有 `<script setup>` 中，在 `const question = ref...` 之前加入：

```typescript
import { defineComponent, h, ref as vref } from 'vue'

const PracticeAnswerToggle = defineComponent({
  props: { answer: String, explanation: String },
  setup(props) {
    const show = vref(false)
    return () => h('div', [
      !show.value
        ? h('button', {
            onClick: () => { show.value = true },
            class: 'text-xs text-primary-500 border border-primary-300 rounded-lg px-3 py-1.5 hover:bg-primary-50 transition-colors',
          }, '查看答案')
        : h('div', { class: 'space-y-1' }, [
            h('p', { class: 'text-sm font-medium text-green-700' }, `答案：${props.answer}`),
            h('p', { class: 'text-xs text-gray-500 leading-relaxed mt-1' }, props.explanation),
          ]),
    ])
  },
})
```

- [ ] **Step 5: 运行 TypeScript 类型检查**

```bash
cd /workshop/ypjh/frontend && npm run type-check 2>&1 | tail -15
```

预期：无错误。如有类型错误（常见于 `knowledge_points` 联合类型），在相关 `v-for` 加 `as any` 强转即可（已在模板代码中处理）。

- [ ] **Step 6: Commit**

```bash
cd /workshop/ypjh && git add frontend/src/types/index.ts frontend/src/api/mock/questions.mock.ts frontend/src/pages/QuestionDetailPage.vue
git commit -m "feat: frontend rich analysis — layered knowledge points, solution steps, error analysis card, practice questions"
```

---

### Task 4: 部署

**Files:** 无代码变更，仅运行时操作

- [ ] **Step 1: 构建前端**

```bash
cd /workshop/ypjh/frontend && npm run build 2>&1 | tail -8
```

预期：`✓ built in ~4s`

- [ ] **Step 2: 重启前端服务**

```bash
kill $(pgrep -f "serve-frontend.js") 2>/dev/null
sleep 2
node /workshop/ypjh/serve-frontend.js > /tmp/wrongbook-frontend.log 2>&1 &
echo "Frontend PID: $!"
sleep 2 && curl -s http://localhost:3000/ | grep -o "<title>.*</title>"
```

预期：`<title>错题本</title>`

- [ ] **Step 3: 验证后端日志无错误**

```bash
tail -20 /tmp/wrongbook-backend.log
```

预期：无 ERROR 行；如有 Bedrock 凭证过期错误，用新凭证重启后端（见 DEPLOYMENT.md）。
