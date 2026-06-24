import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useQuestionsStore } from '@/stores/questions'

describe('useQuestionsStore', () => {
  beforeEach(() => { setActivePinia(createPinia()) })

  it('setList updates items and total', () => {
    const store = useQuestionsStore()
    const fakeQ = [{ id: '1', content: '题目', correct_answer: '答案' }] as never[]
    store.setList(fakeQ, 1)
    expect(store.items.length).toBe(1)
    expect(store.total).toBe(1)
  })

  it('removeById removes item and decrements total', () => {
    const store = useQuestionsStore()
    const fakeQ = [{ id: 'q1' }, { id: 'q2' }] as never[]
    store.setList(fakeQ, 2)
    store.removeById('q1')
    expect(store.items.length).toBe(1)
    expect(store.total).toBe(1)
  })
})
