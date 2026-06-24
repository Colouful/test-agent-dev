# 错题本（Wrong Answer Notebook）

帮助学生拍照上传错题、AI 智能识别、结构化存储、间隔复习的全栈 Web 应用。

## 快速开始

```bash
# 后端（开发模式，Mock Bedrock）
cd backend && uv run uvicorn main:app --reload

# 前端
cd frontend && npm run dev

# 运行测试
python3 -m pytest backend/tests/ -v

# 完整验证（三层断言）
bash ci/verify.sh

# DDD 健康体检
python3 ddd/score_health.py
```

## 架构概览

```
用户拍照
    │
    ▼
前端（Vue 3 + TypeScript）
    │  POST /api/v1/recognize
    ▼
FastAPI 路由 → RecognitionService → check_question_schema（MCP 工具）
    │                                      │
    │                              schema 校验 + R2 规则
    ▼
confidence ≥ 0.7 → high_confidence → 前端展示 → 用户确认入库
confidence < 0.7 → pending_review  → 前端展示 → 用户手动核对
    │
    ▼
QuestionRepository（SQLite/DynamoDB）← R1: 必须带 user_id
```

## 核心规则（MUST 级别）

| 规则 | 说明 |
|------|------|
| **R1** | 所有查询必须携带 `user_id`，严格用户隔离（防 BOLA） |
| **R2** | Bedrock 返回先 schema 校验，`confidence` 缺失按 0.0，不得默认 1.0 |
| **R3** | 题目内容必须结构化存储（`Question` 对象），禁止裸字符串入库 |
| **R4** | `confidence < 0.7` → `status=pending_review`，不得直接入库 |

## Harness 结构

```
ypjh/
├── rules/          ← 分级规则（severity-guide + personal R1-R9 + architecture）
├── skills/         ← add-endpoint Skill（封装 7 步接口开发流程）
├── mcp/            ← check_question_schema（Pydantic 校验工具）
├── ci/             ← arch-check.sh（Fitness Function）+ verify.sh（三层断言）
├── hooks/          ← session-start / post-edit-check / post-compact / human-gate
├── subagents/      ← test-runner（最小权限）
├── memory/         ← progress.md + exit-contract.md（跨会话记忆）
├── ddd/            ← score_health.py（架构健康分，当前 100/100）
├── loop/           ← worker-loop.sh（含三道熔断）+ STATE.md
├── governance/     ← self-healing-design.md + policy.md（成本治理）
├── spec/           ← EARS 需求 + 详细设计
└── docs/           ← 架构文档（含人工标注的单双向门）
```

## CI 检查清单

在提交前运行：

```bash
bash ci/arch-check.sh          # ARCH_OK
bash ci/verify.sh               # VERIFY_OK（三层）
python3 ddd/score_health.py     # 健康分 ≥ 80
python3 -m pytest backend/tests/ -v  # 10 tests passed
```

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | FastAPI + SQLAlchemy 2 (async) + PostgreSQL/DynamoDB |
| 前端 | Vue 3 (Composition API) + TypeScript + Pinia |
| AI  | AWS Bedrock（Claude 视觉模型） |
| 存储 | AWS S3（图片）+ DynamoDB（题目数据） |
| 代码质量 | Ruff + mypy / ESLint + Prettier |
| 测试 | pytest + httpx / Vitest + Vue Testing Library |

## 开发阶段

- **Day 1**：规则体系 + Skill 封装 + AWS 权限（M3-M5）
- **Day 2**：架构评审 + 需求设计 + 识别实现 + 测试（M7-M9）
- **Day 3**：Harness 编排 + 验证体系 + Worker Loop + 治理（M10-M16）
