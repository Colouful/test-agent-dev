# Task 2: Vite Proxy + Env Files

## Context
You are working on the 错题本 app at /workshop/ypjh. The frontend is a Vue 3 + Vite app at frontend/. This task configures the Vite dev server proxy so /api requests go to the backend on port 8000, and sets up env files to control the API base URL.

## What to do

### 1. Replace `frontend/vite.config.ts` entirely with:

```ts
import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
```

Note: Remove `vueDevTools()` plugin (not needed in production and may cause issues).

### 2. Create `frontend/.env.development`:
```
VITE_MOCK=false
VITE_API_BASE_URL=/api
```

### 3. Create `frontend/.env.production`:
```
VITE_MOCK=false
VITE_API_BASE_URL=/api
```

### 4. Create `frontend/.env.mock`:
```
VITE_MOCK=true
VITE_API_BASE_URL=/api
```

### 5. Update `frontend/src/api/client.ts`
Change the baseURL line to:
```ts
baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
```
Keep all other lines in client.ts exactly the same.

## Verification
Run: `cd /workshop/ypjh/frontend && npm run type-check`
Must pass clean.

## Commit
`git commit -m "feat: Vite proxy config, env files for API routing"`

## Report
Write your full report to: /workshop/ypjh/.superpowers/sdd/plan7/task-2-report.md

Return: status (DONE/DONE_WITH_CONCERNS/BLOCKED), commit hash, test summary (one line).
