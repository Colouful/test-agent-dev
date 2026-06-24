<!-- frontend/src/components/SkeletonCard.vue -->
<script setup lang="ts">
defineProps<{ lines?: number }>()
</script>

<template>
  <div class="bg-white rounded-xl shadow-sm p-5 animate-pulse">
    <div class="h-3 bg-gray-200 rounded w-1/4 mb-3"></div>
    <div v-for="i in (lines ?? 3)" :key="i" class="mb-2">
      <div :class="['h-2.5 bg-gray-200 rounded', i === (lines ?? 3) ? 'w-3/4' : 'w-full']"></div>
    </div>
  </div>
</template>
