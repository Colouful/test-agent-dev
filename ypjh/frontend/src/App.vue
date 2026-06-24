<!-- frontend/src/App.vue -->
<script setup lang="ts">
import { ref, provide } from 'vue'
import AppToast from '@/components/AppToast.vue'
import type { ToastMessage } from '@/components/AppToast.vue'

const toastRef = ref<{ show: (text: string, type?: ToastMessage['type']) => void } | null>(null)
provide('toast', {
  show(text: string, type: ToastMessage['type'] = 'info') {
    toastRef.value?.show(text, type)
  },
})
</script>

<template>
  <RouterView />
  <AppToast ref="toastRef" />
</template>
