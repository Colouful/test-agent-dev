# UI Navigation & Detail Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复错题卡片点击无反应的 Bug，新增错题详情页，添加全局底部导航栏，并对所有页面进行 UI 优化。

**Architecture:** 在 `App.vue` 引入持久化底部导航组件（`BottomNav`），仅在已登录时显示；新增 `QuestionDetailPage.vue` 与对应路由 `/questions/:id`；`QuestionCard` 绑定 `@click` 跳转详情；所有页面去掉独立返回头部，改为顶部纯标题栏，底部导航取代返回。

**Tech Stack:** Vue 3, TypeScript, Vue Router 4, Pinia, Tailwind CSS v3（primary 色系已定义）

## Global Constraints

- 主色系：`primary-500 = #1976d2`，沿用 `tailwind.config.ts` 已定义的 primary 色板
- 字体：`font-sans`（Noto Sans SC）正文，`font-serif`（Noto Serif SC）题目内容
- 底部导航 4 个 Tab：首页（`/dashboard`）/ 错题（`/questions`）/ 复习（`/review`）/ 上传（`/upload`）
- 登录页（`/login`）、注册页（`/register`）不显示底部导航
- 详情页路由：`/questions/:id`
- `QuestionCard` 点击整体跳转详情，删除按钮点击不冒泡（`@click.stop`）
- 所有页面底部加 `pb-20` 以防内容被底部导航遮挡
- 触控目标最小 44px（Apple HIG）
- 卡片 hover：`hover:shadow-md transition-shadow`；active：`active:scale-[0.98]`
- 无需新增后端接口，详情页通过已有 `questionsApi.get(id)` 获取数据
- 安全规则（不变）：R1 user_id 过滤、R22 JWT sub、R23 预签名 URL

---

## 文件结构

| 操作 | 文件 | 说明 |
|------|------|------|
| 创建 | `frontend/src/components/BottomNav.vue` | 底部导航栏组件 |
| 创建 | `frontend/src/pages/QuestionDetailPage.vue` | 错题详情页 |
| 修改 | `frontend/src/router/index.ts` | 新增 `/questions/:id` 路由 |
| 修改 | `frontend/src/App.vue` | 挂载 `BottomNav`（登录态才显示） |
| 修改 | `frontend/src/components/QuestionCard.vue` | 整体点击跳转，删除按钮 `.stop` |
| 修改 | `frontend/src/pages/DashboardPage.vue` | 去除底部 router-link 列表，优化视觉 |
| 修改 | `frontend/src/pages/QuestionListPage.vue` | 去除顶部返回，优化标题栏 |
| 修改 | `frontend/src/pages/ReviewPage.vue` | 去除顶部返回，优化 |
| 修改 | `frontend/src/pages/UploadPage.vue` | 去除顶部返回，优化 |
| 修改 | `frontend/src/pages/PrintPage.vue` | 去除顶部返回，优化 |

---

### Task 1: 底部导航组件 + 路由接入

**Files:**
- Create: `frontend/src/components/BottomNav.vue`
- Modify: `frontend/src/router/index.ts`
- Modify: `frontend/src/App.vue`

**Interfaces:**
- Produces: `<BottomNav />` 组件，供 `App.vue` 使用；`/questions/:id` 路由，供 Task 2 的详情页使用

- [ ] **Step 1: 创建 `BottomNav.vue`**

```vue
<!-- frontend/src/components/BottomNav.vue -->
<script setup lang="ts">
import { useRoute } from 'vue-router'

const route = useRoute()

const tabs = [
  { to: '/dashboard', icon: '🏠', label: '首页' },
  { to: '/questions', icon: '📚', label: '错题' },
  { to: '/review',    icon: '🔄', label: '复习' },
  { to: '/upload',    icon: '📷', label: '上传' },
]

function isActive(to: string) {
  if (to === '/dashboard') return route.path === '/dashboard'
  return route.path.startsWith(to)
}
</script>

<template>
  <nav class="fixed bottom-0 left-0 right-0 z-50 bg-white border-t border-gray-200
              safe-area-inset-bottom">
    <div class="max-w-2xl mx-auto flex">
      <RouterLink
        v-for="tab in tabs"
        :key="tab.to"
        :to="tab.to"
        class="flex-1 flex flex-col items-center justify-center py-2 min-h-[56px]
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

- [ ] **Step 2: 修改 `router/index.ts`，新增详情路由**

```typescript
import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login',    component: () => import('@/pages/LoginPage.vue'),         meta: { public: true } },
    { path: '/register', component: () => import('@/pages/RegisterPage.vue'),      meta: { public: true } },
    { path: '/',         redirect: '/dashboard' },
    { path: '/dashboard',    component: () => import('@/pages/DashboardPage.vue') },
    { path: '/upload',       component: () => import('@/pages/UploadPage.vue') },
    { path: '/questions',    component: () => import('@/pages/QuestionListPage.vue') },
    { path: '/questions/:id',component: () => import('@/pages/QuestionDetailPage.vue') },
    { path: '/review',       component: () => import('@/pages/ReviewPage.vue') },
    { path: '/print',        component: () => import('@/pages/PrintPage.vue') },
  ],
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (!to.meta.public && !auth.token) {
    return '/login'
  }
})

export default router
```

- [ ] **Step 3: 修改 `App.vue`，挂载 BottomNav**

```vue
<!-- frontend/src/App.vue -->
<script setup lang="ts">
import { ref, provide, computed } from 'vue'
import { useRoute } from 'vue-router'
import AppToast from '@/components/AppToast.vue'
import BottomNav from '@/components/BottomNav.vue'
import { useAuthStore } from '@/stores/auth'
import type { ToastMessage } from '@/components/AppToast.vue'

const toastRef = ref<{ show: (text: string, type?: ToastMessage['type']) => void } | null>(null)
provide('toast', {
  show(text: string, type: ToastMessage['type'] = 'info') {
    toastRef.value?.show(text, type)
  },
})

const route = useRoute()
const auth = useAuthStore()
const showNav = computed(() =>
  auth.token && !['login', 'register'].includes(String(route.name ?? ''))
  && !['/login', '/register'].includes(route.path)
)
</script>

<template>
  <RouterView />
  <BottomNav v-if="showNav" />
  <AppToast ref="toastRef" />
</template>
```

- [ ] **Step 4: 验证底部导航渲染**

```bash
cd /workshop/ypjh/frontend
npm run type-check
```

期望：无类型错误。

- [ ] **Step 5: Commit**

```bash
cd /workshop/ypjh/frontend
git add src/components/BottomNav.vue src/router/index.ts src/App.vue
git commit -m "feat: add BottomNav component and /questions/:id route"
```

---

### Task 2: 错题详情页（QuestionDetailPage）

**Files:**
- Create: `frontend/src/pages/QuestionDetailPage.vue`

**Interfaces:**
- Consumes: `questionsApi.get(id)` from `src/api/endpoints/questions.ts`（已有）；`Question` type from `src/types/index.ts`（已有）
- Produces: `/questions/:id` 页面，Task 3 中的 `QuestionCard` 点击跳转目标

- [ ] **Step 1: 创建 `QuestionDetailPage.vue`**

```vue
<!-- frontend/src/pages/QuestionDetailPage.vue -->
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { IS_MOCK, mockQuestions } from '@/api/mock'
import { questionsApi } from '@/api/endpoints/questions'
import type { Question } from '@/types'

const route = useRoute()
const question = ref<Question | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)

onMounted(async () => {
  try {
    const id = route.params.id as string
    if (IS_MOCK) {
      const resp = await mockQuestions.get(id)
      question.value = resp.data
    } else {
      const resp = await questionsApi.get(id)
      question.value = resp.data.data
    }
  } catch {
    error.value = '加载失败，请返回重试'
  } finally {
    loading.value = false
  }
})

const TYPE_LABELS: Record<string, string> = {
  multiple_choice: '选择题',
  fill: '填空题',
  short_answer: '简答题',
  calculation: '计算题',
}
</script>

<template>
  <div class="min-h-screen bg-gray-50 pb-20">
    <!-- 顶部标题栏 -->
    <header class="bg-white border-b sticky top-0 z-10">
      <div class="max-w-2xl mx-auto px-4 py-3 flex items-center gap-3">
        <button @click="$router.back()" class="text-gray-400 hover:text-gray-600 transition-colors">
          ←
        </button>
        <h2 class="font-semibold text-gray-900">错题详情</h2>
      </div>
    </header>

    <main class="max-w-2xl mx-auto px-4 py-4 space-y-4">
      <!-- 加载中 -->
      <div v-if="loading" class="space-y-3">
        <div class="h-6 bg-gray-200 rounded animate-pulse w-1/3"></div>
        <div class="h-32 bg-gray-200 rounded animate-pulse"></div>
        <div class="h-20 bg-gray-200 rounded animate-pulse"></div>
      </div>

      <!-- 加载失败 -->
      <div v-else-if="error" class="text-center py-16 text-gray-400">
        <div class="text-4xl mb-3">⚠️</div>
        <p>{{ error }}</p>
      </div>

      <!-- 内容 -->
      <template v-else-if="question">
        <!-- 标签行 -->
        <div class="flex flex-wrap gap-2">
          <span v-if="question.subject"
            class="text-xs px-2 py-0.5 rounded-full bg-blue-50 text-blue-600 font-medium">
            {{ question.subject }}
          </span>
          <span v-if="question.question_type && TYPE_LABELS[question.question_type]"
            class="text-xs px-2 py-0.5 rounded-full bg-purple-50 text-purple-600 font-medium">
            {{ TYPE_LABELS[question.question_type] }}
          </span>
          <span :class="[
            'text-xs px-2 py-0.5 rounded-full font-medium',
            question.status === 'confirmed'
              ? 'bg-green-50 text-green-600'
              : 'bg-yellow-50 text-yellow-600'
          ]">
            {{ question.status === 'confirmed' ? '已确认' : '待确认' }}
          </span>
        </div>

        <!-- 图片 -->
        <div v-if="question.image_url" class="bg-white rounded-2xl overflow-hidden shadow-sm">
          <img :src="question.image_url" alt="题目图片"
            class="w-full object-contain bg-gray-50 max-h-72" loading="lazy">
        </div>

        <!-- 题目内容 -->
        <div class="bg-white rounded-2xl shadow-sm p-5">
          <p class="text-xs text-gray-400 mb-2">题目内容</p>
          <p class="font-serif text-gray-800 text-base leading-relaxed whitespace-pre-wrap">
            {{ question.content }}
          </p>
        </div>

        <!-- 答案区 -->
        <div class="bg-white rounded-2xl shadow-sm p-5 space-y-4">
          <div>
            <p class="text-xs text-gray-400 mb-1.5">正确答案</p>
            <p class="text-green-700 font-medium leading-relaxed">{{ question.correct_answer }}</p>
          </div>
          <div v-if="question.wrong_answer" class="border-t border-gray-100 pt-4">
            <p class="text-xs text-gray-400 mb-1.5">我的错误</p>
            <p class="text-red-500 leading-relaxed">{{ question.wrong_answer }}</p>
          </div>
          <div v-if="question.note" class="border-t border-gray-100 pt-4">
            <p class="text-xs text-gray-400 mb-1.5">笔记</p>
            <p class="text-gray-600 italic leading-relaxed">{{ question.note }}</p>
          </div>
        </div>

        <!-- 统计信息 -->
        <div class="bg-white rounded-2xl shadow-sm p-5">
          <p class="text-xs text-gray-400 mb-3">复习记录</p>
          <div class="grid grid-cols-3 gap-4 text-center">
            <div>
              <p class="text-xl font-bold text-gray-800">{{ question.review_count }}</p>
              <p class="text-xs text-gray-400 mt-0.5">复习次数</p>
            </div>
            <div>
              <p class="text-xl font-bold text-gray-800">{{ question.interval_days }}</p>
              <p class="text-xs text-gray-400 mt-0.5">复习间隔(天)</p>
            </div>
            <div>
              <p class="text-xl font-bold text-gray-800">{{ question.ease_factor.toFixed(1) }}</p>
              <p class="text-xs text-gray-400 mt-0.5">难度系数</p>
            </div>
          </div>
        </div>
      </template>
    </main>
  </div>
</template>
```

- [ ] **Step 2: 在 mock 层添加 `get(id)` 支持**

打开 `frontend/src/api/mock/questions.mock.ts`，检查是否已有 `get` 方法。若无，在 `mockQuestions` 对象中添加：

```typescript
// 在 mockQuestions 对象中添加（放在 list 方法之后）：
async get(id: string) {
  await delay(200)
  const item = MOCK_QUESTIONS.find(q => q.id === id)
  if (!item) throw new Error('not found')
  return { data: item }
},
```

- [ ] **Step 3: 类型检查**

```bash
cd /workshop/ypjh/frontend
npm run type-check
```

期望：无类型错误。

- [ ] **Step 4: Commit**

```bash
git add src/pages/QuestionDetailPage.vue src/api/mock/questions.mock.ts
git commit -m "feat: add QuestionDetailPage with question stats and answer display"
```

---

### Task 3: 修复 QuestionCard 点击跳转

**Files:**
- Modify: `frontend/src/components/QuestionCard.vue`

**Interfaces:**
- Consumes: `/questions/:id` 路由（Task 1 产出）

- [ ] **Step 1: 修改 `QuestionCard.vue`，整体点击跳转，删除按钮阻止冒泡**

完整替换文件内容：

```vue
<!-- frontend/src/components/QuestionCard.vue -->
<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useKatex } from '@/composables/useKatex'
import type { Question } from '@/types'

const props = defineProps<{ question: Question; showAnswer?: boolean }>()
defineEmits<{ delete: [id: string] }>()

const router = useRouter()
const container = ref<HTMLElement | null>(null)
useKatex(container)

function goToDetail() {
  router.push(`/questions/${props.question.id}`)
}
</script>

<template>
  <div
    ref="container"
    @click="goToDetail"
    class="bg-white rounded-xl shadow-sm border border-gray-100 p-5
           hover:shadow-md hover:border-primary-200 transition-all cursor-pointer
           active:scale-[0.98]"
  >
    <div class="flex items-center justify-between mb-3">
      <div class="flex gap-2">
        <span v-if="question.subject"
          class="text-xs px-2 py-0.5 rounded-full bg-blue-50 text-blue-600 font-medium">
          {{ question.subject }}
        </span>
        <span :class="[
          'text-xs px-2 py-0.5 rounded-full font-medium',
          question.status === 'confirmed' ? 'bg-green-50 text-green-600' : 'bg-yellow-50 text-yellow-600'
        ]">
          {{ question.status === 'confirmed' ? '已确认' : '待确认' }}
        </span>
      </div>
      <button
        @click.stop="$emit('delete', question.id)"
        class="text-gray-300 hover:text-red-400 transition-colors text-xs px-2 py-1 -mr-1"
      >
        删除
      </button>
    </div>

    <div v-if="question.image_url" class="mb-3">
      <img :src="question.image_url" alt="题目图片"
        class="max-w-full rounded-lg border border-gray-100" loading="lazy">
    </div>

    <p class="font-serif text-gray-800 text-base leading-relaxed mb-3 whitespace-pre-wrap line-clamp-3">
      {{ question.content }}
    </p>

    <template v-if="showAnswer !== false">
      <div class="border-t border-dashed border-gray-200 pt-3 mt-3 space-y-2">
        <div>
          <p class="text-xs text-gray-400 mb-1">正确答案</p>
          <p class="text-sm text-green-700 font-medium">{{ question.correct_answer }}</p>
        </div>
        <div v-if="question.wrong_answer">
          <p class="text-xs text-gray-400 mb-1">我的错误</p>
          <p class="text-sm text-red-600">{{ question.wrong_answer }}</p>
        </div>
        <div v-if="question.note">
          <p class="text-xs text-gray-400 mb-1">笔记</p>
          <p class="text-sm text-gray-600 italic">{{ question.note }}</p>
        </div>
      </div>
    </template>

    <div class="mt-3 flex items-center justify-end">
      <span class="text-xs text-gray-300">查看详情 →</span>
    </div>
  </div>
</template>
```

- [ ] **Step 2: 类型检查**

```bash
cd /workshop/ypjh/frontend
npm run type-check
```

期望：无类型错误。

- [ ] **Step 3: Commit**

```bash
git add src/components/QuestionCard.vue
git commit -m "fix: QuestionCard click navigates to detail page, delete stops propagation"
```

---

### Task 4: 所有页面 UI 优化（去返回按钮，加 pb-20，优化视觉）

**Files:**
- Modify: `frontend/src/pages/DashboardPage.vue`
- Modify: `frontend/src/pages/QuestionListPage.vue`
- Modify: `frontend/src/pages/ReviewPage.vue`
- Modify: `frontend/src/pages/UploadPage.vue`
- Modify: `frontend/src/pages/PrintPage.vue`

**Interfaces:**
- Consumes: `BottomNav`（Task 1 产出，已由 App.vue 全局挂载）

**核心改动原则：**
- 所有页面根 `div` 添加 `pb-20`（防被底部导航遮挡）
- 顶部 header 去掉「← 返回」链接（底部导航已承担导航职责）；`DashboardPage` 顶部改为纯标题+退出按钮
- `DashboardPage` 去掉底部功能入口 grid（底部导航已覆盖），保留今日统计卡

- [ ] **Step 1: 更新 `DashboardPage.vue`**

```vue
<!-- frontend/src/pages/DashboardPage.vue -->
<script setup lang="ts">
import { onMounted } from 'vue'
import { useReview } from '@/composables/useReview'
import { useAuth } from '@/composables/useAuth'

const { store: reviewStore, fetchStats } = useReview()
const { logout } = useAuth()

onMounted(fetchStats)
</script>

<template>
  <div class="min-h-screen bg-gray-50 pb-20">
    <header class="bg-white border-b border-gray-200 sticky top-0 z-10">
      <div class="max-w-2xl mx-auto px-4 py-3 flex items-center justify-between">
        <h1 class="text-lg font-bold text-gray-900">📝 错题本</h1>
        <button @click="logout" class="text-sm text-gray-400 hover:text-gray-600">退出</button>
      </div>
    </header>

    <main class="max-w-2xl mx-auto px-4 py-6 space-y-5">
      <!-- 复习状态卡 -->
      <div class="bg-gradient-to-br from-primary-500 to-primary-700 rounded-2xl p-6 text-white shadow-md">
        <p class="text-sm opacity-80 mb-1">今日待复习</p>
        <p class="text-5xl font-bold mb-4">{{ reviewStore.stats.due_count }}</p>
        <div class="flex items-center gap-4 text-sm opacity-80">
          <span>今日已完成 <strong class="opacity-100">{{ reviewStore.stats.reviewed_today }}</strong> 题</span>
        </div>
        <RouterLink v-if="reviewStore.stats.due_count > 0" to="/review"
          class="mt-5 inline-flex items-center gap-1 bg-white text-primary-600 px-5 py-2.5
                 rounded-xl text-sm font-semibold hover:bg-primary-50 transition-colors shadow-sm">
          立即复习 →
        </RouterLink>
        <p v-else class="mt-4 text-sm opacity-70">今日无待复习，保持！💪</p>
      </div>

      <!-- 快捷统计 -->
      <div class="grid grid-cols-2 gap-3">
        <RouterLink to="/questions"
          class="bg-white rounded-2xl p-5 shadow-sm border border-gray-100
                 hover:shadow-md hover:border-primary-200 transition-all active:scale-[0.98]">
          <div class="text-3xl mb-2">📚</div>
          <p class="font-semibold text-gray-900">我的错题</p>
          <p class="text-xs text-gray-400 mt-1">浏览和管理所有错题</p>
        </RouterLink>
        <RouterLink to="/upload"
          class="bg-white rounded-2xl p-5 shadow-sm border border-gray-100
                 hover:shadow-md hover:border-primary-200 transition-all active:scale-[0.98]">
          <div class="text-3xl mb-2">📷</div>
          <p class="font-semibold text-gray-900">拍照录题</p>
          <p class="text-xs text-gray-400 mt-1">AI 自动识别题目</p>
        </RouterLink>
        <RouterLink to="/review"
          class="bg-white rounded-2xl p-5 shadow-sm border border-gray-100
                 hover:shadow-md hover:border-primary-200 transition-all active:scale-[0.98]">
          <div class="text-3xl mb-2">🔄</div>
          <p class="font-semibold text-gray-900">开始复习</p>
          <p class="text-xs text-gray-400 mt-1">SM-2 智能间隔复习</p>
        </RouterLink>
        <RouterLink to="/print"
          class="bg-white rounded-2xl p-5 shadow-sm border border-gray-100
                 hover:shadow-md hover:border-primary-200 transition-all active:scale-[0.98]">
          <div class="text-3xl mb-2">🖨️</div>
          <p class="font-semibold text-gray-900">打印题目</p>
          <p class="text-xs text-gray-400 mt-1">生成 PDF 打印预览</p>
        </RouterLink>
      </div>
    </main>
  </div>
</template>
```

- [ ] **Step 2: 更新 `QuestionListPage.vue`**

```vue
<!-- frontend/src/pages/QuestionListPage.vue -->
<script setup lang="ts">
import { onMounted, inject } from 'vue'
import { useQuestions } from '@/composables/useQuestions'
import QuestionCard from '@/components/QuestionCard.vue'
import SkeletonCard from '@/components/SkeletonCard.vue'

const { store, fetchList, softDelete } = useQuestions()
const toast = inject<{ show: (t: string, type?: 'success'|'error'|'info') => void }>('toast')

onMounted(() => fetchList())

async function onDelete(id: string) {
  await softDelete(id)
  toast?.show('已删除', 'success')
}
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
    </header>

    <main class="max-w-2xl mx-auto px-4 py-4 space-y-3">
      <template v-if="store.loading">
        <SkeletonCard v-for="i in 3" :key="i" :lines="4" />
      </template>

      <template v-else-if="store.items.length === 0">
        <div class="text-center py-16 text-gray-400">
          <div class="text-5xl mb-4">📭</div>
          <p class="font-medium">还没有错题</p>
          <RouterLink to="/upload" class="text-primary-500 text-sm mt-2 block hover:underline">
            去录第一道题 →
          </RouterLink>
        </div>
      </template>

      <template v-else>
        <QuestionCard
          v-for="q in store.items"
          :key="q.id"
          :question="q"
          :show-answer="false"
          @delete="onDelete"
        />
      </template>
    </main>
  </div>
</template>
```

> 注意：列表页传 `:show-answer="false"`，卡片只显示题目内容，答案在详情页查看。

- [ ] **Step 3: 更新 `ReviewPage.vue`（去掉返回链接，加 pb-20）**

只修改两处：
1. 根 `div` 的 class 从 `"min-h-screen bg-gray-50 flex flex-col"` 改为 `"min-h-screen bg-gray-50 flex flex-col pb-20"`
2. header 内的 `<RouterLink to="/dashboard" class="text-gray-400">← 返回</RouterLink>` 整行删除，替换为空的占位 `<div></div>`（保持 justify-between 布局）

完整 header 部分：

```html
<header class="bg-white border-b sticky top-0 z-10">
  <div class="max-w-2xl mx-auto px-4 py-3 flex items-center justify-between">
    <h2 class="font-semibold text-gray-900">每日复习</h2>
    <p class="text-sm text-gray-500">
      {{ store.currentIndex }}/{{ store.queue.length }}
    </p>
  </div>
</header>
```

- [ ] **Step 4: 更新 `UploadPage.vue`（去掉返回链接，加 pb-20）**

根 `div` 加 `pb-20`，header 改为：

```html
<header class="bg-white border-b sticky top-0 z-10">
  <div class="max-w-2xl mx-auto px-4 py-3">
    <h2 class="font-semibold text-gray-900">拍照录题</h2>
  </div>
</header>
```

- [ ] **Step 5: 更新 `PrintPage.vue`（去掉返回链接，加 pb-20）**

根 `div` 加 `pb-20`，header 改为：

```html
<header class="bg-white border-b sticky top-0 z-10">
  <div class="max-w-2xl mx-auto px-4 py-3 flex items-center justify-between">
    <h2 class="font-semibold text-gray-900">打印设置</h2>
    <span class="text-sm text-gray-400">已选 {{ selected.size }} 题</span>
  </div>
</header>
```

- [ ] **Step 6: 类型检查 + 构建**

```bash
cd /workshop/ypjh/frontend
npm run type-check && npm run build
```

期望：无错误，`dist/` 生成成功。

- [ ] **Step 7: Commit**

```bash
git add src/pages/DashboardPage.vue src/pages/QuestionListPage.vue \
        src/pages/ReviewPage.vue src/pages/UploadPage.vue src/pages/PrintPage.vue
git commit -m "feat: ui overhaul — bottom nav padding, remove back links, polish pages"
```

---

### Task 5: 端到端验证 + 部署

**Files:**
- 无新增文件，重启服务并验证

- [ ] **Step 1: 前端构建**

```bash
cd /workshop/ypjh/frontend
npm run build
```

期望：`dist/` 生成，无 error。

- [ ] **Step 2: 重启前端静态服务器**

```bash
kill $(pgrep -f "serve-frontend.js") 2>/dev/null
node /workshop/ypjh/serve-frontend.js > /tmp/wrongbook-frontend.log 2>&1 &
echo "Frontend PID: $!"
sleep 2
curl -s http://localhost:3000/ | grep -o '<title>.*</title>'
```

期望：`<title>错题本</title>`

- [ ] **Step 3: 验证后端仍在运行**

```bash
curl -s http://localhost:8000/api/v1/auth/login \
  -X POST -H "Content-Type: application/json" \
  -d '{"email":"alice@test.com","password":"password123"}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('OK' if d['data']['access_token'] else 'FAIL')"
```

期望：`OK`

- [ ] **Step 4: Commit 最终状态**

```bash
cd /workshop/ypjh
git add -A
git status  # 确认无意外文件
git commit -m "chore: rebuild dist after UI overhaul"
```

- [ ] **Step 5: 公网验证清单**

在浏览器打开 `https://dp2xub6x3xhh2.cloudfront.net` 并手动验证：

| 验证项 | 期望结果 |
|--------|---------|
| 底部导航栏显示 | ✅ 首页/错题/复习/上传 4 个 Tab |
| 点击底部「错题」Tab | ✅ 跳转到 `/questions` |
| 错题列表中点击卡片 | ✅ 跳转到 `/questions/:id` 详情页 |
| 详情页显示题目内容、答案、复习记录 | ✅ |
| 详情页「←」返回正常 | ✅ |
| 登录页不显示底部导航 | ✅ |
| 复习页/上传页顶部无返回按钮 | ✅ |
