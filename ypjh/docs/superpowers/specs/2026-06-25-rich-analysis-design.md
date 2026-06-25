# 错题本富解析功能 设计文档

## 目标

将现有单次 Bedrock 调用返回的简单 4 字段解析，升级为完整的结构化解析：分步骤解题、分层知识点、错因诊断+改进建议、举一反三练习题。

## 架构概述

扩展现有 `analysis` JSON 字段（`Question.analysis`），不新增数据库列，不新增 API 端点。扩展 Bedrock prompt，一次调用同时返回所有新字段。前端 `QuestionDetailPage` 替换现有 AI 解析卡片为分层展示。

**Tech Stack:** FastAPI + SQLAlchemy 2 async + SQLite(JSON) + AWS Bedrock Claude Haiku + Vue 3 + TypeScript + Tailwind CSS v3

---

## Global Constraints

- R2: analysis 字段缺失或格式不合法 → null，不报错
- R3: analysis 是 dict | None，禁止裸字符串
- 不新增 API 端点；analysis 随现有 confirm 流程保存
- 旧数据兼容：`analysis` 含旧字段（`explanation` 存在）时前端降级渲染，不报错
- MOCK_BEDROCK=true 时返回固定 mock analysis
- is_question=false 时 analysis=null

---

## 新 analysis JSON 结构

```json
{
  "solution_summary": "一句话解题思路",
  "solution_steps": [
    { "step": 1, "title": "判断函数增减性", "content": "因为 k>0，图像从左向右上升。" },
    { "step": 2, "title": "判断截距位置", "content": "因为 b<0，图像与 y 轴交于负半轴。" }
  ],
  "knowledge_points": {
    "core": ["一次函数图像与系数关系"],
    "prerequisite": ["平面直角坐标系", "函数增减性"],
    "related": ["一次函数与方程"]
  },
  "key_examination": "考查 k、b 对图像影响的综合判断能力",
  "error_analysis": {
    "type": "条件遗漏",
    "reason": "已判断出 k>0 图像上升，但忽略了 b<0 对截距的影响。",
    "improvement": ["判断图像时先看 k 再看 b", "做完后逐个检查题目条件是否都用到了"]
  },
  "common_mistakes": ["只判断增减性，忽略截距", "混淆 k 和 b 的作用"],
  "practice_questions": [
    {
      "content": "已知 y=2x-1，判断图像位于哪些象限？",
      "answer": "一、三、四象限",
      "explanation": "k=2>0 上升，b=-1<0 截距在负半轴，故经过一三四象限。"
    }
  ]
}
```

### 旧字段映射

| 旧字段 | 新字段 |
|--------|--------|
| `explanation` | `solution_summary` + `solution_steps` |
| `knowledge_points: list[str]` | `knowledge_points.core` |
| `key_examination` | `key_examination`（保留） |
| `error_reason` | `error_analysis.reason` |

旧数据（含 `explanation` key）前端做兼容处理，降级显示旧格式。

---

## 后端改动

### 1. `backend/prompts/recognize_question.txt`

替换 `analysis` 对象为：

```
"analysis": {
  "solution_summary": "一句话解题思路，不超过30字",
  "solution_steps": [
    { "step": 1, "title": "步骤标题（5字以内）", "content": "具体推导过程（1-2句）" }
  ],
  "knowledge_points": {
    "core": ["本题直接考查的知识点，1-2个，每个不超过12字"],
    "prerequisite": ["解题前置知识，0-3个，每个不超过12字"],
    "related": ["可延伸的关联知识，0-3个，每个不超过12字"]
  },
  "key_examination": "本题核心考查的能力或概念，1句话",
  "error_analysis": {
    "type": "错误类型（知识缺失/概念混淆/条件遗漏/计算错误/解题方法错误之一）",
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

注意：
- is_question=false 时 analysis 整体为 null
- 图片模糊无法分析时 analysis 整体为 null
- solution_steps 至少 1 步，不超过 5 步
- practice_questions 生成 1 道同类练习题
- knowledge_points 各数组可为空数组 []，但不能省略 key
- error_analysis.type 必须是以下之一：知识缺失、概念混淆、条件遗漏、计算错误、解题方法错误
```

### 2. `backend/schemas/recognition.py`

```python
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
```

`QuestionCandidateOut.analysis: AnalysisOut | None = None` 保持不变。

### 3. `backend/services/recognition_service.py`

更新 MOCK_RESPONSES["clear"] 中的 analysis 为新结构。

更新 `recognize()` 中的 analysis 验证逻辑：旧的 required key 检查（`explanation` 等）替换为新的必填字段检查（`solution_summary`, `solution_steps`, `knowledge_points`, `key_examination`, `error_analysis`）。

### 4. 测试文件

- `backend/tests/test_analysis_schema.py` — 更新 schema 测试
- `backend/tests/test_recognition_analysis.py` — 更新 mock analysis 断言

---

## 前端改动

### 1. `frontend/src/types/index.ts`

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
  // 新格式
  solution_summary?: string
  solution_steps?: SolutionStep[]
  knowledge_points?: KnowledgePoints | string[]  // 兼容旧格式（list[str]）
  key_examination?: string
  error_analysis?: ErrorAnalysis
  common_mistakes?: string[]
  practice_questions?: PracticeQuestion[]
  // 旧格式兼容字段
  explanation?: string
  error_reason?: string
}
```

### 2. `frontend/src/pages/QuestionDetailPage.vue` — AI 解析卡片

替换现有卡片为分层结构（`v-if="question.analysis"`）：

```
💡 AI 解析
├── 解题思路（solution_summary）
│     灰底 bg-gray-50 rounded-lg p-3，text-gray-700
│     旧格式降级：显示 explanation
│
├── 分步解析（solution_steps）
│     标题：text-xs text-gray-400 mb-2
│     每步：序号圆圈（bg-primary-100 text-primary-600）+ 标题粗体 + 内容
│
├── 知识点（knowledge_points）
│     新格式：
│       核心 → bg-blue-50 text-blue-600
│       前置 → bg-gray-100 text-gray-500（前置: 前缀）
│       关联 → bg-green-50 text-green-600（关联: 前缀）
│     旧格式（list[str]）降级：全部蓝色 chip
│
├── 考查要点（key_examination）— text-amber-700
│
├── 错因分析（error_analysis）
│     错误类型：红色 badge（bg-red-50 text-red-600）
│     原因：text-red-600 text-sm
│     改进建议：绿色列表（✓ 每条，text-green-700 text-sm）
│     旧格式降级：显示 error_reason
│
├── 常见错误（common_mistakes）
│     黄色提示条 bg-yellow-50 border-l-2 border-yellow-400
│     每条前加 ⚠️
│
└── 举一反三（practice_questions）
      标题：📝 举一反三
      每道题：
        题目内容（灰底）
        "查看答案" 按钮 → 点击展开答案+解析
        答案（绿色）+ 解析（灰色）
```

### 3. `frontend/src/api/mock/questions.mock.ts`

将 q-1 的 mock analysis 替换为新格式。

---

## 文件变更清单

| 操作 | 文件 |
|------|------|
| 修改 | `backend/prompts/recognize_question.txt` |
| 修改 | `backend/schemas/recognition.py` |
| 修改 | `backend/services/recognition_service.py` |
| 修改 | `backend/tests/test_analysis_schema.py` |
| 修改 | `backend/tests/test_recognition_analysis.py` |
| 修改 | `frontend/src/types/index.ts` |
| 修改 | `frontend/src/api/mock/questions.mock.ts` |
| 修改 | `frontend/src/pages/QuestionDetailPage.vue` |
