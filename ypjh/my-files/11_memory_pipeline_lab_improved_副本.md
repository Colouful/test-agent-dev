# Lab 11 改进版 — 给你的 Claude Code 装一条可直接复用的记忆 Pipeline

> **设计原则**：每层产出都是学员课后能直接用的真实系统。参照 SwarmAI 实际架构（`daily_activity_hook` → `distillation_hook` → `evolution_maintenance_hook`），简化为个人版本，但保留工业设计的关键判断。
>
> **时长**：40 分钟
> **工具**：Claude Code（唯一工具）
> **前置**：harness repo 已有 `rules/`、`skills/`、`memory/`（M10 的 progress/exit-contract）
> **产出承诺**：课后你的 Claude Code 每次会话结束自动积累、每次开始自动加载——直接开始"越用越聪明"
>
> **层次设计**：
> - **Layer 1 — 闭环跑通**（12 min）：最小可用记忆系统，当堂验证"下次它记得"
> - **Layer 2 — 蒸馏进化**（16 min）：参照 SwarmAI 的两阶段提炼，把日志变成可复用知识
> - **Layer 3 — 自动化编排**（12 min）：让飞轮无需手动干预持续运转

---

## 设计哲学：从 SwarmAI 学到什么

SwarmAI 的记忆管道（300+ sessions 实战）给了三个关键教训：

1. **Capture 必须分离"记录"和"判断"** — SwarmAI 的 `daily_activity_hook` 用 `SummarizationPipeline` 做结构化提取（topics/decisions/files/corrections），但 **capture 本身不做深度判断**（短对话用纯 regex，长对话才加 LLM enrichment）。给学员的版本：hook 只做轻量捕获，判断留给 skill。

2. **蒸馏需要"频率门控"和"Git 验证"** — SwarmAI 的 `distillation_hook` 有两个精妙机制：
   - 频率门控：同一观察出现 ≥2 次才提升到 MEMORY.md（一次性的留在 daily 里）
   - Git 验证：声称"实现了 X"的条目，要和 git log 交叉验证，未验证的标 `[UNVERIFIED]`
   这两个机制防止记忆被幻觉污染——学员版本保留频率思想（≥3 次纠正才提案规则）。

3. **进化必须"propose-approve"** — SwarmAI 用 `steeringify` 把反复的 corrections 聚类后生成 STEERING.md 规则提案，但**必须人批准才写入**。学员版本的 `evolve-memory` skill 同样只写 `proposed.md`。

---

## Layer 1 — 闭环跑通：Capture + Retrieve (12 min)

### 目标
用两个 hook 让"这次的痕迹，下次能用"跑通。学员在 5 分钟内亲眼验证闭环。

### 课程概念
- Capture 用 hook：快、稳、不调 LLM（Slide 4、5）
- Retrieve 全量注入优先（Slide 8）
- 纠正是最高价值数据（Slide 5，呼应 M9）
- **SwarmAI 对标**：`daily_activity_hook.py` 的 `_capture_git_activity()` + `SummarizationPipeline._extract_files_modified()` 的极简版

### Step 1.1 — Capture：会话结束自动记痕迹 (5 min)

```bash
# 让 Claude Code 帮你创建完整的 capture 机制
claude
> 帮我配置 Claude Code 的 Stop hook（会话结束时触发），实现以下功能：
>
> 1. 创建脚本 .claude/hooks/capture-session.sh：
>    - 记录日期时间
>    - 用 git diff --name-only HEAD~1 2>/dev/null 记录本次改了哪些文件
>    - 用 git log --oneline -3 --no-decorate 2>/dev/null 记录最近的 commit
>    - 把结果追加到 memory/daily/$(date +%Y-%m-%d).md，格式：
>      ## HH:MM | session
>      **改动文件：** file1, file2
>      **Git：** commit messages
>    - 脚本要 set -uo pipefail，出错不阻塞
>
> 2. 创建脚本 .claude/hooks/capture-correction.sh：
>    - 从 stdin 读取 JSON（Claude Code 会传入含 prompt 的 JSON）
>    - 用 jq 提取 .input.content（用户消息文本）
>    - 如果匹配纠正信号词（不对|应该是|错了|别这么|搞反|不是这样|wrong|should be|don't|stop|revert），
>      则追加到 memory/corrections.md，格式：
>      - [YYYY-MM-DD HH:MM] 用户原文（前120字）
>    - 不匹配则静默退出（exit 0，不输出）
>
> 3. 配置 .claude/settings.json 的 hooks：
>    - Stop 事件挂 capture-session.sh
>    - UserPromptSubmit 事件挂 capture-correction.sh
>
> 4. 确保 memory/daily/ 目录存在
> 5. 脚本加可执行权限
```

**SwarmAI 设计对标讲解**（讲师用）：
> SwarmAI 的 `capture-session.sh` 对应的是 `daily_activity_hook.py`。区别：SwarmAI 从 SQLite 读完整对话再做 structured extraction（因为它管理 Claude CLI 子进程，能拿到全部消息）；学员的版本直接从 git 拿地面真相，更简单但同样有效。SwarmAI 的 `capture-correction.sh` 对应的是 `extraction_patterns.py` 中的 `CORRECTION_PATTERNS`——那个正则有 50+ 行，覆盖英文/中文/结构性重定向。学员版用 6 个信号词足够起步，课后可以逐步扩充。

### Step 1.2 — Retrieve：带着记忆醒来 (4 min)

```bash
> 继续帮我配置 SessionStart hook：
>
> 1. 创建 .claude/hooks/inject-memory.sh：
>    - 如果 memory/MEMORY.md 存在，cat 输出它的内容
>    - 如果 rules/personal.md 存在，cat 输出它的内容
>    - 如果 memory/corrections.md 存在且非空，输出"## 近期纠正（待进化）"后跟最近 10 条
>    - 脚本 stdout 的内容会被 Claude Code 注入为会话上下文
>
> 2. 把它挂到 .claude/settings.json 的 hooks.SessionStart
```

**关键认知（讲师讲解）**：
> 这一步的设计和 SwarmAI 的 `SessionStart` context injection 同源（`core/prompt_builder.py` 的全量注入）。SwarmAI 注入的是 11 个文件（~100K token budget）；学员版注入 MEMORY + rules + corrections（<10K token）——小到装得下，全量注入比 RAG 更可靠。
>
> 为什么注入 corrections？SwarmAI 的 `_ENRICHMENT_PROMPT` 明确要求 LLM 检测"user corrected agent behavior"并记录——corrections 是飞轮最快反馈的燃料。如果 agent 看到"我上次被纠正了什么"，它这次就会主动避免。

### Step 1.3 — 验证闭环 (3 min)

```bash
# 测试纠正捕获
> 不对，这个函数应该返回 Promise 不是直接返回值

# 验证
> 读一下 memory/corrections.md，是否捕获了刚才的纠正？

# 退出触发 Stop hook
/exit

# 重新进入，验证 retrieve
claude
> 你启动时加载了哪些记忆？告诉我上次我纠正过你什么
```

### 预期输出
- `memory/daily/<date>.md` 出现会话痕迹（改动文件 + git commits）
- `memory/corrections.md` 捕获了纠正信号
- 新会话 agent 能说出"你上次纠正了我 Promise vs 直接返回值的问题"

### Done 标准
- [ ] Stop hook 写入 daily 日志（含 git 地面真相）
- [ ] 纠正信号被自动捕获到 corrections.md
- [ ] 新会话启动时 MEMORY + corrections 被注入
- [ ] agent 能复述上次的纠正（闭环验证）
- [ ] 全程零 LLM、无明显延迟

---

## Layer 2 — 蒸馏进化：Distill + Evolve (16 min)

### 目标
写两个 skill，把 Layer 1 积累的原始痕迹自动提炼成可复用知识、把复发纠正提案成规则。参照 SwarmAI 的 `distillation_hook` 和 `steeringify` 的设计思想。

### 课程概念
- Distill 用 skill：需判断、调 LLM（Slide 4、6）
- Evolve = 硬化 + 遗忘（Slide 7）
- 频率门控：一次性观察不升级（SwarmAI `_passes_frequency_gate`）
- 人类 gate：绝不让 agent 自改规则（Slide 7）

### Step 2.1 — Distill：从日志炼出教训 (8 min)

```bash
claude
> 帮我创建一个 skill 文件 skills/distill-memory/SKILL.md，参照以下设计：
>
> ---
> name: distill-memory
> description: 将 memory/daily/ 的原始日志蒸馏为 memory/MEMORY.md 的持久条目
> tools: Read, Write, Glob, Grep
> ---
>
> # 记忆蒸馏
>
> ## 设计参照
> 参照 SwarmAI distillation_hook 的两阶段架构：
> - 阶段1：从 daily 日志提取结构化信号（decisions, lessons, patterns）
> - 阶段2：频率门控 + 去重后写入 MEMORY.md
>
> ## 触发条件
> memory/daily/ 下有 ≥3 个未标记 <!--distilled--> 的日志文件
>
> ## 提取三类条目
>
> ### 1. 关键决策（Key Decisions）
> 识别模式：decided to / chose / will use / going with / switched to
> 格式：- [YYYY-MM-DD] **决策标题** — 为什么这样选择（保留 why）
>
> ### 2. 教训（Lessons Learned）
> 识别模式：lesson learned / fixed by / root cause was / should have / next time
> 格式：- [YYYY-MM-DD] **教训标题** — 具体怎么避免
>
> ### 3. 复发模式（Recurring Patterns）
> 条件：同类事件在不同日志中出现 ≥2 次（频率门控）
> 格式：- [YYYY-MM-DD] **模式名** — 出现N次，建议动作
>
> ## 写入规则
> - 追加（prepend）到 memory/MEMORY.md 对应 section
> - 去重：如果 MEMORY.md 已有相同标题的条目，跳过不写
> - 每条必须对未来会话可直接用（能指导判断，不是流水账）
> - 蒸馏完给 daily 文件尾部加 <!--distilled YYYY-MM-DD-->
>
> ## 铁律
> - 只提炼"学到了什么"，不照抄"发生了什么"
> - 不删 daily（留待 TTL 过期或手动归档）
> - 总 MEMORY.md 体积控制在 <30K token（超出时标记最旧条目为 dormant）
```

**SwarmAI 对标讲解**（讲师用）：
> SwarmAI 的 `_extract_decisions()` 用 `DECISION_PATTERNS_STRICT` 正则匹配（~10 个模式），`_extract_lessons()` 用 `LESSON_PATTERNS`。学员版让 Claude Code 用自然语言做同样的识别——更灵活但不可重复。生产环境应该渐进收紧为 regex（呼应 M9 硬化路径：L1 文字 → L2 代码）。
>
> 频率门控对应 SwarmAI 的 `_passes_frequency_gate()`：它用 fingerprint overlap（词集 ≥30% 重叠）判断是否"同一主题出现在多个 DA 文件"。学员版简化为"同类事件 ≥2 次"由 LLM 判断。
>
> 去重对应 SwarmAI 的 `_run_locked_write()` 中的双策略去重：120 字符前缀匹配 + bold 标题匹配。学员版让 LLM 在写入前先检查已有条目。

**验证**：

```bash
# 先准备数据（如果课堂时间不够 3 个 daily，手动造）
> 读一下 memory/daily/ 下有几个文件，如果不够 3 个，帮我基于这个项目之前的工作，
> 生成 2 个合理的 daily 日志（模拟前两天的会话痕迹）

# 运行蒸馏
> /distill-memory

# 检查产出
> 读 memory/MEMORY.md，告诉我新增了哪些条目，它们是否对未来会话有用
```

### Step 2.2 — Evolve：纠正变规则提案 (8 min)

```bash
> 帮我创建 skills/evolve-memory/SKILL.md：
>
> ---
> name: evolve-memory
> description: 扫描 corrections，把复发纠正提案为规则；标记过期记忆为 dormant
> tools: Read, Write, Grep
> ---
>
> # 记忆进化（硬化 + 遗忘）
>
> ## 设计参照
> 参照 SwarmAI 的三层机制：
> - distillation_hook._extract_corrections() → 提取纠正
> - steeringify.group_and_propose() → 聚类+提案
> - evolution_maintenance_hook → 衰减过期条目
>
> ## 硬化：纠正 → 规则提案
>
> 1. 读 memory/corrections.md，按相似主题归类
> 2. 同类纠正出现 ≥3 次 → 生成规则提案到 rules/proposed.md：
>    - **规则文本**：一句话、可判定、格式参照 rules/personal.md 现有条目
>    - **级别**：MUST（会造成 bug/安全问题）/ SHOULD（偏好/风格）
>    - **证据**：引用触发的纠正记录（日期+原文摘要）
>    - **建议硬化层级**：
>      - L1 文字规则（首次）
>      - L2 hook 门控（复发 5+ 次）
>      - L3 结构性不可能（反复跨项目出现）
> 3. **绝不**直接写入 rules/personal.md 或 CLAUDE.md
>
> ## 遗忘：达尔文式衰减
>
> 4. 扫 memory/MEMORY.md：
>    - 条目日期 >60 天 且 该条目的关键词在最近 5 个 daily 日志中没出现过
>      → 在条目末尾追加 <!--dormant YYYY-MM-DD-->
>    - 已 dormant 超过 30 天 → 移到 memory/archive.md（不删）
>
> ## 铁律
> - 执行者不是立法者：只写 proposed.md，人审后手动转正
> - 遗忘 ≠ 删除：dormant 降权不删，archive 留可查
> - 被推翻的旧决策：标 superseded_by + 降权（SwarmAI COE03 教训）
```

**SwarmAI 对标讲解**（讲师用）：
> SwarmAI 的 evolve 实际上更激进：
> - `_check_steeringify_proposals()` 调用 `steeringify.group_and_propose()` 做聚类，min_group_size=2 就触发
> - `_signal_evolution_corrections()` 当 ≥5 条新 corrections 积压时，通知 `evolution_maintenance_hook` 提前跑（不等 7 天定时器）
> - `_enforce_section_caps()` 用 Ebbinghaus 衰减算法淘汰——`compute_decay_score()` 综合 ref_count、sessions_referenced、last_referenced 算分，最低分的先淘汰
>
> 学员版简化为"≥3 次提案 + 60 天未引用休眠"——足够个人使用，且不需要数据库。
>
> `superseded_by` 标记对应 SwarmAI COE03 事故的真实教训：一条"过期但未标记"的记忆误导了 5 个连续会话。结构性预防比"人记得去删"可靠得多。

**验证**：

```bash
# 准备数据（如果 corrections 不够 3 条同类，手动补充模拟数据）
> 帮我在 memory/corrections.md 补充几条模拟纠正（模拟我反复纠正同一类问题），
> 比如反复纠正"不要在没有错误处理的情况下直接调用外部 API"

# 运行进化
> /evolve-memory

# 检查产出
> 读 rules/proposed.md，有没有规则提案？证据是否充分？
> 同时检查：proposed 的内容是否出现在了 personal.md 里（不应该！）
```

**关键教学时刻——人类 gate 的体验**：

```bash
# 讲师引导学员手动"批准"一条提案
> 我看了 proposed.md 里的第一条提案，我同意它。帮我把它正式转到 rules/personal.md，
> 并在 proposed.md 里标记为 [已批准 YYYY-MM-DD]

# 讲师问：如果刚才那步是自动的会怎样？
# 答：错误的提案也会被自动批准，agent 之后会自信地执行错误规则
```

### Done 标准
- [ ] `distill-memory` skill 能从 daily 日志提炼 MEMORY 条目
- [ ] 条目有去重、有来源日期、是"学到了什么"不是流水账
- [ ] `evolve-memory` skill 能从复发纠正生成规则提案
- [ ] 提案在 proposed.md，**未自动进入** personal.md（人类 gate 生效）
- [ ] 学员亲手"批准"了至少一条规则转正
- [ ] 理解 superseded_by 的意义（旧决策降权不删）

---

## Layer 3 — 自动化编排：让飞轮自转 (12 min)

### 目标
配置让 Layer 1+2 自动运转的触发机制 + 记忆健康自检。课后无需手动干预，正常使用 Claude Code 即可驱动飞轮。

### 课程概念
- Retrieve 时顺带检测蒸馏需求（零额外开销，SwarmAI 的"搭顺风车"思想）
- 健康度量化（Slide 11 Layer 2 简化版）
- **SwarmAI 对标**：`distillation_hook` 在每次 `SessionEnd` 检查 `UNDISTILLED_THRESHOLD`，有则自动蒸馏

### Step 3.1 — 智能注入 + 按需触发蒸馏 (5 min)

```bash
> 帮我升级 .claude/hooks/inject-memory.sh，增加"蒸馏提醒"逻辑：
>
> 1. 数 memory/daily/ 下没有 <!--distilled 标记的文件数量
> 2. 如果 ≥3 个：
>    - 在注入内容末尾追加一段 systemMessage：
>      "📋 你有 N 个未蒸馏的日志。本次会话结束前，建议运行 /distill-memory 整理记忆。"
> 3. 如果 corrections.md 超过 10 条未处理的纠正：
>    - 追加提醒："⚡ 有 N 条积压纠正。建议运行 /evolve-memory 检查是否有复发模式可提案为规则。"
> 4. 无论如何都全量注入 MEMORY.md + personal.md + 最近 5 条 corrections
>
> 关键：提醒是建议不是强制——agent 收到提醒会在合适时机提示用户，不打断当前工作
```

**SwarmAI 对标讲解**（讲师用）：
> SwarmAI 设 `UNDISTILLED_THRESHOLD = 0`（每次会话关闭都蒸馏），因为它有独立后台进程。学员版设为 3（手动触发）——因为个人使用频率低，且蒸馏调 LLM 有成本。
>
> "corrections 积压提醒"对应 SwarmAI 的 `_signal_evolution_corrections()`：当 ≥5 条 corrections pending 时，evolution 周期提前触发。学员版用阈值 10 条触发提醒（不自动跑，因为 evolve 需要人审）。

### Step 3.2 — 记忆健康报告 (7 min)

```bash
> 帮我创建 skills/memory-health/SKILL.md：
>
> ---
> name: memory-health
> description: 对记忆系统做健康度报告：覆盖率、新鲜度、进化率、体积、闭环完整性
> tools: Read, Glob, Grep, Bash
> ---
>
> # 记忆系统健康报告
>
> ## 设计参照
> 参照 SwarmAI DDD Layer 2 的五维健康度评分思想，简化为记忆 pipeline 的五维：
>
> ## 五维评估
>
> ### 1. 覆盖率 Coverage
> - memory/ 下有多少记忆条目？
> - daily/ 积累了多少天的日志？
> - corrections 有多少条？
> - 评分：>20 条记忆 + >7 天日志 + >5 条纠正 = 满分
>
> ### 2. 新鲜度 Freshness
> - 最近一次 daily 日志是什么时候？
> - 最近一次蒸馏（有 <!--distilled--> 标记）是什么时候？
> - 有多少 daily 积压未蒸馏？
> - 评分：<3 天无新日志 + <3 个积压 = 满分
>
> ### 3. 进化率 Evolution Rate
> - corrections 中有多少条对应了 MEMORY 条目或 rules？（被消化的比例）
> - proposed.md 有多少待审提案？有多少已批准转正的？
> - 评分：消化率 >50% + 有已转正规则 = 满分
>
> ### 4. 体积 Size Budget
> - MEMORY.md 当前估算 token 数（word_count * 1.3）
> - rules/ 所有规则总 token 数
> - 总注入体积 vs 50K 上限的余量百分比
> - 评分：<30K 绿 / 30-50K 黄 / >50K 红（需要遗忘或检索）
>
> ### 5. 闭环完整性 Loop Integrity
> - hooks 配置是否完整（Stop + UserPromptSubmit + SessionStart）？
> - skills 是否存在（distill-memory + evolve-memory）？
> - MEMORY.md 是否存在且非空？
> - 评分：全有 = 满分；缺任何一环 = 闭环断裂
>
> ## 输出格式
>
> | 维度 | 得分 | 状态 | 说明 |
> |------|------|------|------|
> | 覆盖率 | N/100 | 🟢/🟡/🔴 | ... |
> | ... | ... | ... | ... |
>
> **总评**：🟢 飞轮健康 / 🟡 需关注（某环节积压）/ 🔴 闭环断裂
>
> **建议下一步**：基于最低分维度给出 1-2 条具体行动
```

**SwarmAI 对标讲解**（讲师用）：
> 这里的五维设计简化自 SwarmAI `ddd_health.py` 的五维：
> - staleness(.25) → Freshness
> - completeness(.20) → Coverage
> - usage(.25) → Evolution Rate（被引用/消化的比例）
> - decay(.15) → Size Budget（衰减是否在控制体积）
> - contradiction(.15) → Loop Integrity（系统一致性）
>
> SwarmAI 的健康分驱动的是"agent 信任与自主度"（低分 → agent 降低自主度、主动问人）。学员版驱动的是"用户对系统的信心"——同样的思想，不同的消费者。
>
> 关键判断（AI 给不了的）：健康报告的目的是**让学员知道系统状态**，不是**给学员排维护待办**。如果每次跑健康报告都产出一堆"你该去做 X"的清单，学员很快就不跑了——和文档腐烂一个道理。正确做法：低分维度 → 建议跑对应 skill（/distill-memory 或 /evolve-memory），而不是手动修文件。

**验证**：

```bash
> /memory-health
# 预期：看到一张五维报告
# 典型现象：Layer 1 刚跑通，覆盖率低、进化率 0（因为还没跑过 distill/evolve）
# 这恰好说明飞轮需要时间积累——Compound 不是即时的
```

### Done 标准
- [ ] SessionStart hook 智能注入 + 按需提醒蒸馏/进化
- [ ] /memory-health 输出五维健康报告
- [ ] 学员理解：课后只需正常用 Claude Code，飞轮就会自动提醒积累
- [ ] 整套系统配置完毕，可在日常项目中持续运行

---

## 产出清单（学员课后直接带走使用）

```
.claude/
├── hooks/
│   ├── capture-session.sh      # Stop hook：记 git 痕迹
│   ├── capture-correction.sh   # UserPromptSubmit hook：捕获纠正
│   └── inject-memory.sh        # SessionStart hook：注入 + 提醒
├── settings.json               # 三个 hook 的注册配置
skills/
├── distill-memory/SKILL.md     # 日志→教训 蒸馏工艺
├── evolve-memory/SKILL.md      # 纠正→规则 进化工艺
└── memory-health/SKILL.md      # 五维健康报告
memory/
├── daily/                      # 原始会话痕迹（30天TTL）
├── corrections.md              # 纠正信号（最高价值数据）
├── MEMORY.md                   # 蒸馏后的持久记忆（全量注入）
└── archive.md                  # 衰减归档（可查不注入）
rules/
├── personal.md                 # 正式规则（人审后转正）
└── proposed.md                 # 规则提案（等人审批）
```

**课后使用指南**（一句话）：正常用 Claude Code 工作，它会自动捕获；看到蒸馏提醒就跑 `/distill-memory`；看到进化提醒就跑 `/evolve-memory` 并审批提案；偶尔跑 `/memory-health` 检查飞轮健康。一个月后你的 Claude Code 会比第一天聪明得多。

---

## Lab 复盘讨论 (3 min)

1. **飞轮验证**：你刚跑通的三层里，哪一层断了飞轮就停？（答：Layer 1 的 capture 断了最致命——没原料一切归零。但 retrieve 断了也白搭——记了但不注入等于没记）

2. **对标 SwarmAI**：SwarmAI 每次会话关闭自动蒸馏（UNDISTILLED_THRESHOLD=0），你的版本是手动触发。什么情况下你也该改成自动？（答：当你每天 5+ 个会话时——积压速度超过手动消化速度）

3. **治理验证**：你的 evolve 只写 proposed.md。如果某天你嫌每次审批麻烦，把它改成自动写入 personal.md——给你自己一个不这么做的理由。（答：SwarmAI COE03 事故——一条错误记忆误导了 5 个会话。规则错误的代价是乘法：它影响之后所有会话的所有决策）

4. **一周后追问**（课后作业）：一周后跑一次 `/memory-health`，截图发到学习群。看看谁的飞轮在转、谁的停了、为什么停的。

5. **扩展路径**：当 MEMORY.md 涨到 30K+ token，你的第一反应是什么？（答：先跑 evolve 的遗忘标记；如果 dormant 了还是太大，才考虑拆分为多个文件 + 选择性注入。向量库是最后手段——呼应 Slide 8"别急着上"）

---

## 与原版实验的关键改变

| 维度 | 原版 | 改进版 |
|------|------|--------|
| **产出可复用性** | 教学骨架，需大量改造 | 直接装入学员项目，课后即用 |
| **层次感** | 5 步并列（capture/distill/evolve/retrieve/DDD体检） | 3 层递进（闭环→蒸馏→自动化），每层都 self-contained |
| **与 Claude Code 协作** | 绕开原生系统建平行文件 | 利用原生 hooks/skills 系统，符合 Claude Code 工作方式 |
| **SwarmAI 对标** | 概念引用（幻灯片提到） | 每步标注对应的 SwarmAI 组件 + 讲师可展开讲 |
| **课堂体验** | 需 ≥3 个 daily 才能触发 distill | Layer 1 在 3 分钟内验证闭环 |
| **课后持续性** | 需手动跑各 skill | Layer 3 自动提醒，学员只需响应 |
| **DDD 体检** | 10 min 写 Python 纯函数脚本 | 替换为 memory-health skill（更轻、和主题更紧密）|
| **教学锚点** | 讲原理为主 | 每步都有"SwarmAI 怎么做的 → 学员版为什么简化"的对比 |

---

## 讲师备注

### 关于 DDD 体检（原 Step 5）的处置

原版 Step 5 的 `score_health.py` 纯函数设计很好，但：
1. 在 40 分钟 Lab 里写 Python 脚本偏离了"用 Claude Code 解决问题"的主线
2. DDD 文档可能在 M7/M8 还不够成熟，跑出的分数无参考意义
3. 与记忆 pipeline 主题关联较弱

**建议**：将 DDD 体检移到 M14（运维）或作为 Lab 11 的课后加分项。M11 聚焦"一套课后能直接用的记忆飞轮"更有冲击力。如果 Day3 时间充裕，可在 memory-health 演示后追加 5 分钟"DDD 文档也能这样评分"作为预告。

### 如何利用 SwarmAI 做现场演示

如果教室环境允许，可以在 Layer 2 讲解时打开 SwarmAI 的源码做 live 对比：

```bash
# 展示 SwarmAI 的 CORRECTION_PATTERNS（50+ 行正则）vs 学员版的 6 个信号词
cat misc/SwarmAI/backend/core/extraction_patterns.py | grep -A30 "CORRECTION_PATTERNS"

# 展示 SwarmAI 的频率门控（fingerprint overlap 算法）
grep -A20 "_passes_frequency_gate" misc/SwarmAI/backend/hooks/distillation_hook.py

# 展示一个真实的 DailyActivity 文件结构
cat misc/SwarmAI/backend/core/daily_activity_writer.py | head -20
```

这让学员看到：你们做的是同一件事的入门版本，但设计思想一脉相承。产品级需要更多边界处理——而你现在知道那些边界在哪里。
