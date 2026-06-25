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
