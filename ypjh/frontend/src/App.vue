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
