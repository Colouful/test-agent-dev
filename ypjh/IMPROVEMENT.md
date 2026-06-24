# IMPROVEMENT.md — 踩过的坑与历史教训

> 这里记录的不是规则，而是**故事**。每个条目都是"我们试过 X，因为 Y 失败，所以现在做 Z"。
> Agent 读完这个文件，应该能避免在已知雷区重复踩坑。

---

## 坑 1：AI 返回空对象，被当成高置信度入库

**发生了什么**：Bedrock 识别反光图片时返回 `{}` 空 JSON 对象。`confidence` 字段不存在，代码用 `result.get('confidence', 1.0)` 兜底，于是空识别结果以"满置信度"直接入库。

**为什么会犯这个错**：写代码时直觉是"字段缺失给个默认值"，1.0 看起来是合理的"乐观默认"。但 AI 返回缺失字段的含义恰恰相反——是"我不确定"，而不是"我很确定"。

**现在的做法**：`confidence` 缺失强制置 0.0，触发 `pending_review` 状态（R2）。`arch-check.sh` 模式4 会自动检测这个反模式。

---

## 坑 2：空内容字段触发 schema 校验失败，返回 error 而非降级

**发生了什么**：图片完全无法识别时，Bedrock 返回 `content: ""`。Pydantic schema 设了 `min_length=1`，直接抛 `ValidationError`，用户看到的是"格式异常"错误，而不是"请手动填写"的提示。

**为什么会犯这个错**：schema 校验放在最前面是正确的，但没有区分"外部输入校验"（应该报错）和"AI 输出降级"（应该兜底）这两种场景。

**现在的做法**：service 层在 schema 校验前，对空 `content`/`correct_answer` 用占位符 `"（识别内容为空）"` 替换，保证 schema 通过，同时 `confidence=0.0` 触发 `pending_review`（R9）。占位符格式固定，不得自创其他格式。

---

## 坑 3：`set -e` 与 `grep` 在 CI 脚本里的冲突

**发生了什么**：`ci/arch-check.sh` 加了 `set -euo pipefail`，当 `grep` 没找到匹配时退出码为 1，脚本直接中止，没有输出任何结果。CI 报"脚本异常退出"，开发者以为是脚本 bug，实际是 grep 正常运行但没有匹配。

**为什么会犯这个错**：`set -e` 的直觉是"遇到错误就停"，但 `grep` 找不到匹配是正常业务结果，不是错误。

**现在的做法**：移除 `-e`，改用 `set -uo pipefail`；所有 `grep` 调用后加 `|| true`，结果存入中间变量再判断。

---

## 坑 4：`arch-check.sh` 模式2 最初是警告，导致违规代码悄悄进入主分支

**发生了什么**：裸字符串检测（ARCH-1）最初只打印警告，不计入 `VIOLATIONS`。有一次 commit 里出现了裸字符串，CI 打印了警告但通过了，代码合入主分支。三天后才在 code review 里发现。

**为什么会犯这个错**：警告比失败"温和"，当时觉得先做警告再升级。但 Agent 写代码时不会主动看 CI 警告日志，只看"通过/失败"。

**现在的做法**：模式2 从 `ARCH_WARN` 升级为 `ARCH_FAIL`，计入 `VIOLATIONS`。任何 ARCH 违规 CI 直接失败。

---

## 坑 5：`verify.sh` 在 `recognize()` 签名变更后悄悄过时

**发生了什么**：`recognition_service.py` 的 `recognize()` 方法加了 `user_id` 参数（R1 要求），但 `ci/verify.sh` 里的 heredoc 测试代码调的是旧签名 `.recognize(b"fake-bytes")`，没有更新。CI 结构断言通过，契约断言通过，但实际调用会 TypeError。

**为什么会犯这个错**：`verify.sh` 里有 6 处调用点，Edit 工具的 `replace_all=true` 只匹配了其中 3 处（变量名不同：`svc` vs `svc_blurry` vs `svc_clear`），剩余 3 处静默跳过。

**现在的做法**：修改函数签名后，必须手动检查 `verify.sh` 和测试文件中的所有调用点，不能依赖 `replace_all` 全量替换（变量名不同时会漏）。

---

## 已放弃的方案

### Event Sourcing 式的识别历史

曾考虑把每次识别都作为独立事件存储，通过事件溯源重建当前状态。放弃原因：对于错题本这种个人工具，事件溯源引入的复杂度远超收益。现在的做法是：重复识别时旧记录标 `superseded`，保留历史但不做完整事件链（R14）。

### 异步识别队列（SQS）

MVP 阶段评估过用 SQS 做异步识别任务队列（参考 rules-example 的架构）。放弃原因：P95 识别时延 < 8s，同步 HTTP 完全可以承担；引入队列需要额外的 Lambda consumer、死信队列、状态轮询接口，基础设施复杂度翻倍。升级条件已记录在 `spec/recognize/design.md` 判断4：当并发识别 > 50 req/min 时再升级。

### 物理删除题目记录

最初 DELETE 端点设计为 `204 + 物理删除`。改为软删除（R21）的原因：用户删错后无法恢复；S3 原图和复习历史形成孤儿数据；审计时数据已消失。

---

## 当前已知技术债

| 债务 | 影响 | 上线前必须修复？ |
|------|------|----------------|
| 数学公式存纯文本（MVP 降级） | 数学题公式显示为 `1/2` 而非 `½`，渲染不美观但不影响理解 | 是（R13，KaTeX 上线前必须接入） |
| Magic Bytes 校验未实现 | 目前只有 MIME type 检查，文件类型校验不完整（R16） | 是（安全问题，上线前必须修复） |
| Prompt 硬编码在 service 层 | `recognition_service.py` 中 Bedrock prompt 是字符串常量，调优需改代码（R24） | 是（提取到 `prompts/` 目录） |
| 预签名 URL 未实现 | API 响应目前直接返回 `image_key`，前端无法展示图片（R23） | 是（图片功能核心） |
