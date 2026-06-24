<!-- frontend/src/components/AppToast.vue -->
<script setup lang="ts">
import { ref } from 'vue'

export interface ToastMessage { id: number; type: 'success' | 'error' | 'info'; text: string }

const messages = ref<ToastMessage[]>([])
let _id = 0

function show(text: string, type: ToastMessage['type'] = 'info') {
  const id = ++_id
  messages.value.push({ id, type, text })
  setTimeout(() => { messages.value = messages.value.filter(m => m.id !== id) }, 3000)
}

defineExpose({ show })
</script>

<template>
  <div class="fixed bottom-4 right-4 z-50 flex flex-col gap-2 items-end">
    <TransitionGroup name="toast">
      <div v-for="msg in messages" :key="msg.id"
        :class="[
          'px-4 py-3 rounded-lg shadow-lg text-sm text-white max-w-xs',
          msg.type === 'success' ? 'bg-green-600' :
          msg.type === 'error'   ? 'bg-red-600'   : 'bg-gray-700'
        ]">
        {{ msg.text }}
      </div>
    </TransitionGroup>
  </div>
</template>

<style scoped>
.toast-enter-active { transition: all .25s ease-out; }
.toast-leave-active { transition: all .2s ease-in; }
.toast-enter-from, .toast-leave-to { opacity: 0; transform: translateY(8px); }
</style>
