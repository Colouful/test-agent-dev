# 架构原则（Architecture Rules）

> 来自 M7 单向门评审。这些决策改回来代价极大，用 Fitness Function 自动守护。

## ARCH-1 [MUST] 题目内容必须结构化存储

**原则**：`Question` 实体的内容字段必须是结构化字段（`content`, `correct_answer`, `wrong_answer` 等分字段），禁止将识别结果存为单一裸字符串（如 `raw_text = "整段识别文字"`）。

**单向门理由**：裸字符串入库后，所有后续功能（筛选/复习/打印）都要重新解析，历史数据无法自动迁移。

**自动检测**：`ci/arch-check.sh` — ARCH_FAIL 亮红灯。

---

## ARCH-2 [MUST] confidence_score 字段强制存储

**原则**：每条入库的 `Question` 记录必须有 `confidence_score`（float，不得为 NULL）。识别置信度是不可回溯的元数据，不存则永久丢失。

**单向门理由**：Bedrock 调用是无状态的，结果不保存。如果入库时不存置信度，后续无法按识别质量过滤，也无法分析模型准确率。

**自动检测**：`ci/arch-check.sh` 模式4 — 检测 `confidence_score: float | None` 或 `confidence_score=None` 写法，出现则 ARCH_FAIL。（当前已实现，见 arch-check.sh 模式4。）

---

## ARCH-3 [MUST] user_id 隔离贯穿所有数据操作

**原则**：`Question`、`ReviewRecord` 等用户数据表，所有 SELECT/UPDATE/DELETE 必须带 `WHERE user_id = :current_user_id`。禁止仅凭资源 ID 操作数据（BOLA 漏洞）。

**单向门理由**：数据一旦混合存储且有访问记录，隔离迁移时存在数据泄漏风险，且所有历史查询都要改写。

**自动检测**：`ci/arch-check.sh` 模式5 — 检测 `repositories/` 下的查询函数是否缺少 `user_id` 参数。缺失则 ARCH_FAIL。（当前已实现，见 arch-check.sh 模式5。）

---

## 双向门（不需要护栏，灵活调整）

- **DB 实现**（SQLite ↔ DynamoDB）：Repository 层抽象，切换代价可控
- **复习算法**（SM-2 ↔ 其他算法）：封装在 `review_service.py`，数据字段通用
- **UI 组件库**（Element Plus ↔ Tailwind 裸组件）：样式层，不影响数据/业务
