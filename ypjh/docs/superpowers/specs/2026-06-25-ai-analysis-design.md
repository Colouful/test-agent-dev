# AI 题目解析功能 设计文档

## 目标

在拍照识别题目的同时，AI 同步生成答案解析、知识点分析、考查要点和出错原因，存入 Question 记录，在题目详情页展示。

## 架构概述

扩展现有 Bedrock 识别 prompt，让同一次 AI 调用同时输出 `analysis` 对象。Question 表新增 `analysis` JSON 字段持久化存储。前端 QuestionDetailPage 在现有答案区块后新增"AI 解析"卡片。

**Tech Stack:** FastAPI + SQLAlchemy 2 async + SQLite(JSON) + AWS Bedrock Claude Haiku + Vue 3 + TypeScript + Tailwind CSS v3

---

## Global Constraints

- R2: Bedrock 返回必须 schema 校验，analysis 缺失 → null，不得报错
- R3: 题目必须结构化存储，analysis 是 dict | None，禁止裸字符串
- R4: confidence < 0.7 → status=pending_review（不影响 analysis 生成）
- is_question=false 时，analysis 所有字段为 null
- MOCK_BEDROCK=true 时返回固定 mock analysis（不调真实 Bedrock）
- analysis 字段为可选，null 时前端不显示 AI 解析卡片
- 不新增 API 端点；analysis 随现有 confirm 流程保存

---

## 数据模型

### Question 表新增字段

```python
# backend/models/question.py
from sqlalchemy import JSON

analysis: Mapped[dict | None] = mapped_column(JSON, default=None)
```

SQLite 将 JSON 字段存为 TEXT，SQLAlchemy 自动序列化/反序列化。

### analysis 对象结构

```json
{
  "explanation": "详细解题过程和答案解析（2-4句）",
  "knowledge_points": ["知识点1", "知识点2"],
  "key_examination": "这道题核心考查要点（1句）",
  "error_reason": "学生做错这类题的典型原因（1-2句）"
}
```

`is_question=false` 时全部为 `null`（即整个 analysis 对象为 null）。

---

## 后端改动

### 1. Prompt 扩展（`backend/prompts/recognize_question.txt`）

在现有 JSON 输出结构中增加 `analysis` 对象字段说明：

```
"analysis": {
  "explanation": "详细解题过程和答案解析，2-4句，针对 correct_answer 展开",
  "knowledge_points": ["涉及的核心知识点，1-3个，每个不超过10字"],
  "key_examination": "这道题核心考查的能力或概念，1句话",
  "error_reason": "学生做错这类题的典型原因，1-2句"
}

注意：
- 如果 is_question=false，analysis 字段整体设为 null
- 如果图片模糊无法分析，analysis 整体设为 null
- knowledge_points 必须是字符串数组，不能是字符串
```

### 2. schemas/recognition.py — RecognitionCandidate 新增 analysis

```python
class AnalysisOut(BaseModel):
    explanation: str
    knowledge_points: list[str]
    key_examination: str
    error_reason: str

class RecognitionCandidate(BaseModel):
    content: str
    correct_answer: str
    wrong_answer: str | None
    subject: str | None
    question_type: str | None
    confidence: float
    image_key: str | None
    analysis: AnalysisOut | None = None  # 新增
```

### 3. schemas/question.py — QuestionCreate 和 QuestionOut 新增 analysis

```python
class QuestionCreate(BaseModel):
    ...
    analysis: dict | None = None  # 新增

class QuestionOut(BaseModel):
    ...
    analysis: dict | None = None  # 新增
```

### 4. recognition_service.py — 解析 analysis 字段

在解析 Bedrock 返回的 JSON 后，提取 `analysis`：

```python
raw_analysis = raw.get("analysis")
analysis = None
if isinstance(raw_analysis, dict):
    # 校验必要字段存在
    if all(k in raw_analysis for k in ("explanation", "knowledge_points", "key_examination", "error_reason")):
        analysis = {
            "explanation": str(raw_analysis["explanation"]),
            "knowledge_points": [str(k) for k in raw_analysis.get("knowledge_points", []) if isinstance(k, str)],
            "key_examination": str(raw_analysis["key_examination"]),
            "error_reason": str(raw_analysis["error_reason"]),
        }
# 写入 candidate
candidate = RecognitionCandidate(..., analysis=analysis)
```

MOCK 模式下返回固定 mock analysis：
```python
MOCK_ANALYSIS = {
    "explanation": "根据第二象限的三角函数符号规则，sin>0 而 cos<0，代入勾股定理得 cos²θ=1-9/25=16/25，取负值得 cosθ=-4/5。",
    "knowledge_points": ["三角函数", "第二象限符号", "勾股定理"],
    "key_examination": "考查三角函数在各象限的符号判断能力",
    "error_reason": "学生常忽略象限限制，直接取正值，未考虑 cos 在第二象限为负。"
}
```

### 5. question_repository.create() — 保存 analysis

```python
q = Question(
    ...
    analysis=data.analysis,  # 新增
)
```

---

## 前端改动

### 1. types/index.ts — 新增 Analysis 类型

```typescript
export interface Analysis {
  explanation: string
  knowledge_points: string[]
  key_examination: string
  error_reason: string
}

// Question 接口新增字段
export interface Question {
  ...
  analysis: Analysis | null  // 新增
}
```

### 2. QuestionDetailPage.vue — 新增 AI 解析卡片

在"我的错误"区块之后，新增以下卡片（`v-if="question.analysis"`）：

```vue
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
      <span v-for="kp in question.analysis.knowledge_points" :key="kp"
        class="text-xs px-2 py-0.5 bg-blue-50 text-blue-600 rounded-full">
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
```

### 3. mock/questions.mock.ts — mock 数据加 analysis

现有 mock 题目（q-1, q-2）加上固定 analysis 数据，q-1 有 analysis，q-2 analysis 为 null（测试两种情况）。

### 4. RecognitionResult 中 candidate.analysis 透传

`api/endpoints/questions.ts` 的 `recognize()` 和 `useQuestions.confirmAndSave()` 已按现有 `candidate` 字段传递，只需确保 `QuestionCreate` 时把 `candidate.analysis` 传入即可。

---

## 文件变更清单

| 操作 | 文件 |
|------|------|
| 修改 | `backend/prompts/recognize_question.txt` |
| 修改 | `backend/models/question.py` |
| 修改 | `backend/schemas/recognition.py` |
| 修改 | `backend/schemas/question.py` |
| 修改 | `backend/services/recognition_service.py` |
| 修改 | `backend/repositories/question_repository.py` |
| 修改 | `frontend/src/types/index.ts` |
| 修改 | `frontend/src/pages/QuestionDetailPage.vue` |
| 修改 | `frontend/src/api/mock/questions.mock.ts` |
| 修改 | `frontend/src/composables/useQuestions.ts` |
