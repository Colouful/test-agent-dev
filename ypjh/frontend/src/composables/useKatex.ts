// frontend/src/composables/useKatex.ts
import { onMounted, onUpdated, type Ref } from 'vue'

export function useKatex(containerRef: Ref<HTMLElement | null>) {
  function renderMath() {
    if (!containerRef.value) return
    import('katex/contrib/auto-render').then(({ default: renderMathInElement }) => {
      if (!containerRef.value) return
      renderMathInElement(containerRef.value, {
        delimiters: [
          { left: '$$', right: '$$', display: true },
          { left: '$', right: '$', display: false },
        ],
        throwOnError: false,
      })
    })
  }
  onMounted(renderMath)
  onUpdated(renderMath)
}
