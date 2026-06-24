# Exit Contract — 错题本项目交接说明

> 每次会话结束前更新此文件。下一个会话的 agent 必须先读取此文件再开始工作。

---

## 当前会话完成内容

- 所有 Lab（M3-M16）全部完成
- superpowers 插件已安装
- **全套 harness 文件 diff + 修复完成（生产级水平）**：
  - M3: severity-guide.md（SHOULD/CAN Agent 行为补全）、personal.md（R5-R9 Agent 行为补全，R8/R9 顺序修正）
  - M3: architecture.md（ARCH-2/3 自动检测说明）、CLAUDE.md（architecture.md 加入渐进披露表）
  - M4: skills/add-endpoint/SKILL.md（织入 R2/R3/R4，加判断树，识别接口模板）
  - M5: mcp/README.md（修正措辞，区分 CLI 库 vs MCP server，补升级路径）、settings.local.json（移除无效 drop-table deny，新增 s3 sync deny）
  - M7: ci/arch-check.sh（新增 ARCH-2/3 检测，模式2升为 FAIL，修复 grep -e 问题）
  - M8: spec/recognize/requirements.md（新增 REQ-11 科目层边界）、design.md（补 S3 失败分支、HTTP 状态码映射、判断4同步/队列）
  - M8: recognition_service.py（MOCK_BEDROCK 改环境变量、加 user_id 参数、REQ-11 学科白名单、S3 失败提前返回）
  - ci/verify.sh（同步更新 user_id 参数）、测试文件（同步更新 user_id 参数）

## 下一个会话的入口

**Harness 优化完成，全套 CI 通过（arch ✓ verify ✓ ddd 100/100 ✓ 10 tests ✓）。**

后续方向（已讨论，等待选择）：
1. **开始实际业务代码开发**：全栈并行（FastAPI + Vue 3）
   - 已决定：先 brainstorming 详细设计再动手
   - 已决定：使用 JWT 认证
   - 已决定：按 EARS 需求（REQ-1~REQ-11）实现识别主线功能
2. 接入真实 Bedrock：`MOCK_BEDROCK=false`，接入 boto3
3. SM-2 复习算法：`ease_factor`、`next_review_at` 字段实现
4. 部署到 AWS：Lambda + API Gateway + DynamoDB

---

## 项目当前可运行状态

```bash
# 运行测试
cd /workshop/ypjh
python3 -m pytest backend/tests/test_recognition_service.py -v

# 预期结果：10 tests passed
```

---

## 关键约束（下一个 agent 必须遵守）

| ID | 级别 | 规则 |
|----|------|------|
| R1 | MUST | 所有查询必须带 user_id 过滤 |
| R2 | MUST | Bedrock 返回必须 schema 校验，confidence 缺失→0.0 |
| R3 | MUST | 题目必须结构化存储，禁止裸字符串入库 |
| R4 | MUST | confidence < 0.7 → status=pending_review |
| R9 | SHOULD | content/answer 为空→占位符，不报 error |

**AWS 禁止操作**（绝对不执行）：
- `aws dynamodb delete-table`
- `aws dynamodb delete-item`
- `aws dynamodb put-item`（未经确认）
- `aws s3 rm`

---

## 已尝试但失败的方案

| 方案 | 为什么失败 | 正确做法 |
|------|-----------|---------|
| empty mock 不填 content/answer | schema min_length=1 报 ValidationError，test_r2 status="error" | service 层用占位符降级（已修复，见 R9） |
| confidence 缺失默认 1.0 | 违反 R2，大量垃圾数据入库 | 强制 0.0，触发 pending_review |

---

## 当前文件树（核心）

```
/workshop/ypjh/
├── rules/
│   ├── severity-guide.md     # 规则分级
│   ├── personal.md           # R1-R9
│   ├── 01-项目概述.md
│   ├── 02-编码规范.md
│   └── architecture.md
├── skills/add-endpoint/SKILL.md
├── mcp/check_question_schema.py
├── ci/arch-check.sh          # Fitness Function（三态：OK/FAIL/SKIP）
├── hooks/post-edit-check.sh  # 编辑 .py 后自动跑 arch-check
├── subagents/test-runner.md  # 最小权限测试 runner
├── memory/
│   ├── progress.md           # 进度记录（本文件）
│   └── exit-contract.md      # 交接说明（此文件）
├── spec/recognize/
│   ├── requirements.md       # REQ-1~REQ-10
│   └── design.md
├── docs/architecture.md
└── backend/
    ├── services/recognition_service.py
    └── tests/test_recognition_service.py
```

---

## 未完成的 Labs（优先级排序）

1. **Lab M11** — 记忆 Pipeline（`hooks/session-start.sh`）+ DDD 健康体检
2. **Lab M12** — `ci/verify.sh`：结构断言 + 契约断言 + 统计断言（不调真实 Bedrock）
3. **Lab M13** — `loop/worker-loop.sh`（熔断：最大迭代 + 时间限制 + 人类兜底）
4. **Lab M14** — 部署 + `governance/self-healing-design.md` + 成本治理
5. **Lab M16** — Capstone：整合 harness + README + 互评
