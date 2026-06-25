# 科目标签筛选 + 我的页面 设计文档

## 目标

为错题本 App 增加两个功能：
1. **科目标签**：错题列表支持按科目筛选和分组展示
2. **我的页面**：个人信息、学习统计、修改密码、退出登录

## 架构概述

纯前端改动为主（科目标签无需新 API），我的页面新增一个后端接口（修改密码）。底部导航最后一个 tab 从"上传"改为"我的"，上传入口保留在 Dashboard 快捷卡。

**Tech Stack:** Vue 3 + TypeScript + Pinia + Tailwind CSS v3 + FastAPI

---

## Global Constraints

- R1: 所有查询必须带 user_id 过滤（从 JWT sub 提取，拒绝客户端传入）
- R22: user_id 从 JWT sub 提取，拒绝客户端传入
- 不新增不必要的 API 端点；能前端计算的数据不走后端
- 现有页面布局风格保持一致（白底卡片、primary 色、pb-20、sticky header）

---

## 功能一：底部导航调整

### 变更

`BottomNav.vue` 将最后一个 tab 从"上传 `/upload`"改为"我的 `/profile`"：

```
首页 /dashboard | 错题 /questions | 复习 /review | 我的 /profile
```

`/upload` 路由保留不删除；入口通过 Dashboard 现有"拍照录题"快捷卡访问。

---

## 功能二：科目标签筛选 + 分组（QuestionListPage）

### 标签栏

- 位置：固定在 header 下方，水平可滚动（`overflow-x-auto`，隐藏滚动条）
- 标签来源：从已加载题目列表中提取去重科目，前端 `computed` 计算，无需新 API
- 标签顺序：`全部`（固定第一）+ 各科目按出现顺序排列
- 无 subject 字段的题目归入`其他`分组（仅当有此类题目时显示该标签）
- 选中样式：`bg-primary-500 text-white`；未选中：`bg-gray-100 text-gray-600`

### 分组展示

- 选中`全部`：按科目分组，每组显示组标题（如 `数学 · 3题`），`其他`组置底
- 选中某科目：只显示该科目题目，不再显示分组标题
- 组标题样式：`text-xs text-gray-400 font-medium px-1 py-2`

### 数据流

```
GET /api/v1/questions
  → questions[]
  → computed subjectTabs: ['全部', '数学', '英语', '其他']
  → computed filteredGroups: { subject: Question[] }[]
  → v-for 渲染分组 + 卡片
```

---

## 功能三：我的页面（ProfilePage）

**路由：** `GET /profile`（新增，懒加载）

### 页面结构

#### 1. 个人信息卡
- 头像：取用户名首字的彩色圆形（`bg-primary-100 text-primary-600`，大写首字母）
- 用户名 + 邮箱（从 `useAuthStore().user` 读取）

#### 2. 学习统计卡（2×2 网格）
| 指标 | 数据来源 |
|------|---------|
| 总错题数 | `GET /api/v1/questions` → `total` |
| 今日待复习 | `GET /api/v1/review/stats` → `due_count` |
| 今日已复习 | `GET /api/v1/review/stats` → `reviewed_today` |
| 累计复习次数 | 暂显示"--"（当前 API 无此字段，预留位置） |

两个 API 并行请求（`Promise.all`），页面挂载时触发。

#### 3. 设置列表

**修改密码**
- 点击展开内联表单（不跳新页）：旧密码 + 新密码 + 确认新密码
- 提交调用 `PATCH /api/v1/auth/password`
- 成功后收起表单，toast 提示"密码已更新"

**退出登录**
- 点击弹出确认对话框（简单 `window.confirm` 即可）
- 确认后调 `auth.logout()`，`router.push('/login')`

---

## 功能四：修改密码后端接口

**端点：** `PATCH /api/v1/auth/password`

**请求体：**
```json
{
  "old_password": "string",
  "new_password": "string"  // 最少 8 位
}
```

**响应：**
- `200 OK`：`{"data": {"message": "密码已更新"}, "error": null}`
- `400`：旧密码错误 → `{"code": "WRONG_PASSWORD", "message": "旧密码不正确"}`
- `422`：新密码不足 8 位（Pydantic 校验）

**实现：**
1. 从 JWT 取 `user_id`（R22）
2. 查询用户记录
3. `bcrypt.verify(old_password, user.hashed_password)`，失败返回 400
4. `bcrypt.hash(new_password)` 更新数据库

---

## 文件变更清单

| 操作 | 文件 |
|------|------|
| 修改 | `frontend/src/components/BottomNav.vue` |
| 修改 | `frontend/src/router/index.ts` |
| 修改 | `frontend/src/pages/QuestionListPage.vue` |
| 新增 | `frontend/src/pages/ProfilePage.vue` |
| 新增 | `backend/api/v1/endpoints/auth.py`（新增 PATCH /password 路由） |
| 修改 | `backend/schemas/auth.py`（新增 ChangePasswordRequest schema） |
| 修改 | `backend/services/auth_service.py`（新增 change_password 方法） |
