# 科目标签筛选 + 我的页面 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为错题本 App 增加科目标签筛选/分组、我的页面（个人信息+统计+设置），以及修改密码后端接口。

**Architecture:** 底部导航第 4 个 tab 改为"我的"（`/profile`），上传入口保留在 Dashboard；错题列表前端 computed 派生科目标签，不增加 API；`/profile` 新页面调现有 questions/review stats API 展示统计，修改密码新增 `PATCH /api/v1/auth/password` 接口。

**Tech Stack:** Vue 3 + TypeScript + Pinia + Tailwind CSS v3 + FastAPI + SQLAlchemy 2 async + bcrypt

## Global Constraints

- R1: 所有查询必须带 user_id 过滤（从 JWT sub 提取）
- R22: user_id 从 JWT sub 提取，拒绝客户端传入
- 新密码最少 8 位（Pydantic field_validator，同现有 RegisterRequest 规则）
- 科目标签前端计算，不新增 API
- 布局风格一致：白底卡片、primary 色、pb-20、sticky header、max-w-2xl mx-auto px-4
- IS_MOCK 分支：`import.meta.env.VITE_MOCK === 'true'`（从 `@/api/mock` 导入 `IS_MOCK`）

---

## 文件变更清单

| 操作 | 文件 | 说明 |
|------|------|------|
| 修改 | `frontend/src/components/BottomNav.vue` | 最后 tab 改为"我的 /profile" |
| 修改 | `frontend/src/router/index.ts` | 新增 `/profile` 路由 |
| 修改 | `frontend/src/pages/QuestionListPage.vue` | 加科目标签栏 + 分组渲染 |
| 新增 | `frontend/src/pages/ProfilePage.vue` | 我的页面 |
| 新增 | `frontend/src/api/endpoints/profile.ts` | changePassword API 调用 |
| 新增 | `frontend/src/api/mock/profile.mock.ts` | changePassword mock |
| 修改 | `frontend/src/api/mock/index.ts` | 导出 mockProfile、IS_MOCK |
| 修改 | `frontend/src/types/index.ts` | 新增 ProfileStats 类型 |
| 修改 | `backend/schemas/auth.py` | 新增 ChangePasswordRequest |
| 修改 | `backend/services/auth_service.py` | 新增 change_password 方法 |
| 修改 | `backend/api/v1/endpoints/auth.py` | 新增 PATCH /password 路由 |

---

### Task 1: 底部导航 + 路由（纯前端，无后端）

**Files:**
- Modify: `frontend/src/components/BottomNav.vue`
- Modify: `frontend/src/router/index.ts`

**Interfaces:**
- Produces: `/profile` 路由可访问（ProfilePage 占位页），底部导航显示"我的"

- [ ] **Step 1: 修改 BottomNav.vue**

将文件内容替换为：

```vue
<!-- frontend/src/components/BottomNav.vue -->
<script setup lang="ts">
import { useRoute } from 'vue-router'

const route = useRoute()

const tabs = [
  { to: '/dashboard', icon: '🏠', label: '首页' },
  { to: '/questions', icon: '📚', label: '错题' },
  { to: '/review',    icon: '🔄', label: '复习' },
  { to: '/profile',   icon: '👤', label: '我的' },
]

function isActive(to: string) {
  if (to === '/dashboard') return route.path === '/dashboard'
  return route.path.startsWith(to)
}
</script>

<template>
  <nav class="fixed bottom-0 left-0 right-0 z-50 bg-white border-t border-gray-200"
       style="padding-bottom: env(safe-area-inset-bottom, 0px)">
    <div class="max-w-2xl mx-auto flex">
      <RouterLink
        v-for="tab in tabs"
        :key="tab.to"
        :to="tab.to"
        class="flex-1 relative flex flex-col items-center justify-center py-2 min-h-[56px]
               transition-colors select-none"
        :class="isActive(tab.to)
          ? 'text-primary-600'
          : 'text-gray-400 hover:text-gray-600 active:text-gray-600'"
      >
        <span class="text-xl leading-none mb-0.5">{{ tab.icon }}</span>
        <span class="text-[10px] font-medium leading-none">{{ tab.label }}</span>
        <span
          v-if="isActive(tab.to)"
          class="absolute bottom-0 w-8 h-0.5 bg-primary-500 rounded-t-full"
        />
      </RouterLink>
    </div>
  </nav>
</template>
```

- [ ] **Step 2: 修改 router/index.ts，新增 /profile 路由**

在 `/review` 路由后面加一行：

```typescript
{ path: '/profile', component: () => import('@/pages/ProfilePage.vue') },
```

完整 routes 数组变为：
```typescript
routes: [
  { path: '/login', component: () => import('@/pages/LoginPage.vue'), meta: { public: true } },
  { path: '/register', component: () => import('@/pages/RegisterPage.vue'), meta: { public: true } },
  { path: '/', redirect: '/dashboard' },
  { path: '/dashboard', component: () => import('@/pages/DashboardPage.vue') },
  { path: '/upload', component: () => import('@/pages/UploadPage.vue') },
  { path: '/questions', component: () => import('@/pages/QuestionListPage.vue') },
  { path: '/questions/:id', component: () => import('@/pages/QuestionDetailPage.vue') },
  { path: '/review', component: () => import('@/pages/ReviewPage.vue') },
  { path: '/profile', component: () => import('@/pages/ProfilePage.vue') },
  { path: '/print', component: () => import('@/pages/PrintPage.vue') },
],
```

- [ ] **Step 3: 创建 ProfilePage.vue 占位页（防止路由报错）**

新建文件 `frontend/src/pages/ProfilePage.vue`，内容为：

```vue
<template>
  <div class="min-h-screen bg-gray-50 pb-20">
    <header class="bg-white border-b sticky top-0 z-10">
      <div class="max-w-2xl mx-auto px-4 py-3">
        <h2 class="font-semibold text-gray-900">我的</h2>
      </div>
    </header>
  </div>
</template>
```

- [ ] **Step 4: 手动验证**

确认底部导航第 4 个 tab 显示"👤 我的"，点击能跳转到 `/profile`，不报路由错误。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/BottomNav.vue \
        frontend/src/router/index.ts \
        frontend/src/pages/ProfilePage.vue
git commit -m "feat: bottom nav → 我的, add /profile route placeholder"
```

---

### Task 2: 科目标签筛选 + 分组（QuestionListPage）

**Files:**
- Modify: `frontend/src/pages/QuestionListPage.vue`

**Interfaces:**
- Consumes: `store.items: Question[]`（Question 有 `subject: string | null` 字段）
- Produces: 标签栏 + 分组列表（纯前端 computed，无新 API）

- [ ] **Step 1: 将 QuestionListPage.vue 替换为以下完整内容**

```vue
<!-- frontend/src/pages/QuestionListPage.vue -->
<script setup lang="ts">
import { onMounted, inject, computed, ref } from 'vue'
import { useQuestions } from '@/composables/useQuestions'
import QuestionCard from '@/components/QuestionCard.vue'
import SkeletonCard from '@/components/SkeletonCard.vue'
import type { Question } from '@/types'

const { store, fetchList, softDelete } = useQuestions()
const toast = inject<{ show: (t: string, type?: 'success'|'error'|'info') => void }>('toast')
const activeSubject = ref<string>('全部')

onMounted(() => fetchList())

async function onDelete(id: string) {
  await softDelete(id)
  toast?.show('已删除', 'success')
}

// 从题目列表提取科目标签（去重，保持出现顺序）
const subjectTabs = computed(() => {
  const seen = new Set<string>()
  const tabs: string[] = ['全部']
  for (const q of store.items) {
    const s = q.subject ?? '其他'
    if (!seen.has(s)) {
      seen.add(s)
      tabs.push(s)
    }
  }
  // 「其他」始终排最后
  const idx = tabs.indexOf('其他')
  if (idx > 1) {
    tabs.splice(idx, 1)
    tabs.push('其他')
  }
  return tabs
})

// 按当前选中科目过滤并分组
const groupedItems = computed<{ subject: string; items: Question[] }[]>(() => {
  const filtered = store.items.filter(q => {
    if (activeSubject.value === '全部') return true
    const s = q.subject ?? '其他'
    return s === activeSubject.value
  })

  if (activeSubject.value !== '全部') {
    return [{ subject: activeSubject.value, items: filtered }]
  }

  // 全部模式：按科目分组
  const map = new Map<string, Question[]>()
  for (const q of filtered) {
    const s = q.subject ?? '其他'
    if (!map.has(s)) map.set(s, [])
    map.get(s)!.push(q)
  }
  // 保持 subjectTabs 顺序（跳过"全部"）
  const groups: { subject: string; items: Question[] }[] = []
  for (const tab of subjectTabs.value.slice(1)) {
    if (map.has(tab)) groups.push({ subject: tab, items: map.get(tab)! })
  }
  return groups
})
</script>

<template>
  <div class="min-h-screen bg-gray-50 pb-20">
    <header class="bg-white border-b sticky top-0 z-10">
      <div class="max-w-2xl mx-auto px-4 py-3 flex items-center justify-between">
        <h2 class="font-semibold text-gray-900">我的错题（{{ store.total }}）</h2>
        <RouterLink to="/upload"
          class="text-sm bg-primary-500 text-white px-3 py-1.5 rounded-lg
                 hover:bg-primary-600 transition-colors">
          + 录题
        </RouterLink>
      </div>

      <!-- 科目标签栏 -->
      <div v-if="!store.loading && store.items.length > 0"
           class="max-w-2xl mx-auto px-4 pb-2 flex gap-2 overflow-x-auto
                  scrollbar-hide">
        <button
          v-for="tab in subjectTabs"
          :key="tab"
          @click="activeSubject = tab"
          class="shrink-0 px-3 py-1 rounded-full text-xs font-medium transition-colors"
          :class="activeSubject === tab
            ? 'bg-primary-500 text-white'
            : 'bg-gray-100 text-gray-600 hover:bg-gray-200'"
        >
          {{ tab }}
        </button>
      </div>
    </header>

    <main class="max-w-2xl mx-auto px-4 py-4 space-y-3">
      <!-- 加载骨架 -->
      <template v-if="store.loading">
        <SkeletonCard v-for="i in 3" :key="i" :lines="4" />
      </template>

      <!-- 空状态 -->
      <template v-else-if="store.items.length === 0">
        <div class="text-center py-16 text-gray-400">
          <div class="text-5xl mb-4">📭</div>
          <p class="font-medium">还没有错题</p>
          <RouterLink to="/upload" class="text-primary-500 text-sm mt-2 block hover:underline">
            去录第一道题 →
          </RouterLink>
        </div>
      </template>

      <!-- 分组列表 -->
      <template v-else>
        <template v-for="group in groupedItems" :key="group.subject">
          <!-- 分组标题（仅"全部"模式显示） -->
          <p v-if="activeSubject === '全部'"
             class="text-xs text-gray-400 font-medium px-1 pt-2">
            {{ group.subject }} · {{ group.items.length }}题
          </p>
          <QuestionCard
            v-for="q in group.items"
            :key="q.id"
            :question="q"
            :show-answer="false"
            @delete="onDelete"
          />
        </template>
      </template>
    </main>
  </div>
</template>
```

- [ ] **Step 2: 手动验证**

进入"错题"页面，确认：
- 标签栏正确显示各科目（如"全部 / 数学 / 英语"）
- 点击科目标签只显示该科目题目
- 点击"全部"恢复分组展示，每组有"数学 · N题"标题

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/QuestionListPage.vue
git commit -m "feat: subject tag filter and grouped list in QuestionListPage"
```

---

### Task 3: 修改密码后端接口

**Files:**
- Modify: `backend/schemas/auth.py`
- Modify: `backend/services/auth_service.py`
- Modify: `backend/api/v1/endpoints/auth.py`
- Test: `backend/tests/test_change_password.py`（新建）

**Interfaces:**
- Produces: `PATCH /api/v1/auth/password`，请求体 `{old_password, new_password}`，成功返回 `{"data": {"message": "密码已更新"}, "error": null}`

- [ ] **Step 1: 写失败测试**

新建 `backend/tests/test_change_password.py`：

```python
import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app


@pytest.fixture
async def auth_headers(async_client: AsyncClient):
    # 注册并登录，获取 token
    await async_client.post("/api/v1/auth/register",
                            json={"email": "pw@test.com", "password": "oldpass123"})
    resp = await async_client.post("/api/v1/auth/login",
                                   json={"email": "pw@test.com", "password": "oldpass123"})
    token = resp.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def async_client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_change_password_success(async_client, auth_headers):
    resp = await async_client.patch(
        "/api/v1/auth/password",
        json={"old_password": "oldpass123", "new_password": "newpass456"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["message"] == "密码已更新"


@pytest.mark.asyncio
async def test_change_password_wrong_old(async_client, auth_headers):
    resp = await async_client.patch(
        "/api/v1/auth/password",
        json={"old_password": "wrongpass", "new_password": "newpass456"},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "WRONG_PASSWORD"


@pytest.mark.asyncio
async def test_change_password_too_short(async_client, auth_headers):
    resp = await async_client.patch(
        "/api/v1/auth/password",
        json={"old_password": "oldpass123", "new_password": "short"},
        headers=auth_headers,
    )
    assert resp.status_code == 422
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
cd /workshop/ypjh && backend/.venv/bin/pytest backend/tests/test_change_password.py -v
```

预期：FAILED（路由不存在，404）

- [ ] **Step 3: 在 schemas/auth.py 新增 ChangePasswordRequest**

在文件末尾追加：

```python
class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def new_password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("新密码至少需要 8 个字符")
        return v
```

- [ ] **Step 4: 在 services/auth_service.py 新增 change_password 方法**

在 `AuthService` 类中追加（`login` 方法后）：

```python
async def change_password(
    self, session: AsyncSession, user_id: str, old_password: str, new_password: str
) -> dict:
    from sqlalchemy import select
    from backend.models.user import User
    result = await session.execute(
        select(User).where(User.id == user_id, User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()
    if user is None or not verify_password(old_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "WRONG_PASSWORD", "message": "旧密码不正确"},
        )
    user.hashed_password = hash_password(new_password)
    await session.commit()
    return {"message": "密码已更新"}
```

同时在文件顶部确认已导入 `HTTPException, status`（已有）和 `AsyncSession`（已有）。

- [ ] **Step 5: 在 endpoints/auth.py 新增 PATCH /password 路由**

在文件末尾（`me` 函数后）追加：

```python
from backend.schemas.auth import ChangePasswordRequest

@router.patch("/password", response_model=ApiResponse[dict])
async def change_password(
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[dict]:
    result = await _svc.change_password(
        session, current_user.id, body.old_password, body.new_password
    )
    return ApiResponse(data=result)
```

注意：`ChangePasswordRequest` 的 import 要加到文件顶部的 import 行：
```python
from backend.schemas.auth import AuthResponse, ChangePasswordRequest, LoginRequest, RegisterRequest, UserResponse
```

- [ ] **Step 6: 运行测试，确认通过**

```bash
cd /workshop/ypjh && backend/.venv/bin/pytest backend/tests/test_change_password.py -v
```

预期：3 tests passed

- [ ] **Step 7: Commit**

```bash
git add backend/schemas/auth.py \
        backend/services/auth_service.py \
        backend/api/v1/endpoints/auth.py \
        backend/tests/test_change_password.py
git commit -m "feat: add PATCH /auth/password endpoint with old-password verification"
```

---

### Task 4: 我的页面前端（ProfilePage）

**Files:**
- Create: `frontend/src/api/endpoints/profile.ts`
- Create: `frontend/src/api/mock/profile.mock.ts`
- Modify: `frontend/src/api/mock/index.ts`
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/pages/ProfilePage.vue`（替换 Task 1 的占位）

**Interfaces:**
- Consumes:
  - `useAuthStore().user: User | null`（`{ id: string, email: string }`）
  - `questionsApi.list(1, 0)` → `ApiResponse<QuestionList>`（取 `total`）
  - `reviewApi.stats()` → `ApiResponse<ReviewStats>`（`due_count`, `reviewed_today`）
  - `profileApi.changePassword(old, new)` → `ApiResponse<{ message: string }>`
- Produces: 完整我的页面

- [ ] **Step 1: 新增 types（ProfileStats）**

在 `frontend/src/types/index.ts` 末尾追加：

```typescript
export interface ProfileStats {
  totalQuestions: number
  dueCount: number
  reviewedToday: number
}
```

- [ ] **Step 2: 新增 profile API 端点文件**

新建 `frontend/src/api/endpoints/profile.ts`：

```typescript
import { apiClient } from '@/api/client'
import type { ApiResponse } from '@/types'

export const profileApi = {
  changePassword(old_password: string, new_password: string) {
    return apiClient.patch<ApiResponse<{ message: string }>>('/v1/auth/password', {
      old_password,
      new_password,
    })
  },
}
```

- [ ] **Step 3: 新增 profile mock**

新建 `frontend/src/api/mock/profile.mock.ts`：

```typescript
import type { ApiResponse } from '@/types'

export const mockProfile = {
  async changePassword(
    _old: string,
    _new: string,
  ): Promise<ApiResponse<{ message: string }>> {
    await new Promise(r => setTimeout(r, 400))
    // mock 永远成功（不校验旧密码）
    return { data: { message: '密码已更新' }, error: null }
  },
}
```

- [ ] **Step 4: 更新 mock/index.ts，导出 mockProfile**

将 `frontend/src/api/mock/index.ts` 替换为：

```typescript
export { mockAuth } from './auth.mock'
export { mockQuestions } from './questions.mock'
export { mockReview } from './review.mock'
export { mockPrint } from './print.mock'
export { mockProfile } from './profile.mock'

export const IS_MOCK = import.meta.env.VITE_MOCK === 'true'
```

- [ ] **Step 5: 实现完整 ProfilePage.vue**

将 `frontend/src/pages/ProfilePage.vue` 替换为：

```vue
<!-- frontend/src/pages/ProfilePage.vue -->
<script setup lang="ts">
import { ref, onMounted, computed, inject } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { IS_MOCK, mockReview, mockProfile } from '@/api/mock'
import { reviewApi } from '@/api/endpoints/review'
import { questionsApi } from '@/api/endpoints/questions'
import { profileApi } from '@/api/endpoints/profile'
import type { ProfileStats } from '@/types'

const auth = useAuthStore()
const router = useRouter()
const toast = inject<{ show: (t: string, type?: 'success'|'error'|'info') => void }>('toast')

const stats = ref<ProfileStats>({ totalQuestions: 0, dueCount: 0, reviewedToday: 0 })
const statsLoading = ref(true)

const showPwForm = ref(false)
const oldPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const pwSaving = ref(false)

// 用户名首字母
const avatarLetter = computed(() => {
  const email = auth.user?.email ?? ''
  return (email[0] ?? '?').toUpperCase()
})

onMounted(async () => {
  statsLoading.value = true
  try {
    const [listResp, statsResp] = await Promise.all([
      IS_MOCK
        ? (await import('@/api/mock')).mockQuestions.list(1, 0)
        : (await questionsApi.list(1, 0)).data,
      IS_MOCK
        ? mockReview.stats()
        : (await reviewApi.stats()).data,
    ])
    stats.value = {
      totalQuestions: listResp.data.total,
      dueCount: statsResp.data.due_count,
      reviewedToday: statsResp.data.reviewed_today,
    }
  } finally {
    statsLoading.value = false
  }
})

async function onChangePassword() {
  if (newPassword.value !== confirmPassword.value) {
    toast?.show('两次密码不一致', 'error')
    return
  }
  if (newPassword.value.length < 8) {
    toast?.show('新密码至少 8 位', 'error')
    return
  }
  pwSaving.value = true
  try {
    const resp = IS_MOCK
      ? await mockProfile.changePassword(oldPassword.value, newPassword.value)
      : (await profileApi.changePassword(oldPassword.value, newPassword.value)).data
    if (resp.error) {
      toast?.show(resp.error.message, 'error')
    } else {
      toast?.show('密码已更新', 'success')
      showPwForm.value = false
      oldPassword.value = ''
      newPassword.value = ''
      confirmPassword.value = ''
    }
  } catch {
    toast?.show('修改失败，请检查旧密码', 'error')
  } finally {
    pwSaving.value = false
  }
}

function onLogout() {
  if (window.confirm('确认退出登录？')) {
    auth.logout()
    router.push('/login')
  }
}
</script>

<template>
  <div class="min-h-screen bg-gray-50 pb-20">
    <header class="bg-white border-b sticky top-0 z-10">
      <div class="max-w-2xl mx-auto px-4 py-3">
        <h2 class="font-semibold text-gray-900">我的</h2>
      </div>
    </header>

    <main class="max-w-2xl mx-auto px-4 py-4 space-y-4">
      <!-- 个人信息卡 -->
      <div class="bg-white rounded-2xl shadow-sm p-5 flex items-center gap-4">
        <div class="w-14 h-14 rounded-full bg-primary-100 text-primary-600
                    flex items-center justify-center text-2xl font-bold select-none shrink-0">
          {{ avatarLetter }}
        </div>
        <div>
          <p class="font-semibold text-gray-900 text-base">{{ auth.user?.email?.split('@')[0] ?? '用户' }}</p>
          <p class="text-sm text-gray-400 mt-0.5">{{ auth.user?.email ?? '' }}</p>
        </div>
      </div>

      <!-- 学习统计卡 -->
      <div class="bg-white rounded-2xl shadow-sm p-5">
        <h3 class="text-sm font-medium text-gray-500 mb-3">学习统计</h3>
        <div class="grid grid-cols-2 gap-3">
          <div class="bg-gray-50 rounded-xl p-3 text-center">
            <p class="text-2xl font-bold text-gray-900">
              {{ statsLoading ? '…' : stats.totalQuestions }}
            </p>
            <p class="text-xs text-gray-400 mt-0.5">总错题数</p>
          </div>
          <div class="bg-gray-50 rounded-xl p-3 text-center">
            <p class="text-2xl font-bold text-primary-600">
              {{ statsLoading ? '…' : stats.dueCount }}
            </p>
            <p class="text-xs text-gray-400 mt-0.5">今日待复习</p>
          </div>
          <div class="bg-gray-50 rounded-xl p-3 text-center">
            <p class="text-2xl font-bold text-green-600">
              {{ statsLoading ? '…' : stats.reviewedToday }}
            </p>
            <p class="text-xs text-gray-400 mt-0.5">今日已复习</p>
          </div>
          <div class="bg-gray-50 rounded-xl p-3 text-center">
            <p class="text-2xl font-bold text-gray-300">--</p>
            <p class="text-xs text-gray-400 mt-0.5">累计复习次数</p>
          </div>
        </div>
      </div>

      <!-- 设置列表 -->
      <div class="bg-white rounded-2xl shadow-sm overflow-hidden">
        <!-- 修改密码 -->
        <button
          @click="showPwForm = !showPwForm"
          class="w-full flex items-center justify-between px-5 py-4
                 hover:bg-gray-50 transition-colors border-b border-gray-100"
        >
          <span class="text-sm font-medium text-gray-700">修改密码</span>
          <span class="text-gray-400 text-sm">{{ showPwForm ? '▲' : '▶' }}</span>
        </button>

        <!-- 修改密码内联表单 -->
        <div v-if="showPwForm" class="px-5 py-4 space-y-3 border-b border-gray-100 bg-gray-50">
          <input v-model="oldPassword" type="password" placeholder="旧密码"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm
                   focus:outline-none focus:ring-2 focus:ring-primary-400" />
          <input v-model="newPassword" type="password" placeholder="新密码（至少 8 位）"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm
                   focus:outline-none focus:ring-2 focus:ring-primary-400" />
          <input v-model="confirmPassword" type="password" placeholder="确认新密码"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm
                   focus:outline-none focus:ring-2 focus:ring-primary-400" />
          <div class="flex gap-3">
            <button @click="showPwForm = false"
              class="flex-1 py-2 border border-gray-300 rounded-lg text-sm text-gray-600 hover:bg-gray-100">
              取消
            </button>
            <button @click="onChangePassword" :disabled="pwSaving"
              class="flex-1 py-2 bg-primary-500 text-white rounded-lg text-sm font-medium
                     hover:bg-primary-600 disabled:opacity-60 transition-colors">
              {{ pwSaving ? '保存中…' : '保存' }}
            </button>
          </div>
        </div>

        <!-- 退出登录 -->
        <button
          @click="onLogout"
          class="w-full flex items-center justify-between px-5 py-4
                 hover:bg-red-50 transition-colors text-red-500"
        >
          <span class="text-sm font-medium">退出登录</span>
          <span class="text-sm">▶</span>
        </button>
      </div>
    </main>
  </div>
</template>
```

- [ ] **Step 6: 手动验证**

访问 `/profile`，确认：
1. 顶部显示用户邮件前缀和邮箱
2. 统计卡显示总错题数、今日待复习、今日已复习
3. 点击"修改密码"展开表单，填写后点保存，toast 提示"密码已更新"
4. 点击"退出登录"→ confirm → 跳转到 `/login`

- [ ] **Step 7: 重启后端，验证真实 API 修改密码**

```bash
pkill -f "backend.main:app" 2>/dev/null; sleep 2
cd /workshop/ypjh && MOCK_BEDROCK=false S3_BUCKET=wrongbook-images-851725516537 \
  backend/.venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000 >> /tmp/wrongbook-backend.log 2>&1 &
sleep 5
# 用 VITE_MOCK=false 模式在浏览器测试修改密码
```

- [ ] **Step 8: Commit**

```bash
git add frontend/src/pages/ProfilePage.vue \
        frontend/src/api/endpoints/profile.ts \
        frontend/src/api/mock/profile.mock.ts \
        frontend/src/api/mock/index.ts \
        frontend/src/types/index.ts
git commit -m "feat: ProfilePage — avatar, stats, change password, logout"
```
