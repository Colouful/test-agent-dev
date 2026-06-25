# Claude Code Harness — 架构设计与操作手册

> 项目：错题本（Wrong Book）
> 版本：v1.0（Lab 10-13 完整体系）
> 最后更新：2026-06-25

---

## 1. 系统定位

### 1.1 一句话定义

**Harness = 一套工程骨架，让 Claude Code 从"裸 agent"变成有纪律、有记忆、能自愈的工程伙伴。**

### 1.2 解决的核心问题

| 问题 | 没有 Harness 时 | 有 Harness 后 |
|------|----------------|---------------|
| Agent 违反架构规则 | 你口头提醒，它偶尔忘记 | Hook 机械拦截，0 次绕过 |
| 测试日志淹没上下文 | 主对话被几百行日志稀释 | 子代理隔离执行，只返回结构化摘要 |
| 跨会话状态丢失 | 每次从头理解项目 | Exit-contract + 记忆注入，秒级恢复上下文 |
| AI 输出不可信 | "它说修好了"但你不确定 | 三层断言验证，机器判定对错 |
| 反复犯同样的错 | 纠正 N 次还犯 | 自动捕获→蒸馏→提案规则→不再重犯 |
| 手动修 bug 耗时 | 简单 bug 也要你盯着 | Worker Loop 无人值守修，修好或叫人 |

### 1.3 设计原则

1. **硬约束沉为 Hook，软规则放 CLAUDE.md** — 能绕过的规则 = 没有规则
2. **信任阶梯递进** — 约束 → 记忆 → 验证 → 自动化，每层是下层前提
3. **人类 Gate 守不可逆** — 可逆操作自动，不可逆操作必须确认
4. **验证独立于实现** — 测试和代码来自不同"认知"，防止同义反复
5. **熔断宁紧勿松** — 5 轮改不好的 bug，10 轮大概率也改不好

---

## 2. 架构总览

### 2.1 四层架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        Layer 4: 自动化层                         │
│                     loop/worker-loop.sh                          │
│         (无人值守修复 + 熔断 + STATE.md + 2-Strike)              │
├─────────────────────────────────────────────────────────────────┤
│                        Layer 3: 验证层                           │
│                       ci/verify.sh                               │
│         (结构断言 → 契约断言 → 统计断言，快速失败)               │
├─────────────────────────────────────────────────────────────────┤
│                        Layer 2: 记忆层                           │
│        capture → distill → evolve → retrieve                    │
│     (日志积累 → 蒸馏教训 → 提案规则 → 注入上下文)              │
├─────────────────────────────────────────────────────────────────┤
│                        Layer 1: 约束层                           │
│           Hook + SubAgent + Human Gate + Exit-Contract           │
│      (自动拦截 + 委派隔离 + 人类把关 + 状态交接)                │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 数据流

```
用户编辑 .py ─────→ PostToolUse Hook ─────→ arch-check.sh
                          │                       │
                          │ 违规                  │ 通过
                          ▼                       ▼
                    错误回灌 agent            静默通过
                    agent 自动修正

用户说"跑测试" ──→ 委派 test-runner ──→ 隔离上下文执行
                                              │
                                              ▼
                                      结构化报告回主对话

用户发送消息 ────→ UserPromptSubmit ──→ capture-correction.sh
                                              │
                                              │ 匹配纠正信号词?
                                              ▼
                                     memory/corrections.md

会话结束 ────────→ Stop Hook ─────────→ capture-session.sh
                                              │
                                              ▼
                                     memory/daily/YYYY-MM-DD.md

新会话启动 ──────→ SessionStart Hook ──→ inject-memory.sh
                                              │
                                              ▼
                              MEMORY.md + corrections + exit-contract
                              注入为会话上下文

发现 bug ────────→ worker-loop.sh ────→ claude -p (headless)
                        │                     │
                        │                     ▼
                        │              ci/verify.sh
                        │                     │
                        │     ┌───────────────┼───────────────┐
                        │     ▼               ▼               ▼
                        │  通过→exit 0    失败→回灌       熔断→exit 1
                        │                 下一轮            叫人
                        └─────────────────────────────────────┘
```

---

## 3. 组件详解

### 3.1 Layer 1 — 约束层

#### 3.1.1 PostToolUse Hook（编辑后自动检查）

| 属性 | 值 |
|------|-----|
| 文件 | `hooks/post-edit-check.sh` |
| 触发 | 每次 Claude Code 使用 Edit 工具 |
| 逻辑 | 如果编辑的是 .py 文件 → 跑 ci/arch-check.sh |
| 违规 | exit 1 + 错误输出回灌 agent → 自动修正 |
| 通过 | exit 0，静默 |

**为什么是 Hook 不是 Rules**：SwarmAI 25 天实测，文字规则被跳过 6 次，Hook 0 次绕过。

#### 3.1.2 Test-Runner 子代理

| 属性 | 值 |
|------|-----|
| 文件 | `.claude/agents/test-runner.md` |
| 权限 | Bash, Read, Grep（最小化） |
| 禁止 | Edit, Write（绝不改代码） |
| 价值 | 上下文隔离 — 测试日志不污染主对话 |

**何时该拆子代理**：上下文会被大量输出淹没时。何时不该：简单操作不值得 handoff 开销。

#### 3.1.3 Human Gate

| 操作 | 是否自动 | 理由 |
|------|---------|------|
| git add / commit | 自动 | 本地可逆 |
| 创建/编辑文件 | 自动 | 本地可逆 |
| 运行测试 | 自动 | 只读操作 |
| git push | 需确认 | 不可逆（别人可见） |
| 删除文件 | 需确认 | 可能丢数据 |
| aws 写入 | 需确认 | 影响生产 |

**判断标准**：后果的可逆性，不是操作的复杂度。

#### 3.1.4 Exit-Contract

| 属性 | 值 |
|------|-----|
| 模板 | `memory/exit-contract.template.md` |
| 实例 | `memory/exit-contract.md`（每次交接更新） |
| 五栏 | 完成了什么 / 进行中 / 已失败方案 / 决策理由 / 下一步 |

**最重要的一栏**："已尝试但失败的方案" — 防止下次会话重复犯错。

---

### 3.2 Layer 2 — 记忆层

#### 3.2.1 记忆飞轮总览

```
         ┌────────────────────────────────────────┐
         │            正常使用 Claude Code          │
         └──────────┬───────────────┬─────────────┘
                    │               │
         ┌──────────▼──┐    ┌──────▼───────────┐
         │ Stop Hook   │    │ UserPromptSubmit  │
         │ capture-    │    │ capture-          │
         │ session.sh  │    │ correction.sh     │
         └──────┬──────┘    └──────┬────────────┘
                │                  │
                ▼                  ▼
     memory/daily/*.md      memory/corrections.md
                │                  │
                │  (积压>=3)       │  (同类>=3)
                ▼                  ▼
        /distill-memory       /evolve-memory
                │                  │
                ▼                  ▼
        memory/MEMORY.md     rules/proposed.md
                │                  │
                │                  │ 人类审批
                │                  ▼
                │           rules/personal.md
                │                  │
                └──────────────────┘
                         │
                         ▼
              SessionStart → inject-memory.sh
              (全量注入到新会话)
```

#### 3.2.2 各组件职责

| 组件 | 位置 | 触发方式 | 调 LLM? | 输出 |
|------|------|---------|---------|------|
| capture-session | `.claude/hooks/` | Stop（会话结束） | 否 | daily/日期.md |
| capture-correction | `.claude/hooks/` | UserPromptSubmit | 否 | corrections.md |
| inject-memory | `.claude/hooks/` | SessionStart | 否 | stdout→上下文 |
| distill-memory | `skills/` | 手动 /distill-memory | 是 | MEMORY.md |
| evolve-memory | `skills/` | 手动 /evolve-memory | 是 | proposed.md |
| memory-health | `skills/` | 手动 /memory-health | 否 | 五维报告 |

#### 3.2.3 关键设计决策

| 决策 | 选择 | 理由 |
|------|------|------|
| Capture 调 LLM? | 否 | Hook 必须快（<1s），LLM 判断放 skill |
| Retrieve 用 RAG? | 否，全量注入 | <10K token 装得下，全量比检索可靠 |
| Evolve 自动写规则? | 否，只写 proposed.md | 执行者不是立法者，人审才转正 |
| 频率门控阈值 | >=3 次 | 一次性观察不升级，防幻觉 |
| 遗忘策略 | 60 天无引用→dormant | 达尔文式衰减，不删只降权 |

---

### 3.3 Layer 3 — 验证层

#### 3.3.1 三层断言金字塔

```
        ╱╲
       ╱  ╲        L3: 统计断言（低频，可能真调 AI）
      ╱    ╲       - 分布合理性、波动容忍
     ╱──────╲      - 不放进 loop 主终点线
    ╱        ╲
   ╱   L2:    ╲    L2: 契约断言（每次跑，mock）
  ╱  契约断言   ╲   - R2: confidence 缺失→0.0
 ╱              ╲  - R4: 低置信度→pending_review
╱────────────────╲
╱    L1: 结构断言  ╲  L1: 结构断言（每次跑，mock）
╱                    ╲ - 字段存在性、类型正确
╱════════════════════╲ - status 在合法值集合内
```

#### 3.3.2 verify.sh 设计

| 属性 | 值 |
|------|-----|
| 文件 | `ci/verify.sh` |
| 退出码 | 0=通过, 1=断言失败, 2=环境错误 |
| 快速失败 | L1 挂了不跑 L2，L2 挂了不跑 L3 |
| 调真实 AI? | 否（全 mock，秒级，确定性） |
| 用途 | Loop 的停止条件 + 日常一键验证 |

#### 3.3.3 为什么统计断言不放进 Loop

1. **经济学**：Loop 每轮都跑验证，真调 AI = 双倍烧钱
2. **确定性**：统计断言有波动，做停止条件会导致 Loop 误判

---

### 3.4 Layer 4 — 自动化层

#### 3.4.1 Worker Loop 状态机

```
         ┌──────────┐
         │  START   │
         └────┬─────┘
              │ 清空 STATE.md + 环境检查
              ▼
    ┌─────────────────────┐
    │  第 i 轮            │◄──────────────────┐
    │  检查时间上限       │                    │
    └────┬────────────────┘                    │
         │                                     │
         ▼                                     │
    构建 CONTEXT                               │
    (TASK + STATE.md历史 + 2-Strike升级?)      │
         │                                     │
         ▼                                     │
    claude -p "$CONTEXT"                       │
         │                                     │
         ▼                                     │
    ci/verify.sh                               │
         │                                     │
    ┌────┴────┐                                │
    │ 通过?   │                                │
    └────┬────┘                                │
    Yes  │  No                                 │
    │    │                                     │
    │    ▼                                     │
    │  记录到 STATE.md                         │
    │  Strike 计算                             │
    │    │                                     │
    │    ├─ 3-Strike? ──→ EXIT code=1（叫人）  │
    │    │                                     │
    │    └─ 继续 ──────────────────────────────┘
    │
    ▼
  EXIT code=0（修好了）
```

#### 3.4.2 熔断三件套

| 熔断条件 | 默认值 | 退出码 | 含义 |
|---------|--------|--------|------|
| MAX_ITER | 5 轮 | 1 | 蛮力用尽，换人 |
| MAX_SECONDS | 300s | 2 | 时间到了，别耗了 |
| CONSEC_FAIL_LIMIT | 3 次同类 | 1 | 模型错了，人来理解 |

#### 3.4.3 2-Strike 策略升级

```
第 1 轮失败：正常回灌错误，下一轮重试
第 2 轮同层失败：追加"请先分析 root cause，提出不同思路"
第 3 轮仍然同层：熔断叫人 — 超出 agent 能力
```

**设计思想**：SwarmAI 3 连挂事故启示 — 同一策略第 3 次成功的概率几乎为零。

#### 3.4.4 STATE.md 格式

```markdown
## 第 1 轮 (14:32:07)
**尝试方向：** 修改 confidence 阈值判断逻辑...
**结果：** 失败
**错误摘要：** VERIFY_FAIL: R4 违反: blurry scenario status=high_confidence
---

## 第 2 轮 (14:33:45)
**尝试方向：** 重构 recognize() 返回值处理...
**结果：** 通过 ✓
---
```

---

## 4. 文件结构总览

```
/workshop/ypjh/
│
├── .claude/
│   ├── settings.json                 # 全局 hooks 注册（4 个事件）
│   ├── settings.local.json           # AWS 权限（allow/deny）
│   ├── agents/
│   │   └── test-runner.md            # 测试子代理
│   └── hooks/
│       ├── capture-session.sh        # Stop: 记 git 痕迹
│       ├── capture-correction.sh     # UserPromptSubmit: 捕获纠正
│       └── inject-memory.sh          # SessionStart: 注入+提醒
│
├── hooks/
│   ├── post-edit-check.sh            # PostToolUse(Edit): 架构检查
│   └── session-start.sh              # SessionStart: 基础注入
│
├── rules/
│   ├── personal.md                   # R1-R9 + 人类 Gate
│   ├── severity-guide.md             # 规则分级标准
│   ├── architecture.md               # 架构约束
│   └── proposed.md                   # 规则提案（evolve 产出）
│
├── memory/
│   ├── exit-contract.template.md     # 交接模板
│   ├── exit-contract.md              # 当前交接状态
│   ├── progress.md                   # 进度记忆
│   ├── MEMORY.md                     # 蒸馏后持久记忆
│   ├── corrections.md                # 纠正信号
│   ├── archive.md                    # 衰减归档
│   └── daily/                        # 原始会话日志
│       └── YYYY-MM-DD.md
│
├── skills/
│   ├── add-endpoint/SKILL.md         # 添加 API 端点
│   ├── distill-memory/SKILL.md       # 日志蒸馏
│   ├── evolve-memory/SKILL.md        # 纠正进化
│   └── memory-health/SKILL.md        # 健康报告
│
├── ci/
│   ├── verify.sh                     # 三层验证（loop 终点线）
│   └── arch-check.sh                 # 架构 Fitness Function
│
├── loop/
│   ├── worker-loop.sh                # Worker Loop（熔断+记忆+Strike）
│   └── STATE.md                      # 排错轨迹（运行时生成）
│
├── spec/recognize/
│   ├── requirements.md               # REQ-1~REQ-11
│   └── design.md                     # 详细设计
│
└── backend/
    ├── services/recognition_service.py  # 识别功能实现
    └── tests/test_recognition_service.py
```

---

## 5. 日常使用指南

### 5.1 每天的工作流

```bash
# 1. 启动 Claude Code（自动注入记忆）
claude
# → inject-memory.sh 加载 MEMORY + corrections + exit-contract

# 2. 正常写代码（Hook 自动护航）
# → 编辑 .py 后自动架构检查

# 3. 需要跑测试时
> 用 test-runner 跑一下测试
# → 子代理隔离执行，返回结构化报告

# 4. 一键验证
> 运行 ci/verify.sh
# → 三层断言，秒级反馈

# 5. 有 bug 要修？
bash loop/worker-loop.sh
# → agent 自己修，修好或叫你

# 6. 看到蒸馏提醒时
> /distill-memory
# → 日志炼成教训

# 7. 看到进化提醒时
> /evolve-memory
# → 纠正提案为规则（你审批）

# 8. 复杂任务中途要走
> 交接
# → 自动写 exit-contract，下次无缝恢复
```

### 5.2 常用命令速查

| 场景 | 命令 |
|------|------|
| 验证代码正确性 | `bash ci/verify.sh` |
| 架构合规检查 | `bash ci/arch-check.sh` |
| 自动修 bug | `bash loop/worker-loop.sh` |
| 快速修（少轮数） | `MAX_ITER=3 bash loop/worker-loop.sh` |
| 查看排错轨迹 | `cat loop/STATE.md` |
| 记忆健康检查 | `/memory-health` |
| 蒸馏日志 | `/distill-memory` |
| 进化纠正 | `/evolve-memory` |
| 跑全部测试 | `python3 -m pytest backend/tests/ -v` |

### 5.3 环境变量覆盖

```bash
# Worker Loop 自定义
MAX_ITER=10 bash loop/worker-loop.sh        # 更多轮数
MAX_SECONDS=600 bash loop/worker-loop.sh    # 更长时间
TASK="修复 X 问题" bash loop/worker-loop.sh  # 自定义任务
VERIFY_CMD="bash ci/arch-check.sh" bash loop/worker-loop.sh  # 自定义验证
```

---

## 6. 安全与治理

### 6.1 AWS 操作权限矩阵

| 操作 | 权限 | 配置位置 |
|------|------|---------|
| dynamodb describe/query/scan/get | Allow | settings.local.json |
| s3 ls / s3 cp | Allow | settings.local.json |
| bedrock invoke-model | Allow | settings.local.json |
| dynamodb delete-table/delete-item | **Deny** | settings.local.json |
| dynamodb put-item/update-item | **Deny** | settings.local.json |
| s3 rm / s3 rb / s3 sync | **Deny** | settings.local.json |

### 6.2 规则分级

| 级别 | 含义 | 违反后果 | 载体 |
|------|------|---------|------|
| MUST | 绝对不可违反 | 数据损坏/安全漏洞 | Hook + Rules |
| SHOULD | 强烈建议遵守 | 技术债/体验差 | Rules |
| CAN | 建议但可跳过 | 无直接后果 | CLAUDE.md |

### 6.3 升级路径：规则从哪来

```
观察到 agent 犯错
    │
    ▼
纠正它（口头/文字）──→ capture-correction.sh 自动捕获
    │
    │ 同类 >=3 次
    ▼
evolve-memory 提案 ──→ rules/proposed.md
    │
    │ 人工审批
    ▼
rules/personal.md（L1 文字规则）
    │
    │ 仍然被违反
    ▼
hooks/（L2 机械拦截）
    │
    │ 跨项目反复出现
    ▼
结构性不可能（L3 代码/架构层面消除）
```

---

## 7. 扩展路径

### 7.1 Loop 成熟度模型

| 等级 | 触发方式 | 交付方式 | 人的角色 |
|------|---------|---------|---------|
| L1（当前） | 人手动跑 | 人 review 改动 | 发起者 + 审核者 |
| L2 | CI/webhook 自动触发 | 自动提 PR | 审核者 |
| L3 | 监控告警自动触发 | 自动修+自动部署 | 事后审计 |

### 7.2 记忆系统扩展

| 阶段 | 策略 | 适用场景 |
|------|------|---------|
| <10K token | 全量注入（当前） | 个人项目 |
| 10-30K | 分文件 + 选择性注入 | 中型项目 |
| 30-50K | dormant 衰减 + 归档 | 长期项目 |
| >50K | 向量库 RAG | 团队级/企业级 |

### 7.3 从错题本到通用模板

这套 Harness 可复用到任何项目，只需替换：

| 组件 | 错题本版本 | 替换为 |
|------|-----------|--------|
| verify.sh | 识别功能三层断言 | 你项目的核心验证逻辑 |
| arch-check.sh | Python 架构约束 | 你项目的架构规则 |
| TASK 变量 | "修复识别功能" | 你的修复目标 |
| rules/personal.md | R1-R9 | 你项目的业务规则 |

---

## 8. 问题排查

### 8.1 常见问题

| 症状 | 原因 | 解决 |
|------|------|------|
| Hook 不触发 | settings.json 路径错误 | 检查绝对路径、matcher 配置 |
| inject-memory 无输出 | MEMORY.md 等文件不存在 | 先跑一次 capture 或手动创建 |
| verify.sh 报 import error | 缺少 pydantic 依赖 | `pip install pydantic` |
| Loop 第 1 轮就超时 | claude -p 网络慢 | 调大 MAX_SECONDS 或检查网络 |
| 2-Strike 不触发 | extract_fail_stage 提取为空 | 确保 verify.sh 输出含"第 N 层" |
| capture-correction 不工作 | jq 未安装 | 改用 grep/python 降级提取 |
| Loop exit 3 | verify.sh 不可执行 | `chmod +x ci/verify.sh` |

### 8.2 诊断命令

```bash
# 检查所有 hooks 是否可执行
find .claude/hooks/ hooks/ -name "*.sh" -exec ls -la {} \;

# 检查 settings.json 格式
python3 -c "import json; json.load(open('.claude/settings.json'))" && echo "JSON OK"

# 验证全套 CI
bash ci/verify.sh && bash ci/arch-check.sh && echo "ALL GREEN"

# Loop 空跑（验证脚本语法）
bash -n loop/worker-loop.sh && echo "语法 OK"

# 记忆系统状态
echo "Daily logs: $(ls memory/daily/ 2>/dev/null | wc -l)"
echo "Corrections: $(wc -l < memory/corrections.md 2>/dev/null || echo 0)"
echo "MEMORY size: $(wc -c < memory/MEMORY.md 2>/dev/null || echo 0) bytes"
```

---

## 9. 关键约束清单

| ID | 级别 | 规则 | 载体 |
|----|------|------|------|
| R1 | MUST | 所有查询必须带 user_id 过滤 | rules + verify.sh |
| R2 | MUST | Bedrock 返回必须 schema 校验，confidence 缺失→0.0 | verify.sh L2 |
| R3 | MUST | 题目必须结构化存储，禁止裸字符串入库 | arch-check.sh |
| R4 | MUST | confidence < 0.7 → status=pending_review | verify.sh L2 |
| R9 | SHOULD | content/answer 为空→占位符，不报 error | verify.sh L1 |
| HG1 | MUST | git push 必须人类确认 | rules |
| HG2 | MUST | aws 写入必须人类确认 | settings.local.json deny |

---

## 10. 总结

### 这套系统的本质

```
传统开发：人写代码 → 人跑测试 → 人修 bug → 人 review

有 Harness：
  人写代码 → Hook 自动护航
  人跑测试 → 子代理隔离执行
  人修 bug → Loop 自动修（简单的）+ 叫人（复杂的）
  人 review → verify.sh 先过一遍（机器审）+ 人最终审

人的角色从"执行者"变成"决策者"：
  - 决定规则（proposed.md → personal.md）
  - 决定信任（review Loop 的产出）
  - 决定升级（文字规则 → Hook → 结构性不可能）
```

### 一句话课后心得

> 你不是在教 AI 怎么写代码——你在建一套治理系统，让 AI 在安全边界内自主工作，而你只在关键时刻介入。
