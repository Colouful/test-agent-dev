<!-- frontend/src/pages/QuestionDetailPage.vue -->
<!-- Stub: full implementation in Task 2 -->
<script setup lang="ts">
import { useRoute } from 'vue-router'

const route = useRoute()
const id = route.params.id
</script>

<template>
  <div class="p-4">
    <p>Loading question {{ id }}…</p>
  </div>
</template>
