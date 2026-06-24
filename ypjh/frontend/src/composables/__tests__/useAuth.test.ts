import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from '@/stores/auth'

describe('useAuthStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
  })

  it('starts with null token', () => {
    const store = useAuthStore()
    expect(store.token).toBeNull()
  })

  it('setToken persists to localStorage', () => {
    const store = useAuthStore()
    store.setToken('test-jwt')
    expect(store.token).toBe('test-jwt')
    expect(localStorage.getItem('access_token')).toBe('test-jwt')
  })

  it('logout clears token and localStorage', () => {
    const store = useAuthStore()
    store.setToken('test-jwt')
    store.logout()
    expect(store.token).toBeNull()
    expect(localStorage.getItem('access_token')).toBeNull()
  })
})
