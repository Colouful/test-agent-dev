<!-- frontend/src/components/ReviewScoreButtons.vue -->
<script setup lang="ts">
defineProps<{ disabled?: boolean }>()
defineEmits<{ score: [n: number] }>()

const SCORES = [
  { score: 1, label: '完全不会', color: 'bg-red-100 text-red-700 hover:bg-red-200 border-red-200' },
  { score: 2, label: '模糊', color: 'bg-orange-100 text-orange-700 hover:bg-orange-200 border-orange-200' },
  { score: 3, label: '想起来了', color: 'bg-yellow-100 text-yellow-700 hover:bg-yellow-200 border-yellow-200' },
  { score: 4, label: '记得', color: 'bg-blue-100 text-blue-700 hover:bg-blue-200 border-blue-200' },
  { score: 5, label: '完全掌握', color: 'bg-green-100 text-green-700 hover:bg-green-200 border-green-200' },
]
</script>

<template>
  <div class="flex gap-2 flex-wrap justify-center">
    <button v-for="s in SCORES" :key="s.score"
      :disabled="disabled"
      :class="['px-4 py-2 rounded-lg border text-sm font-medium transition-all',
               'focus:outline-none focus:ring-2 focus:ring-offset-1',
               'disabled:opacity-50 disabled:cursor-not-allowed', s.color]"
      @click="$emit('score', s.score)">
      <span class="block font-bold">{{ s.score }}</span>
      <span class="text-xs">{{ s.label }}</span>
    </button>
  </div>
</template>
