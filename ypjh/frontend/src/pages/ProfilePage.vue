<!-- frontend/src/pages/ProfilePage.vue -->
<script setup lang="ts">
import { ref, onMounted, computed, inject } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { IS_MOCK, mockReview, mockProfile, mockQuestions } from '@/api/mock'
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
        ? mockQuestions.list(1, 0)
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
