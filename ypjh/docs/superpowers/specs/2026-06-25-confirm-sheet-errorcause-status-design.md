# 题目确认 Sheet + 错因诊断 + 错题状态机 设计文档

## 目标

将「拍照→直接保存」的粗糙流程升级为：

1. **A — 底部半屏确认 Sheet**：识别完成后弹出可编辑确认页，用户校对后保存
2. **B — 错因诊断入口**：保存后在详情页引导用户标记错误原因
3. **C — 六态状态机**：为每道错题跟踪学习生命周期

---

## 数据模型变更

### Question 新增两个字段

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `learning_status` | str (enum) | `"待分析"` | 六态学习状态 |
| `user_error_type` | str \| null | `null` | 用户确认的错误原因 |

### 六态枚举值

```
待分析 → 待订正 → 待巩固 → 待复习 → 基本掌握 → 已掌握
```

### 状态流转规则（仅正向，不自动倒退）

| 触发动作 | 状态变化 |
|---------|---------|
| 保存新题 | 自动设为 `待分析` |
| 调用 PATCH /error-type | `待分析 → 待订正` |
| 点击「我已理解，进入复习」 | `待订正 → 待巩固` |
| 点击「加入今日复习」 | `待巩固 → 待复习` |
| 复习通过（SM-2 interval 累计 ≥ 2 次） | `待复习 → 基本掌握` |
| interval_days ≥ 7 且复习通过 | `基本掌握 → 已掌握` |
| 用户手动操作「重置」 | 任意状态 → `待订正` |

用户无法手动设置状态（除重置外），所有流转由以上规则触发。

### 新增 API 端点

```
PATCH /api/v1/questions/{id}/error-type
Body: { "user_error_type": str }
Response: QuestionOut（含更新后的 learning_status）
```

约束：
- `user_error_type` 必须是枚举值之一（见下文错因列表）
- 调用后 `learning_status` 从 `待分析` 推进至 `待订正`；已是 `待订正` 或更高时不倒退，仅更新 `user_error_type`
- user_id 从 JWT 提取（R1/R22），不接受客户端传入

### QuestionOut 扩展

```python
class QuestionOut(BaseModel):
    # 现有字段 ...
    learning_status: str = "待分析"
    user_error_type: str | None = None
```

---

## 功能 A：底部半屏确认 Sheet

### 触发位置

`UploadPage.vue` — 识别成功（`status === 'high_confidence' || 'pending_review'`）后，替换现有跳转逻辑，改为打开 Sheet。

### Sheet 组件：`ConfirmSheet.vue`

放置于 `frontend/src/components/ConfirmSheet.vue`。

**布局结构：**
```
┌─────────────────────────────────┐
│         ▔▔▔ 拖拽条 ▔▔▔           │
│ "识别完成 ✓"  [置信度: 92%]      │  ← 低置信度时整行变黄色背景
│ ─────────────────────────────── │
│ 题目内容                         │
│ [textarea, 4 行, 可编辑]         │
│                                  │
│ 正确答案                         │
│ [input, 单行]                    │
│                                  │
│ 我的错误答案（选填）              │
│ [input, 单行, placeholder=留空]  │
│                                  │
│ 学科                             │
│ [select: 语文/数学/.../不确定]   │
│                                  │
│ ┌────────────────────────────┐  │
│ │       保存到错题本          │  │  ← loading 态 + 成功关闭
│ └────────────────────────────┘  │
└─────────────────────────────────┘
```

**低置信度状态（confidence < 0.7）：**
- 顶部状态行背景 `bg-yellow-50`，文字 `⚠️ 识别置信度较低，请仔细检查`
- 保存按钮文字改为「确认并保存」

**交互细节：**
- 点击遮罩层不关闭（防误触丢失编辑内容）；右上角有「×」关闭按钮
- 保存成功后：关闭 Sheet，跳转到 `/questions/{newId}?new=1`
- 用 Vue `Teleport` 挂载到 `<body>`，配合 CSS transition 滑入动画

**Props：**
```typescript
interface ConfirmSheetProps {
  visible: boolean
  candidate: RecognitionResult['candidate']  // 预填数据
}
```

**Emits：**
- `close` — 用户点 × 关闭
- `saved(question: Question)` — 保存成功

---

## 功能 B：错因诊断入口

### 触发条件

`QuestionDetailPage.vue` 挂载时检测：
- URL query 包含 `?new=1`，且
- `question.learning_status === '待分析'`

满足时在题目卡片上方渲染引导横幅。

### 引导横幅（内联，非 Sheet）

```
┌─────────────────────────────────────┐
│ 📌 标记一下你的错误原因，帮助AI优化解析  │
│                    [ 立即标记 → ]     │
└─────────────────────────────────────┘
```

点击「立即标记」后，横幅下方展开内联选择区（手风琴展开，不跳转）：

```
你认为这题出错的主要原因？

○ 知识点没掌握      ○ 概念混淆
○ 漏看题目条件      ○ 解题思路错误
○ 计算错误          ○ 粗心/手误
○ 时间不足          ○ 其他

[ 确认 ]   [ 跳过 ]
```

**错因枚举值（8个）：**
```
知识点没掌握 / 概念混淆 / 漏看题目条件 /
解题思路错误 / 计算错误 / 粗心手误 / 时间不足 / 其他
```

**「确认」：** 调用 `PATCH /questions/{id}/error-type`，成功后：
- 引导横幅消失
- AI 解析卡片 `error_analysis` 区域顶部新增「你的错因：{type}」标签（橙色）
- `learning_status` 更新为 `待订正`，底部操作栏随之变化

**「跳过」：** 仅隐藏引导横幅（不调用 API，状态不变）

### AI 解析卡片错因并列展示

```
错因分析
[用户: 计算错误]  [AI: 条件遗漏]   ← 两个标签并排
AI 诊断原因: ...
```

---

## 功能 C：状态机 UI

### QuestionListPage — 卡片状态角标

每张 `QuestionCard` 右上角添加状态点：

| 状态 | 样式 |
|------|------|
| 待分析 | `w-2 h-2 rounded-full bg-gray-300` |
| 待订正 | `w-2 h-2 rounded-full bg-orange-400` |
| 待巩固 | `w-2 h-2 rounded-full bg-blue-400` |
| 待复习 | `w-2 h-2 rounded-full bg-purple-400` |
| 基本掌握 | `w-2 h-2 rounded-full bg-green-400` |
| 已掌握 | `text-green-500 text-xs` → `✓` |

### QuestionDetailPage — 底部操作栏

固定在页面底部（`fixed bottom-0`），根据 `learning_status` 条件渲染：

| 状态 | 按钮文字 | 点击动作 |
|------|---------|---------|
| 待订正 | 我已理解，进入复习 | PATCH learning_status → 待巩固 |
| 待巩固 | 加入今日复习 | PATCH learning_status → 待复习 |
| 其他 | 不渲染 | — |

操作栏在 `待分析` 时不渲染（引导横幅已覆盖）。

新增 API：
```
PATCH /api/v1/questions/{id}/learning-status
Body: { "learning_status": str }
```
约束：只允许正向流转（后端验证），非法跳跃返回 400。

### DashboardPage — 待订正徽章

现有统计行新增：
```
待复习  12    待订正  3
```
数据来源：现有 `GET /review/stats` 扩展返回 `pending_correction_count` 字段。

---

## 文件变更清单

### 后端

| 文件 | 操作 |
|------|------|
| `backend/models/question.py` | 新增 `learning_status`、`user_error_type` 字段 |
| `backend/schemas/question.py` | `QuestionOut`、`QuestionCreate` 新增两字段 |
| `backend/api/v1/endpoints/questions.py` | 新增 `PATCH /{id}/error-type`、`PATCH /{id}/learning-status` |
| `backend/api/v1/endpoints/review.py` | `GET /review/stats` 返回新增 `pending_correction_count` |
| `backend/services/question_service.py` | 新增 `set_error_type()`、`set_learning_status()` 方法，状态流转验证 |
| `backend/tests/test_learning_status.py` | 新建，覆盖状态流转规则和非法跳跃拒绝 |
| `alembic/versions/xxxx_add_learning_status.py` | 新建迁移（或 SQLite 直接 ALTER TABLE） |

### 前端

| 文件 | 操作 |
|------|------|
| `frontend/src/components/ConfirmSheet.vue` | 新建 |
| `frontend/src/pages/UploadPage.vue` | 替换跳转逻辑为打开 ConfirmSheet |
| `frontend/src/pages/QuestionDetailPage.vue` | 错因引导横幅 + 底部操作栏 |
| `frontend/src/components/QuestionCard.vue` | 新增状态角标 |
| `frontend/src/pages/DashboardPage.vue` | 新增「待订正」计数 |
| `frontend/src/types/index.ts` | Question 新增两字段 |
| `frontend/src/api/mock/questions.mock.ts` | mock 数据新增字段 |

---

## 安全约束

- R1: 所有 PATCH 必须验证 `question.user_id == current_user.id`
- R22: `user_id` 从 JWT 提取，不接受客户端传入
- `learning_status` 枚举值后端白名单校验，非法值返回 422
- `user_error_type` 枚举值后端白名单校验（8个固定选项）
- 状态只能正向流转，非法方向返回 400 `INVALID_STATUS_TRANSITION`
