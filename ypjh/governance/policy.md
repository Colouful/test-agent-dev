# 治理策略（Governance Policy）

## 成本账户划分

错题本的 AI 成本分两个账户独立追踪：

### 账户 A — 开发 Token 消耗（Dev Token Burn）

**定义**：Claude Code agent 在开发过程中消耗的 token（代码生成、规则讨论、测试迭代）

| 阶段 | 预估消耗 | 说明 |
|------|---------|------|
| M3-M5（规则+权限） | ~50k tokens | 规则文件、settings.json 迭代 |
| M7-M8（架构+设计） | ~80k tokens | 架构文档、需求文档 |
| M9（实现+测试） | ~120k tokens | service 实现、10 个测试调试 |
| M10-M13（harness） | ~100k tokens | hooks、loop、memory 搭建 |
| **合计（Day1-2）** | **~350k tokens** | |

**控制手段**：
- 记忆 Pipeline（session-start.sh）减少重复上下文重建
- Rules 渐进式披露（CLAUDE.md 只加载必要规则文件）
- Worker Loop 熔断防止无限循环消耗

---

### 账户 B — 每次上传 Bedrock 成本（Per-Upload Bedrock Cost）

**定义**：用户每次上传错题图片时调用 Bedrock 视觉模型的 API 成本

| 模型 | 单次调用成本（估算） | 月活 100 用户 × 日均 5 题 |
|------|-----------------|----------------------|
| Claude 3 Haiku（视觉） | ~$0.002 / 图 | ~$30/月 |
| Claude 3 Sonnet（视觉） | ~$0.010 / 图 | ~$150/月 |

**当前选择**：开发阶段用 Mock（$0），Day3 接入时选 Haiku 控制成本。

**控制手段**：
- R4：低置信度不重复识别，等用户确认后再入库（避免反复调用）
- S3 缓存：同一图片 hash 命中缓存，不重复调用 Bedrock
- 限流：单用户每日上限 50 张（防止滥用）

---

## 权限边界（Permission Boundary）

参见 `.claude/settings.local.json`：

| 操作 | 策略 | 原因 |
|------|------|------|
| `dynamodb:Query/Scan/GetItem` | ALLOW | 读操作，只读不写 |
| `dynamodb:PutItem/UpdateItem` | DENY | 必须经过 API，不允许 agent 直写 |
| `dynamodb:DeleteTable/DeleteItem` | DENY | 不可逆，绝对禁止 |
| `s3:cp`（上传） | ALLOW | 图片上传必要 |
| `s3:rm`（删除） | DENY | 不可逆 |
| `bedrock-runtime:invoke-model` | ALLOW | 识别功能核心 |

---

## 不可逆操作的人类 Gate

在执行以下操作前，必须运行 `bash hooks/human-gate.sh "<操作描述>"` 获得确认：

1. `git push`（推送到远端）
2. AWS 数据写入（即使权限允许）
3. 删除任何 memory/ 或 loop/STATE.md 文件
4. 修改 .claude/settings.local.json 的 deny 列表

---

## 合规检查清单（发布前）

- [ ] `bash ci/arch-check.sh` → ARCH_OK
- [ ] `bash ci/verify.sh` → VERIFY_OK
- [ ] `python3 ddd/score_health.py` → 健康分 ≥ 80
- [ ] `bash loop/worker-loop.sh` → LOOP_OK（第 1 轮通过）
- [ ] R1 隔离：所有 Repository 查询函数含 user_id 参数
- [ ] R2/R4：test_recognition_service.py 全绿（10 个测试）
