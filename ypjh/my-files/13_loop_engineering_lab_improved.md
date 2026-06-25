# Lab 13 改进版 — 跑通你的第一个 Worker Loop：从"看着它自己修 bug"到"敢放手"

> **设计原则**：每层产出都是学员课后能直接用的真实系统。参照 SwarmAI 实际经验（3 连挂事故 / 11 天烧钱 / 2-strike 规则 / 状态机建模），让学员从"写出 loop"递进到"敢放心跑 loop"。
>
> **时长**：45 分钟
> **工具**：Claude Code（由 loop 脚本调用，headless/print 模式）
> **前置**：harness repo 已有 `ci/verify.sh`（M12 产出，主终点线是确定的结构+契约断言）、M9 识别功能实现、M10 exit-contract
> **产出承诺**：课后你有一个可在任何项目复用的 `loop/worker-loop.sh`——带熔断、带记忆、带退出码语义——可直接用于"让 agent 自己修 bug"
>
> **层次设计**：
> - **Layer 1 — 看它自己转**（15 min）：写最小 loop，亲眼看 agent 无人值守修 bug——震撼体验
> - **Layer 2 — 装好刹车**（15 min）：熔断三件套 + 退出码语义——从"能跑"到"敢跑"
> - **Layer 3 — 给它记忆**（15 min）：STATE.md 外部记忆 + 2-strike 规则——从"蛮力试"到"聪明试"

---

## 设计哲学：从 SwarmAI 学到什么

SwarmAI 的自动化循环（300+ sessions 持续运行）给了三个关键教训：

1. **Loop 是程序不是 prompt** — SwarmAI 的 `session_router` 管理多个 Claude CLI 子进程的生命周期（COLD→IDLE→STREAMING 状态机），每个"循环修复"任务就是一个带明确停止条件的 while 循环。里面的 Claude 调用只是 `call_agent()` 一行——难点全在循环外面的控制逻辑。Boris Cherny（Claude Code 创造者）："我不再直接 prompt Claude，我写 loop 让它去 prompt。"

2. **没有刹车的 loop 就是定时炸弹** — 真实案例：一个停止条件写错的 loop 跑了 11 天、烧了几万美金，产出是"自信的废话"（语法完美、逻辑自洽、但偏离目标）。SwarmAI 的每个 job 都有三道熔断：max_iterations + token_budget + wall_clock_timeout。学员版同样是熔断三件套。

3. **没有记忆的 loop 是金鱼** — SwarmAI 3 连挂事故（`post-mortems/02-understand-the-state-machine.md`）：守护进程自升级任务连续 3 轮"局部合理但全局错误"的修复，每次都没建模到第 5 个状态。根因：没记住"前两轮为什么失败"，所以第三轮还在同一个坑里换花样。2-strike 规则：同一类修复挂两次 = 模型错了，停手去理解系统。学员版：STATE.md 记录每轮尝试和失败，强制 loop 不重复犯错。

---

## Layer 1 — 看它自己转：最小 Loop (15 min)

### 目标
写一个最小的 worker loop：调用 Claude Code 修代码 → 跑 M12 的 verify.sh → 不过则回灌错误再来。亲眼看 agent 无人值守修 bug——第一次体验 "human out of the loop"。

### 课程概念
- Loop 是控制流程序（Slide 1、2）
- 停止条件 = M12 的 verify.sh（Slide 2-3）
- 失败信息 = 下一轮的 prompt（Slide 2，"test as prompt"）
- `claude -p`（headless/print 模式）是 loop 的基础原语
- **SwarmAI 对标**：`session_router.send()` → `session_unit` 子进程调用 → 结果回传

### Step 1.1 — 准备一个 bug (3 min)

```bash
claude
> 帮我做两件事：
> 1. 确认 ci/verify.sh 当前是绿的（所有断言通过）
> 2. 然后故意打破一条识别契约——把"低置信度标待确认"的逻辑删掉或改坏
>    （让 ci/verify.sh 失败，且错误信息指明是契约断言挂了）

# 验证
./ci/verify.sh; echo "exit=$?"
# 预期：exit=1，输出 VERIFY_FAIL stage=L2-contract
```

### Step 1.2 — 写最小 loop 脚本 (7 min)

```bash
> 帮我创建 loop/worker-loop.sh：
>
> ```bash
> #!/usr/bin/env bash
> # loop/worker-loop.sh — L1 本地 worker loop（最小版本）
> set -uo pipefail
>
> TASK="修复 src/ 中识别功能的 bug，使 ci/verify.sh 的契约断言全部通过。
> 规则：不要修改测试代码、不要修改断言、不要修改 ci/verify.sh。只改实现。"
>
> CONTEXT="$TASK"
> MAX_ITER=5
>
> echo "🔄 Worker Loop 启动 — 最多 $MAX_ITER 轮"
> echo "停止条件：ci/verify.sh 通过（退出码 0）"
> echo ""
>
> for i in $(seq 1 $MAX_ITER); do
>   echo "━━━ 第 $i/$MAX_ITER 轮 ━━━"
>
>   # 调用 Claude Code (headless/print 模式)
>   claude -p "$CONTEXT" --dangerously-skip-permissions 2>/dev/null
>
>   # 跑停止条件
>   echo "  🧪 运行 verify..."
>   if OUT=$(./ci/verify.sh 2>&1); then
>     echo "  ✅ 验证通过！第 $i 轮收敛"
>     echo ""
>     echo "=== LOOP 成功 === 退出码 0"
>     exit 0
>   else
>     echo "  ❌ 未通过 — 错误回灌下一轮"
>     CONTEXT="$TASK
>
> 上一轮验证失败，错误如下，请据此修正（不要重复之前的尝试）：
> $OUT"
>   fi
>   echo ""
> done
>
> echo "=== LOOP 未收敛 === 达到 $MAX_ITER 轮上限"
> exit 1
> ```
>
> 加可执行权限。
```

### Step 1.3 — 第一次放手 (5 min)

```bash
chmod +x loop/worker-loop.sh
./loop/worker-loop.sh
```

**观察要点**（讲师引导学员关注）：
- 每轮 agent 的修复方向变了吗？（因为错误信息在变）
- 哪一轮修好了？如果没修好——为什么？
- 全程你没有输入任何东西——这就是 "human out of the loop"

**关键教学时刻**：
> 讲师问："第一次看着它自己修 bug、你不插手——什么感受？"
> 追问："如果这个 loop 没有 MAX_ITER=5 的上限，你敢让它跑吗？"（引出 Layer 2）

**SwarmAI 对标讲解**（讲师用）：
> SwarmAI 的 `session_router` 本质就是一个更复杂的 loop：
> ```
> user_message → session_unit.send() → Claude CLI 子进程 → result
>            → 如果是 tool_use → 执行工具 → 结果回灌 → 继续
>            → 如果是 text → 返回给用户
> ```
> 学员写的 `worker-loop.sh` 和它是同构的——只是停止条件从"用户满意"变成了"verify.sh 通过"。
>
> Claude Code 的 `-p`（print 模式）是这一切的基础原语。它让 Claude Code 变成一个**可编程的函数调用**——输入是 prompt string，输出是 stdout，退出码表示成功/失败。一旦你有了这个原语，loop/pipeline/job 都是在它上面搭的编排。

### Done 标准
- [ ] `loop/worker-loop.sh` 可运行
- [ ] Loop 自动迭代：每轮调 Claude Code → 跑 verify → 回灌
- [ ] 能在不介入下修复简单 bug（或至少看到收敛趋势）
- [ ] 学员体验了 "human out of the loop"
- [ ] 理解：没有刹车，这个 loop 就是个定时炸弹（自然过渡 Layer 2）

---

## Layer 2 — 装好刹车：熔断三件套 (15 min)

### 目标
给 loop 加上完整的熔断保护：时间上限 + 退出码语义 + 安全退出信息。让学员从"能跑 loop"变成"敢跑 loop"。

### 课程概念
- 熔断是安全带不是可选项（Slide 3、7）
- 11 天烧钱事故的教训：停止条件不可达 + 没有熔断 = 灾难
- 退出码语义让上层（CI / 人类 / 更高级 loop）知道发生了什么
- 错题本 loop 的"两头烧钱"：改代码烧 token + 验证真调 AI 又烧（M12 已把真调移出主终点线）
- **SwarmAI 对标**：每个 `job` 都有 `max_runtime_seconds` + `max_cost_usd` + `max_iterations`

### Step 2.1 — 加熔断 + 退出码语义 (8 min)

```bash
claude
> 帮我升级 loop/worker-loop.sh，加入完整的熔断三件套：
>
> 1. 三道熔断（任何一个先到，无条件停）：
>    - MAX_ITER=5（已有）
>    - MAX_SECONDS=300（5 分钟时间上限）
>    - （token 预算用轮数近似——生产中可接 API usage 统计）
>
> 2. 退出码语义（让上层知道怎么停的）：
>    - exit 0 = 验证通过，修好了
>    - exit 1 = 达到最大轮数，未收敛
>    - exit 2 = 时间超限
>    - exit 3 = 环境错误（verify.sh 本身坏了）
>
> 3. 安全退出信息：
>    - 无论哪种停止，最后都输出一行摘要：
>      "LOOP_EXIT code=N reason=xxx elapsed=Xs rounds=N"
>    - 这行信息让人/CI 快速知道发生了什么
>
> 4. 在每轮开始时检查时间：
>    NOW=$(date +%s)
>    if [ $((NOW - START)) -gt $MAX_SECONDS ]; then
>      echo "LOOP_EXIT code=2 reason=timeout elapsed=$((NOW-START))s rounds=$((i-1))"
>      exit 2
>    fi
```

### Step 2.2 — 验证刹车有效 (7 min)

```bash
# 测试 1：给一个修不好的 bug（或不可达的停止条件）
# 确保 loop 在熔断处停止，而不是永远跑
> 帮我把识别功能改成一个"看起来能修但实际修不好"的状态
> （比如让契约断言依赖一个不存在的 API 返回值——agent 怎么改实现都过不了）

./loop/worker-loop.sh; echo "exit=$?"
# 预期：exit=1（轮数熔断）或 exit=2（时间熔断）
# 输出包含 LOOP_EXIT 摘要

# 测试 2：把 MAX_SECONDS 改成 10，验证时间熔断
MAX_SECONDS=10 ./loop/worker-loop.sh; echo "exit=$?"
# 预期：很快停止，exit=2

# 恢复正常 bug，验证还能修好
> 把 bug 恢复成 Layer 1 那个简单的契约违反
./loop/worker-loop.sh; echo "exit=$?"
# 预期：exit=0，修好了
```

**关键教学时刻**：
> 讲师问："如果今天没先装刹车就放手跑——错题本 loop 是两头烧钱（改代码 token + 万一验证真调 Bedrock），最坏能烧成什么样？"
> 答：11 天事故的教训。5 轮 × 每轮约 $0.5-2 的 API 调用 = $2.5-10 很合理。但如果没有 MAX_ITER 和 MAX_SECONDS，一个写错的停止条件可以无限循环。
>
> 讲师追问："退出码为什么重要？"
> 答：当 loop 是被 CI 调用时（L2 成熟度），CI 需要知道"修好了"还是"没修好需要人看"。exit 0 = 自动合 PR，exit 1/2 = 通知人类。没有退出码语义，上层就是瞎的。

**SwarmAI 对标讲解**（讲师用）：
> SwarmAI 的 job 系统（`jobs/` 13 个信号源）每个都有预算门控：
> - `max_runtime_seconds`：超时自动 kill
> - `max_cost_usd`：成本超限停止（接 Bedrock usage API）
> - `max_iterations`：轮数上限
>
> 它们的退出信息写入 `job_runs` 表，上层调度器据此决定"要不要重跑""要不要通知人类"。学员版的 `LOOP_EXIT` 摘要是同样思想的轻量版。
>
> 关键设计原则：**熔断宁紧勿松**。5 轮改不好的 bug，10 轮大概率也改不好（agent 的修复能力在第 3-5 轮已经饱和）。松的熔断只是在烧钱等一个不会来的结果。

### Done 标准
- [ ] 熔断三件套生效（轮数 + 时间 + 任何一个先到就停）
- [ ] 退出码语义清晰（0/1/2/3 各有含义）
- [ ] LOOP_EXIT 摘要信息一行可读
- [ ] 验证过"它不会无限跑"——真的在熔断处停了
- [ ] 学员理解"宁紧勿松"的设计原则

---

## Layer 3 — 给它记忆：STATE.md + 2-Strike (15 min)

### 目标
给 loop 加外部记忆，让它"记住前几轮试了什么、为什么失败"——不再做金鱼。加入 2-strike 规则：同类修复挂两次就强制升级策略。

### 课程概念
- 外部记忆对抗每轮失忆（Slide 3）
- 呼应 M10 exit-contract（同一思想在 loop 里的用法）
- 2-strike 规则（Slide 4 事故教训）：连续同类失败 = 模型错了，换个层次想
- STATE.md 也是人类事后复盘的审计日志
- **SwarmAI 对标**：3 连挂事故 → 第 4 轮"先画状态机"才对 / `daily_activity_writer` 的"三问"格式

### Step 3.1 — 加 STATE.md 记忆 (8 min)

```bash
claude
> 帮我升级 loop/worker-loop.sh，加入 STATE.md 外部记忆：
>
> 1. loop 开始时清空 loop/STATE.md
>
> 2. 每轮失败后，追加到 STATE.md：
>    ```
>    ## 第 N 轮 (HH:MM:SS)
>    **尝试方向：** （从 agent 输出的第一行提取，或写"见上方输出"）
>    **结果：** 失败
>    **错误摘要：** （verify.sh 输出的前 3 行）
>    ---
>    ```
>
> 3. 下一轮的 CONTEXT 包含 STATE.md 内容：
>    CONTEXT="$TASK
>
>    ## 历史尝试记录（不要重复这些已失败的方向）：
>    $(cat loop/STATE.md)
>
>    ## 本轮任务：
>    基于以上教训修正。最近一次错误：
>    $OUT"
>
> 4. loop 成功结束后，STATE.md 保留（人可以事后看完整排错轨迹）
```

### Step 3.2 — 加 2-Strike 检测 (4 min)

```bash
> 继续升级 loop/worker-loop.sh，加入 2-strike 检测：
>
> 在每轮失败后，检查 STATE.md 中最近两条的"错误摘要"：
> - 如果连续两轮的 VERIFY_FAIL stage= 相同（同一层失败），触发 2-strike：
>   echo "⚠️ 2-STRIKE：同一类错误连续 2 轮未解决"
>   echo "  建议：停止蛮力修复，先理解系统/画状态机/换策略"
>   echo "  当前策略已耗尽，升级 prompt 为：'先分析 root cause 再修'"
>
> - 2-strike 触发后，给下一轮的 CONTEXT 追加一段强制策略升级：
>   "⚠️ 前两轮在同一个地方失败了。不要继续用类似方法修。
>    请先：1. 分析为什么前两轮失败了（root cause）
>          2. 提出一个和前两轮不同思路的方案
>          3. 再动手修"
>
> - 如果 2-strike 后第三轮还是同类失败 → 直接熔断叫人：
>   echo "🛑 3-STRIKE：同类错误 3 轮，超出 agent 能力，需要人工介入"
>   exit 1
```

### Step 3.3 — 完整验证 (3 min)

```bash
# 清空之前的状态
rm -f loop/STATE.md

# 跑一个真实 bug
./loop/worker-loop.sh

# 查看排错轨迹
cat loop/STATE.md
```

**观察要点**：
- STATE.md 记录了每轮的尝试方向和失败原因
- 后续轮次的 agent 确实没有重复前面失败的方向
- 如果触发了 2-strike，prompt 升级了吗？agent 确实换了思路吗？

**关键教学时刻**：
> 讲师问："STATE.md 和 M10 的 exit-contract 是什么关系？"
> 答：同一个思想——"已尝试但失败的方案"。exit-contract 是跨会话的，STATE.md 是跨轮次的。一个让人不重复犯错，一个让 loop 不重复犯错。
>
> 追问："2-strike 和 SwarmAI 3 连挂事故的对应关系？"
> 答：事故里前 3 轮都是"增量式修症状"——每次只看到 3-4 个状态。2-strike 在第 2 轮就强制你换思路（"先画完整状态机再修"），第 4 轮才能一次成功。

**SwarmAI 对标讲解**（讲师用）：
> SwarmAI 3 连挂事故的教训直接催生了两个设计：
> 1. STATE.md（记录失败）：对应 SwarmAI `daily_activity_writer` 的"三问"格式——交付了什么？失败了什么？学到了什么？
> 2. 2-strike（强制升级策略）：对应事故里第 4 轮"被迫先画状态机"——当蛮力不行时，逼出更高层次的理解
>
> "确定能 work"与正确性负相关——事故里 3 次失败前都宣称"确定能 work"。loop 最该防的不是"单次出错"，而是"自信地、增量地、在错误模型上反复试"。STATE.md + 2-strike 就是对抗这种失败模式的工程化手段。
>
> 学员的 3-strike 直接叫人，和 SwarmAI 事故第 4 轮一样——让人来做 agent 做不了的事（画状态机、重新建模系统）。

### Done 标准
- [ ] STATE.md 每轮记录尝试方向 + 失败原因
- [ ] 下一轮 prompt 包含历史（agent 不重复已失败方向）
- [ ] 2-strike 检测生效：连续同类失败时强制升级策略
- [ ] 3-strike 熔断叫人
- [ ] STATE.md 可读——人能复盘整个排错过程
- [ ] `loop/` 目录已提交进 repo

---

## 产出清单（学员课后直接带走使用）

```
loop/
├── worker-loop.sh    # 完整 worker loop（熔断 + 记忆 + 2-strike）
└── STATE.md          # 排错轨迹（loop 运行时自动生成）
```

**课后使用指南**（一句话）：任何时候你有一个失败的测试/断言，把 `verify.sh` 的路径改成你的验证命令，把 TASK 改成你的修复目标，跑 `./loop/worker-loop.sh`——它会在刹车保护下自己修，修不好就叫你。你只需要在它成功时 review PR，或在它叫人时接手分析。

**升级路径**（课后探索）：
- L1 → L2：把 loop 接入 CI——草稿 PR 触发，CI 里自动修
- L2 → L3：监控报 bug → 自动触发 loop → 修完提 PR 等人审（M14 详谈）
- 每级升级只需要改"触发方式"和"交付方式"，loop 核心逻辑不变

---

## Lab 复盘讨论 (3 min)

1. **感受**：第一次看着 loop 自己修 bug、你不插手——什么感受？你敢让它修多复杂的 bug？（答：简单的契约违反可以放心让它修；涉及多文件重构/状态机/并发的——先理解再修，2-strike 的适用场景）

2. **经济学**：如果今天没先装熔断就放手跑——错题本 loop 两头烧钱，最坏会烧成什么样？（答：5 轮 × 每轮 ~$1 ≈ $5 很合理。但没有 MAX_ITER 的无限循环 × 每轮真调 Bedrock ≈ 灾难。M12 把真调移出主终点线正是为了这里省钱）

3. **验证信任**：你的 verify.sh 主终点线全是 mock 契约断言、没真调 Bedrock。这让 loop 跑得起又省钱。但只验 mock 不验真实识别质量——修出来的东西你敢直接合吗？（答：需要人最后跑一次统计断言/快照——"loop 修到绿 + 人验一次真" = 安全。这就是 L1 loop 的正确姿势）

4. **2-strike 的边界**：STATE.md 怎么帮 loop 在"同类修复挂了 2 次"时停下来换思路？如果你给 loop 加"连续 N 轮零进展就熔断叫人"的规则——N 该设多少？（答：N=2 或 3。SwarmAI 事故启示——第 3 次尝试相同思路成功的概率几乎为零）

5. **升级路径**：这个 L1 loop 升级到 L2（CI 触发）、L3（线上自愈）各差什么？（答：L2 差一个 webhook 触发 + PR 提交逻辑；L3 差监控接入 + 沙箱隔离 + 可观测 + 人类审批 gate。M14 展开）

---

## 与原版实验的关键改变

| 维度 | 原版 | 改进版 |
|------|------|--------|
| **层次感** | 4 步并列（准备/写 loop/熔断/记忆），无优先级 | 3 层递进：跑通→敢放→聪明，每层有明确的认知升级 |
| **体验设计** | 写完就结束 | Layer 1 "第一次放手"是震撼体验，Layer 2 验证刹车有效 |
| **判断层** | 熔断当配置写 | 2-strike 规则是核心判断——什么时候该停止蛮力、换层次想 |
| **产出复用** | 教学骨架 | worker-loop.sh 可直接用于任何"失败测试→自动修"的场景 |
| **SwarmAI 对标** | 概念引用 | 每步标注 SwarmAI 事故/设计 + 讲师可展开讲 |
| **退出码设计** | 无 | 明确退出码语义——为升级到 L2/CI 做准备 |
| **2-strike** | 复盘时提一句 | 内嵌到 loop 代码中，学员亲手实现+体验 |

---

## 讲师备注

### Layer 1 的"放手时刻"是灵魂

跑 `./loop/worker-loop.sh` 然后什么都不做、看着它一轮一轮自己修——这是 Day3 最有冲击力的 5 分钟。讲师不要在这时候讲话，让学员沉浸在"它在自己转"的体验中。

如果 bug 太简单（1 轮就修好了），可以换一个稍难的 bug（比如同时打破两条契约）。目标是让学员看到至少 2-3 轮的迭代过程——看到"失败→回灌→换方向→再试"的循环，才能理解 loop 的真正形态。

### 关于 `--dangerously-skip-permissions`

Lab 里用了这个 flag——因为 loop 是无人值守的，每轮都弹权限框就没法跑。**但必须强调**：
- 仅在隔离的练习目录使用
- 生产环境绝不可如此——应该用 `allowedTools` 配置限定 agent 能力
- 这也是 L2/L3 loop 需要额外安全基建（沙箱）的原因之一

### 如果 loop 在课堂时间内没收敛

备案：
1. 讲师准备一份预跑好的 loop 日志截屏——让学员看到"完整的 5 轮收敛过程"
2. 降低 bug 难度：只打破一条最简单的契约（比如"返回值必须是数组"——只需加个 `[]` 包装）
3. 如果网络/API 延迟导致超时：把 MAX_SECONDS 调大，或改为只运行 2 轮演示效果

### 安全提醒

- loop 涉及真实 token 消耗。**务必让学员先完成 Layer 2 熔断再长跑**（课堂 Layer 1 的 MAX_ITER=5 本身就是保护）
- 如果有学员把 MAX_ITER 改大了跑——提醒他们看 LOOP_EXIT 里的 elapsed 时间和轮数
- STATE.md 是可审计的——如果 loop 做了奇怪的事，STATE.md 能复盘整个过程
