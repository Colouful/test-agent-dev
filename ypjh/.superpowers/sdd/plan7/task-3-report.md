# Task 3 Report: Real API Endpoint Functions + Wire Composables

## Status: DONE

## Commit: bc62ca6

## What Was Done

### New Endpoint Files Created
- `frontend/src/api/endpoints/auth.ts` — authApi with login, register, me
- `frontend/src/api/endpoints/questions.ts` — questionsApi with list, get, create, update, delete, recognize
- `frontend/src/api/endpoints/review.ts` — reviewApi with queue, submitScore, stats
- `frontend/src/api/endpoints/print.ts` — printApi with preview

### Composables Updated
- `useAuth.ts`: Replaced `apiClient` import with `authApi`; wired login() and register() non-mock branches
- `useQuestions.ts`: Replaced `apiClient` import with `questionsApi`; wired fetchList(), recognize(), confirmAndSave(), softDelete()
- `useReview.ts`: Replaced `apiClient` import with `reviewApi`; wired fetchQueue(), fetchStats(), submitScore()

All direct `apiClient` calls removed from composables; each file now only imports from its typed endpoint module.

## Verification

- `npm run type-check`: PASSED (clean, no errors)
- `uv run pytest backend/tests/ -q --tb=short`: 75 passed, 1 warning (pre-existing StarletteDeprecationWarning unrelated to this task)

Note: pytest must be run from `/workshop/ypjh/backend/` (not the repo root) since pyproject.toml is there.
