# 自愈设计（Self-Healing Design）

## 概述

错题本应用的自愈能力分三个层次，从最小代价到最大代价依次尝试。

```
异常发生
    │
    ▼
L1 自动降级（< 1s）─── 无需人工 ─── 例：Bedrock 超时 → 返回 pending_review
    │  失败
    ▼
L2 自动重试（< 30s）── 无需人工 ─── 例：503 → 指数退避 × 3 次
    │  失败
    ▼
L3 人类兜底（需介入）── 告警通知 ─── 例：连续失败 → PagerDuty / 邮件
```

---

## L1 — 自动降级规则

| 触发条件 | 降级策略 | 影响 |
|---------|---------|------|
| Bedrock 返回残缺 JSON（无 confidence） | confidence → 0.0，status → pending_review | 用户需手动核对 |
| Bedrock 返回 content/answer 为空 | 填充占位符（R9），status → pending_review | 用户需手动填写 |
| S3 上传超时 | 跳过图片存储，返回 pending_review | 题目无附图 |
| schema 校验失败 | status → error，返回友好错误信息 | 用户重新上传 |

**实现位置**：`backend/services/recognition_service.py`（已实现 L1 全部规则）

---

## L2 — 自动重试规则

```python
# 指数退避重试（未来接入真实 Bedrock 时启用）
MAX_RETRIES = 3
BACKOFF_BASE = 1.5  # 秒

for attempt in range(MAX_RETRIES):
    try:
        result = call_bedrock(image_key)
        break
    except (BotoCoreError, ClientError) as e:
        if attempt == MAX_RETRIES - 1:
            raise
        wait = BACKOFF_BASE ** attempt
        await asyncio.sleep(wait)
```

**触发条件**：AWS SDK 5xx 错误、网络超时、限流（ThrottlingException）

**不重试的错误**：4xx 客户端错误（图片格式不对、权限不足）

---

## L3 — 人类兜底触发条件

| 条件 | 阈值 | 通知方式 |
|------|------|---------|
| Worker Loop 连续失败 | 3 次（`CONSEC_FAIL_LIMIT`） | 终端输出 + `loop/STATE.md` |
| DDD 健康分下降 | < 80 分 | `ddd/score_health.py` 输出 ARCH_WARN |
| 架构护栏失败 | 任意 ARCH_FAIL | `ci/arch-check.sh` 退出码 1 |
| ci/verify.sh 失败 | 任意层断言失败 | 终端输出 + 退出码 1 |

**当前阶段**：人类兜底通过终端输出实现。Day3 接入真实 AWS 后升级为 CloudWatch Alarm。

---

## 架构护栏与自愈的关系

```
代码变更
    │
    ▼
PostToolUse(Edit) Hook
    │
    ▼
arch-check.sh（L1 护栏）
    │  ARCH_FAIL
    ▼
阻止继续（exit 1）← 告知 agent 修复，不让有问题的代码进入循环
```

自愈的前提是"不引入新的架构破坏"。Fitness Function 是自愈的**前置条件**，不是后置处理。
