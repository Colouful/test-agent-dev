# 识别功能详细设计

## 模块划分

```
POST /api/v1/questions/recognize
        │
        ▼
RecognizeRouter（路由层）
  - 接收 multipart/form-data
  - 调用 RecognitionService
  - 返回 RecognitionResultOut
        │
        ▼
RecognitionService（业务层）
  ├── upload_to_s3(image_bytes) → image_key
  ├── call_bedrock(image_key) → raw_dict
  ├── check_question_schema(raw_dict) → QuestionCandidate   ← 必经校验
  └── decide_status(candidate) → RecognitionResult
        │
        ▼
QuestionService.create_from_candidate(candidate, user_id)
  └── QuestionRepository.insert(question)
```

## 接口定义

### 请求

```
POST /api/v1/questions/recognize
Content-Type: multipart/form-data
Authorization: Bearer <token>

image: <binary>
```

### 响应 Schema

```python
class RecognitionResultOut(BaseModel):
    status: Literal["high_confidence", "pending_review", "error"]
    candidate: QuestionCandidateOut | None   # status=error 时为 None
    error_hint: str | None                  # 用户可读的错误提示

class QuestionCandidateOut(BaseModel):
    content: str
    correct_answer: str
    wrong_answer: str | None
    confidence: float
    subject: str | None
    question_type: str | None
    image_key: str
```

## 控制流图

```
上传图片
    │
    ▼
upload_to_s3()
    ├─ S3 上传失败/超时 ──→ status=error, error_hint="图片上传失败，请重试"
    │                        （不继续调 Bedrock，避免无图片 key 入库）
    ▼
call_bedrock(image_key)
    ├─ 网络/超时错误 ──→ status=error, error_hint="识别服务暂时不可用"
    │
    ▼
raw_dict["confidence"] 存在？
    ├─ 否 ──→ raw_dict["confidence"] = 0.0  （R2）
    │
raw_dict["content"] / ["correct_answer"] 为空？
    ├─ 是 ──→ 填充占位符 "（识别内容为空）"（R9），confidence 已为 0.0
    │
    ▼
check_question_schema(raw_dict)
    ├─ ValidationError ──→ status=error, error_hint="识别结果格式异常"
    │
    ▼
confidence >= 0.7？
    ├─ 是 ──→ status=high_confidence，返回候选供用户确认
    └─ 否 ──→ status=pending_review，提示手动核对（不入库）
```

### HTTP 状态码映射

| RecognitionResult.status | HTTP 状态码 | 说明 |
|---|---|---|
| `high_confidence` | 200 | 正常识别，候选供确认 |
| `pending_review` | 200 | 低置信度，需人工核对（不是错误） |
| `error` | 200 | 识别失败，返回 error_hint（业务错误用 200，不用 5xx） |

## 三个关键设计判断

### 判断 1：手写答案剔除方案

**选择**：语义层 — 让大模型识别并区分题目正文和手写答案。

**理由**：像素级图像分离需要额外 CV 模型，维护成本高；
Bedrock 视觉模型本身能理解语义，直接在 prompt 中要求"仅返回印刷体题目，忽略手写部分"。

**代价**：依赖模型理解准确性，遇到复杂手写可能混入正文；
需要在测试 fixture 中准备含手写的样本图片做回归测试。

### 判断 2：低置信度兜底策略

**选择**：降级让用户确认（不直接入库，不默认值）。

**理由**：错题本的核心价值是数据准确——宁可多问用户一次，
也不能让错误数据悄悄入库影响复习质量。

**代价**：用户需要多一步操作；如果识别准确率不高，用户会频繁看到"待确认"提示，体验下降。

### 判断 3：识别与入库分离（两步操作）

**选择**：识别结果先展示确认，用户点击"确认"后才入库（二步）。

**理由**：识别是非确定性的，用户确认是质量门控；
一步直接入库会导致大量错误数据，后期清理成本极高。

**代价**：用户操作步骤增加（上传 → 查看 → 确认），
在用户体验上略逊于"上传即完成"的设计。

### 判断 4：同步识别 vs. 异步任务队列

**选择**：同步识别（HTTP 请求直接等待 Bedrock 返回）。

**理由**：MVP 阶段用户上传图片后期望立即看到识别结果；
Bedrock 响应通常在 3-8 秒内，低于前端 10 秒超时；
引入异步队列（Celery/SQS）会显著增加基础设施复杂度。

**代价**：高并发时（>50 并发上传）会占满事件循环中的等待槽，
吞吐量受 Bedrock API 限速约束而非服务器并发能力；
如果 Bedrock 响应超过 10 秒，用户会看到超时错误而非"处理中"状态。

**升级条件**：当 Bedrock 响应 P95 > 5s 或用户量 > 500 DAU 时，迁移到异步队列（SQS + Lambda）。

---

## 测试策略

**验结构（必须严格）**：
- 响应必须是合法 JSON
- `status` 字段存在且值为 `high_confidence` / `pending_review` / `error`
- `candidate.confidence` 为 float，范围 [0.0, 1.0]
- `candidate.content` 非空字符串
- `candidate.correct_answer` 非空字符串

**容忍波动（不断言具体文字）**：
- 不断言 `candidate.content == "某固定字符串"`
- 不断言 `candidate.correct_answer == "某固定答案"`
- 识别文字是非确定输出，每次可能不同（REQ-10）

**关键 Fixture 清单**：
- `fixture_clear_question.jpg` — 清晰印刷体题目（预期 confidence >= 0.7）
- `fixture_blurry_question.jpg` — 模糊图片（预期 confidence < 0.7）
- `fixture_handwritten_question.jpg` — 含手写答案的题目
- `fixture_math_formula.jpg` — 含 LaTeX 公式的数学题
- `fixture_multi_question.jpg` — 一图多题（测试列表返回）
- `fixture_empty_response.json` — Bedrock 返回空 JSON（测试 confidence 缺失处理）
