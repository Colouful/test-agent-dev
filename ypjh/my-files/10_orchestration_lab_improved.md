# Lab 10 改进版 — 给你的 Claude Code 装一条可直接复用的编排流水线

> **设计原则**：每层产出都是学员课后能直接用的真实系统。参照 SwarmAI 实际架构（`hooks` → `subagents` → `session_router + exit-contract`），简化为个人版本，但保留工业设计的关键判断。
>
> **时长**：45 分钟
> **工具**：Claude Code（唯一工具）
> **前置**：harness repo 已有 `rules/`（M3-M7 的产出）、`ci/`（如有）；学员理解 Claude Code 基本用法
> **产出承诺**：课后你的 Claude Code 有"硬约束自动拦"、"子代理独立做事"、"状态跨会话不丢"三大能力——不再是一个"你说什么它做什么"的裸 agent
>
> **层次设计**：
> - **Layer 1 — 硬约束自动拦**（12 min）：配好 hook，agent 编辑后自动检查，违规自动修——课后每次写代码都在保护你
> - **Layer 2 — 职责拆分委派**（15 min）：定义子代理，把"跑测试"独立出去——课后一句话委派，主对话不被测试日志淹没
> - **Layer 3 — 状态续命 + 人类 Gate**（18 min）：exit-contract 跨会话交接 + 不可逆操作人类把关——课后复杂任务不再"每次从头来"

---

## 设计哲学：从 SwarmAI 学到什么

SwarmAI 的编排系统（170K LOC 后端）给了三个关键教训：

1. **硬约束必须沉为 Hook，软规则放 CLAUDE.md** — SwarmAI 在 25 天内观察到 agent 违规跳过自己写的流程 6 次（C011→C032 事故）。文字警告全部失效，只有机械门止住了它。教训：规则要么不可绕过（hook），要么就等着被绕过。学员版：把 M7 的架构护栏从"建议"变成"自动拦截"。

2. **子代理动机只有三个：上下文隔离、最小权限、并发** — SwarmAI 有 86 个 skill 模块（子代理），但它们存在的理由永远是这三个之一。"分工协作"听起来酷，但每多一个子代理就多一份"协作税"（handoff 成本 + 上下文丢失）。学员版：只造一个 test-runner，体验"隔离上下文"的真实收益。

3. **状态不落文件 = 每次从头** — SwarmAI 的 `session_router` 跨轮次复用 Claude CLI 子进程（保持上下文），关闭后用 `daily_activity_hook` + exit-contract 落地关键状态。没有这个，300+ sessions 的项目根本不可能延续。学员版：`exit-contract` 模板 + `memory/progress.md`。

---

## Layer 1 — 硬约束自动拦：Hook 即法律 (12 min)

### 目标
配置一个 PostToolUse hook，让 agent 每次编辑文件后自动跑 lint + 架构检查。违规时错误回灌、agent 自动修正。学员体验"规则不可被绕过"的力量。

### 课程概念
- Hook 是硬约束载体（Slide 2，呼应 M3 Slide 7）
- Hook 要快（Slide 8）——慢的检查走 CI 不走 hook
- "能绕过的规则 = 没有规则"（Slide 3 人格陷阱案例）
- **SwarmAI 对标**：21 个 hooks 中的 `code_change_feed`（分析 diff → 建议更新 TECH.md）+ 架构约束 hooks

### Step 1.1 — 配置编辑后自动检查 (7 min)

```bash
claude
> 帮我配置 Claude Code 的 PostToolUse hook（当 agent 使用 Edit 或 Write 工具后触发），实现：
>
> 1. 创建 hooks/post-edit-check.sh 脚本：
>    - 运行 lint 检查（npx eslint --quiet 被编辑的文件路径，如拿不到路径则 eslint src/）
>    - 运行简单架构检查：grep 检查 src/ 下是否有直接引用数据库/外部 API 的代码出现在 UI 组件中
>      （例：grep -r "fetch\|axios\|prisma\|db\." src/components/ 2>/dev/null）
>    - 如有违规：非零退出码 + stdout 输出问题说明（让 agent 能收到并修正）
>    - 如无问题：exit 0，不输出（静默通过）
>    - 总超时不超过 10 秒
>    - set -uo pipefail
>
> 2. 配置 .claude/settings.json：
>    {
>      "hooks": {
>        "PostToolUse": [{
>          "matcher": "Edit|Write",
>          "hooks": [{
>            "type": "command",
>            "command": "./hooks/post-edit-check.sh",
>            "timeout": 10
>          }]
>        }]
>      }
>    }
>
> 3. 确保 hooks/ 目录存在，脚本有执行权限
```

### Step 1.2 — 体验"规则不可绕过" (5 min)

```bash
> 现在故意在 src/ 里的一个组件文件中引入一个架构越界（比如直接写 fetch('http://...')）。
> 观察编辑后发生了什么。

# 预期：hook 自动触发，输出架构违规信息，agent 收到后自动修正
# 关键体验：你不需要提醒它，hook 替你执法
```

**关键教学时刻**：
> 讲师问："如果这个约束写在 CLAUDE.md 的规则里而不是 hook 里，它一定会遵守吗？"
> 答：SwarmAI 25 天实测——文字规则被跳过 6 次。Hook 0 次绕过。这就是 M3 "规则可执行"的终点：真正关键的规则，做成 hook。

**SwarmAI 对标讲解**（讲师用）：
> SwarmAI 的 `code_change_feed` hook 在每次代码改动后分析 diff，检查是否需要同步更新 TECH.md。它的 21 个 hooks 覆盖了从代码风格到知识同步的方方面面。但核心设计原则完全一致：**hook 负责"绝不能破"的硬约束，CLAUDE.md 负责"最好遵守"的偏好**。
>
> 学员版只有 1 个 hook（lint + arch-check）——这已经比没有 hook 的项目高出一个维度。课后学员可以根据自己项目的"绝不能破"清单逐步追加。

### 预期输出
- `.claude/settings.json` 含 PostToolUse hook 配置
- `hooks/post-edit-check.sh` 可执行
- 编辑后自动检查，违规时 agent 自动修正
- agent 修正后重新编辑，这次通过——闭环

### Done 标准
- [ ] Hook 在每次编辑后自动触发（秒级）
- [ ] 违规时错误信息回灌 agent 并促成自动修正
- [ ] 通过时静默，不打扰正常工作流
- [ ] 学员理解：这是"不可被绕过"的硬约束，不是建议

---

## Layer 2 — 职责拆分委派：子代理 (15 min)

### 目标
定义一个 test-runner 子代理，体验"上下文隔离"和"最小权限"的真实收益。学员感受到：委派 vs 主对话里跑测试，体验截然不同。

### 课程概念
- Subagent 三动机：上下文隔离 / 最小权限 / 并发（Slide 4-5）
- 约束优先：子代理只能做被允许的事（Slide 4）
- 关键判断：什么时候该拆子代理，什么时候不该（Slide 5 天平）
- **SwarmAI 对标**：86 个 skills（子代理）各有明确职责边界，`tools` 字段限定能力

### Step 2.1 — 定义 test-runner 子代理 (7 min)

```bash
claude
> 帮我创建 .claude/agents/test-runner.md：
>
> ---
> name: test-runner
> description: 运行测试套件并结构化报告结果。当需要执行测试、定位失败原因时委派给它。
> tools: Bash, Read, Grep
> ---
>
> # 角色：测试执行者
>
> ## 职责
> 1. 运行 `ci/verify.sh` 或项目测试命令（npm test / vitest 等）
> 2. 解析结果，结构化报告：通过数 / 失败数 / 每个失败的文件:行 + 原因
> 3. **不修改任何实现代码** — 你只负责跑和报告，修复交回主 agent
>
> ## 输出格式
> ```
> 总览：X passed / Y failed
> ---
> 失败 #1：
>   测试名：test_xxx
>   期望：xxx
>   实际：xxx
>   位置：src/foo.ts:42
>   修复线索：xxx
> ---
> ```
>
> ## 红线
> - 绝不改实现代码
> - 绝不改测试代码
> - 只用 Bash/Read/Grep 三个工具
```

### Step 2.2 — 对比体验：委派 vs 不委派 (8 min)

```bash
# 实验 A：不用子代理，直接在主对话跑测试
> 运行 ci/verify.sh（或项目测试命令），如果有失败，分析原因

# 观察：测试日志占满上下文，之后的对话容易被"测试噪声"干扰

# 实验 B：用子代理
> 用 test-runner 跑一下测试，报告结果

# 观察：子代理在隔离上下文运行，主对话只收到结构化的报告，干净清晰
```

**关键教学时刻**：
> 讲师问："两次体验有什么不同？子代理的真正价值是什么？"
> 答：不是"分工酷"——是**上下文保护**。测试输出可能有几百行日志，全塞进主对话会稀释你之前建立的所有上下文。子代理用自己的上下文消化日志，只返回结构化摘要。

**SwarmAI 对标讲解**（讲师用）：
> SwarmAI 有 86 个 skill（子代理），每个 skill 定义在 `backend/skills/s_<name>/` 目录。关键设计：
> - `s_code-review`：只有 Read + Grep，不能修改代码（和 test-runner 一样的最小权限思想）
> - `s_autonomous-pipeline`：有完整权限，但被严格约束了输出格式
> - skill 之间不互相调用——避免"子代理调子代理"的级联失控
>
> 子代理的成本：每次委派 = 一次上下文切换 + handoff 开销。SwarmAI 的经验是：只在上下文隔离或权限隔离能带来明显收益时才拆。"因为能拆所以拆"是反模式。

### 预期输出
- `.claude/agents/test-runner.md` 可被 `/agents` 列出
- 委派测试时得到干净的结构化报告
- 主对话上下文不被测试日志污染
- 学员能说出"什么时候该用子代理，什么时候不该"

### Done 标准
- [ ] test-runner 定义完成，`/agents` 可见
- [ ] 委派后在隔离上下文运行，主对话只收到报告
- [ ] 报告结构化、信息富（能直接指导修复）
- [ ] 子代理没越权修改代码
- [ ] 学员能判断"拆 vs 不拆"的决策依据

---

## Layer 3 — 状态续命 + 人类 Gate (18 min)

### 目标
配置 exit-contract 让状态跨会话存活，设置人类 gate 保护不可逆操作。学员体验"复杂任务中途关机不丢进度"和"危险操作必须人确认"。

### 课程概念
- Exit-contract：状态落文件（Slide 6）
- 自动 vs 人类 gate 的判断（Slide 7）
- 进度 + 已试方案 + 下一步 = 完整交接（呼应 M13 STATE.md）
- **SwarmAI 对标**：`session_router` 热恢复（`--resume`）+ `daily_activity_hook` 写交接 + `SummarizationPipeline` 的"三问"格式

### Step 3.1 — Exit-Contract 跨会话续命 (10 min)

```bash
claude
> 帮我建立完整的会话交接机制：
>
> 1. 创建 memory/exit-contract.template.md：
>    ```markdown
>    # 会话交接契约
>    ## 本次完成了什么
>    - (列出已完成的具体事项)
>
>    ## 进行中 — 下次从这里接
>    - (正在做但没做完的事，精确到文件和函数)
>
>    ## 已尝试但失败的方案（别再走这条路）
>    - (方案描述 + 为什么失败)
>
>    ## 关键决策及理由
>    - (做了什么选择 + 为什么这样选)
>
>    ## 下一步建议
>    - (具体的 1-3 个 action items)
>    ```
>
> 2. 在 CLAUDE.md 或 rules/personal.md 中加一条规则：
>    "当用户说'交接'或'收工'或会话内容复杂时，主动按 memory/exit-contract.template.md 的格式
>    将当前进度写入 memory/progress.md。特别重要：'已失败方案'那栏必须填，
>    它防止下次会话重复犯错。"
>
> 3. 配置 SessionStart hook（或在 inject-memory.sh 中追加逻辑）：
>    - 如果 memory/progress.md 存在且非空，把它的内容注入会话上下文
>    - 输出格式："## 上次交接\n" + progress.md 内容
```

**验证跨会话**：

```bash
# 模拟一个复杂任务中途
> 帮我重构 src/ 里的识别模块（或任何正在做的事），做到一半时我说：交接

# 观察：agent 按模板写出 progress.md
> 读 memory/progress.md，确认格式完整、"已失败方案"有内容

# 退出，重新进入
/exit
claude
> 我上次做到哪了？

# 预期：agent 读到 progress.md，精确说出上次的进度、已试方案、下一步
```

**SwarmAI 对标讲解**（讲师用）：
> SwarmAI 的 `SummarizationPipeline` 围绕三个问题组织摘要：
> - 交付了什么？（deliverables）
> - 产出是什么？（files_modified + git_commits）
> - 学到了什么？（lessons + corrections）
>
> 学员版的 exit-contract 就是同样思想的显式版本。SwarmAI 因为管理 Claude CLI 子进程，可以自动在会话关闭后提取（`daily_activity_hook`）。学员用的是原生 Claude Code，所以需要主动触发（说"交接"）。
>
> "已失败方案"这栏对应 SwarmAI 的 `corrections` 字段 + M13 的 STATE.md——它防止 loop 反复犯错，也防止跨会话重复犯错。同一个思想，不同的粒度。

### Step 3.2 — 人类 Gate：不可逆操作必须确认 (8 min)

```bash
> 帮我配置一个"人类 gate"规则：
>
> 1. 在 rules/personal.md 追加：
>    ## 人类 Gate 规则
>    以下操作必须暂停并等待我明确确认（输出"⚠️ 需要确认"后等我回复），绝不自动执行：
>    - git push（任何推送到远端）
>    - 删除文件（rm / unlink）
>    - 修改 CI 配置
>    - 修改 package.json 的 dependencies
>    - 调用外部 API（真实环境，非 mock）
>
>    以下操作可以自动执行，不需要问我：
>    - git add / commit（本地提交）
>    - 创建/编辑文件
>    - 运行测试
>    - 安装 devDependencies
>
> 2. （可选进阶）用 PreToolUse hook 对 "git push" 做机械拦截：
>    配置一个 PreToolUse hook，matcher 为 Bash，
>    脚本检查命令是否包含 "git push"，如果是则 exit 2（BLOCK）
```

**验证人类 gate**：

```bash
> 帮我把当前改动提交并推送到远端

# 预期：
# - git add + commit 自动完成（不问你）
# - git push 前暂停："⚠️ 需要确认：即将 push 到 origin/main，是否继续？"
```

**关键教学时刻**：
> 讲师问："为什么 git commit 允许自动但 git push 要人确认？"
> 答：可逆性。commit 是本地的，随时能 amend/reset；push 出去了别人就能看到，是不可逆的。Gate 的决策标准是**后果的可逆性**，不是操作的复杂度。
>
> 追问："这套规则如果放到 M13 的 loop 里，哪些 gate 能去掉？哪些绝不能去？"
> 答：loop 可以自动 commit、自动跑测试——但 push 和删文件永远不能自动。loop 跑到终点后 PR 给你审，这就是 human out of the loop 但有最后关口。

### 预期输出
- `memory/exit-contract.template.md` 交接模板
- `memory/progress.md` 含实际交接内容
- 新会话能读取并精确恢复上次进度
- 不可逆操作有 gate（agent 暂停等人确认）
- 可逆操作无 gate（自动执行不打扰）

### Done 标准
- [ ] Exit-contract 模板完整（5 栏都有用）
- [ ] 跨会话验证成功——新会话能恢复上次进度
- [ ] "已失败方案"栏有内容（防重复犯错）
- [ ] 人类 gate 生效：push/删除等暂停确认
- [ ] 普通操作不被打断（自动 gate 判断正确）
- [ ] 学员能说出"什么操作该 gate、什么不该"

---

## 产出清单（学员课后直接带走使用）

```
.claude/
├── settings.json               # PostToolUse hook 注册
├── agents/
│   └── test-runner.md          # 测试执行子代理
hooks/
├── post-edit-check.sh          # 编辑后 lint + 架构检查
memory/
├── exit-contract.template.md   # 会话交接模板
├── progress.md                 # 实际交接状态
rules/
├── personal.md                 # 含人类 Gate 规则
```

**课后使用指南**（一句话）：正常用 Claude Code 工作，编辑后自动检查护你代码质量；需要跑测试时一句"用 test-runner"委派不污染上下文；复杂任务说"交接"落地进度不怕丢；push/删除等危险操作永远会等你确认。

---

## Lab 复盘讨论 (3 min)

1. **硬 vs 软**：你设的 hook 和 rules/personal.md 里的规则，本质区别是什么？如果一条规则 agent 连续违反 3 次，你该把它升级到哪？（答：从 rules 升级到 hook。SwarmAI 25 天实测：文字规则被跳过 6 次，hook 零次绕过）

2. **子代理判断**：如果你的项目有 "code review"、"文档生成"、"部署" 三个操作，哪个最该做成子代理？（答：code review——上下文隔离价值最大，且只需 Read 权限。部署不是子代理的活——它需要人类 gate）

3. **通向 loop**：今天你还在"提交前等我确认"。如果把这条流水线交给 M13 的 loop 自己跑，exit-contract 变成什么？（答：变成 STATE.md——loop 每轮读它，知道上一轮试过什么失败了）

4. **扩展路径**：你现在只有 1 个 hook + 1 个子代理。SwarmAI 有 21 个 hook + 86 个 skill。什么信号告诉你"该加新的了"？（答：当你发现自己反复手动做同一个检查——就该变成 hook；当你发现主对话被某类输出淹没——就该拆子代理）

---

## 与原版实验的关键改变

| 维度 | 原版 | 改进版 |
|------|------|--------|
| **层次感** | 3 步并列（hook/subagent/memory），无递进 | 3 层递进（拦截→委派→续命），每层 self-contained |
| **体验设计** | 配置完毕就结束 | 每层有"对比实验"让学员感受差异 |
| **产出可复用性** | 教学骨架，需改造 | 直接装入学员项目，课后即用 |
| **SwarmAI 对标** | 概念引用 | 每步标注 SwarmAI 组件 + 讲师可展开讲 |
| **判断层教学** | 配置 how-to 为主 | 每步嵌入"为什么这样设计"的判断讨论 |
| **通向 loop** | 仅在复盘提一句 | 每层显式标注"这件事到了 M13 loop 里会变成什么" |

---

## 讲师备注

### 关于子代理判断的天平

原版 Slide 4-5 讲了子代理三动机和天平尺子，是本模块判断层核心。Lab 里的对比实验（Step 2.2）是让学员"体验"天平的关键——不是你告诉他"隔离好"，是他亲手感受到主对话被日志淹没 vs 干净报告的差距。

如果课堂时间紧张，Step 2.2 的实验 A（不委派）可以改为讲师演示+截图对比，学员只跑实验 B。但建议尽量保留——体验式学习是对抗"我知道但我不做"的最好方式。

### 安全提醒

- `--dangerously-skip-permissions` 绝不在 hook 演示中使用——hook 本身就是安全机制，用跳过权限来演示安全机制是逻辑矛盾
- PreToolUse hook 拦截 git push 是高级选项——如果学员 Claude Code 版本不支持 exit code 2 = BLOCK 语义，用 rules 规则即可
- exit-contract 的"已失败方案"栏**必须强调**——这是 M13 STATE.md 的前置概念，也是防止 loop 重复犯错的核心
