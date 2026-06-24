# Task 1: Backend CORS Middleware

## Context
You are working on the 错题本 app at /workshop/ypjh. The backend is a FastAPI app at backend/main.py. This task adds CORS middleware so the frontend dev server (Vite on port 5173) can call the backend (port 8000).

## What to do

Edit `backend/main.py` — add CORS middleware after `app = FastAPI(...)`:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Verification
Run: `cd /workshop/ypjh && uv run pytest backend/tests/ -q --tb=short`
All 75 tests must pass.

## Commit
`git commit -m "feat: add CORS middleware for frontend dev origin"`

## Report
Write your full report to: /workshop/ypjh/.superpowers/sdd/plan7/task-1-report.md

Return: status (DONE/DONE_WITH_CONCERNS/BLOCKED), commit hash, test summary (one line).
