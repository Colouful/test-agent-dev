# 项目进度记忆

## 当前状态（Lab M12 完成）

### 完成的 Lab

- [x] Lab M3 — 规则分级标准 + 5 条个人规则（R1-R8）
- [x] Lab M4 — `add-endpoint` Skill 封装
- [x] Lab M5 — AWS 权限配置 + `check_question_schema` 工具
- [x] Lab M7 — 架构评审 + `arch-check.sh` Fitness Function
- [x] Lab M8 — EARS 需求 + 识别功能详细设计
- [x] Lab M9 — 识别功能实现 + Rule Reflection（+R9）+ 10 个测试全绿
- [x] Lab M10 — 编排 hook + test-runner subagent + memory 初始化
- [x] Lab M11 — 记忆 Pipeline（PostCompact hook）+ DDD 健康体检（score_health.py，当前得分 100/100）
- [x] Lab M12 — 识别功能验证体系（ci/verify.sh，三层断言全绿：结构 ✓ 契约 ✓ 统计 ✓）

### 待完成

- [x] Lab M13 — Worker Loop（含三道熔断：迭代上限/时间/连续失败，第 1 轮通过）
- [x] Lab M14 — 自愈设计（self-healing-design.md，三层L1/L2/L3）+ 成本治理（policy.md，双账户）
- [x] Lab M16 — Capstone：README + 全套校验全绿（arch ✓ verify ✓ ddd 100/100 ✓ 10 tests ✓）

## 关键决策记录

| 决策 | 选择 | 理由 |
|------|------|------|
| 低置信度策略 | 展示给用户确认，不直接入库 | 数据准确 > 操作便捷 |
| 内容字段缺失 | 用占位符降级（R9） | 引导填写 > 报错 |
| 测试策略 | 验结构/契约，不验具体文字 | AI 输出非确定性 |
| DB 切换 | SQLite(dev) / DynamoDB(prod) | Repository 抽象隔离 |

## 已尝试但失败的方案

| 方案 | 问题 | 改为 |
|------|------|------|
| `empty` mock 不填 content/answer | schema min_length=1 报错，test_r2 失败 | service 层用占位符降级（R9） |
