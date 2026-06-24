# SDD Progress Ledger — 错题本 Plan 1

## Plan
docs/superpowers/plans/2026-06-24-plan1-backend-foundation.md

## Tasks
- [x] Task 1: pyproject.toml + 依赖安装
- [x] Task 2: core/config.py + core/database.py
- [x] Task 3: models/user.py + models/question.py + models/review_log.py
- [x] Task 4: core/security.py（JWT + 密码哈希）
- [x] Task 5: repositories/user_repository.py + services/auth_service.py + schemas/auth.py
- [x] Task 6: api/v1/endpoints/auth.py + main.py + tests/conftest.py + tests/api/test_auth.py
- [x] Task 7: HTTPException 统一错误处理

## Minor Findings (accumulated)
(none yet)
Task 1: complete (commits bc2ae17..9fba076, review clean)
Task 2: complete (commits 9fba076..0d07ee1, review clean)
Task 3: complete (commits 0d07ee1..dfb9d32, review clean; minor: field named confidence_score not confidence)
## Minor Findings
- Task 3: Question.confidence_score (not .confidence) — diverges from Plan 2/3 schema field name; downstream services should use .confidence_score
Task 4: complete (commits dfb9d32..4c9c6d7, review clean; minor: HTTPBearer used instead of OAuth2PasswordBearer)
Task 5: complete (commits 4c9c6d7..9285c79 + 1deb205 pycache fix, review clean; tech debt: repo.create() commits — fix when multi-table txns needed)
Task 6: complete (commits 1deb205..d5d2ae5, LOW fixes applied; MEDIUM: test assertions use [detail][code] not [error][code] — fix together with Task 7 HTTPException handler)
Task 7: complete (commits d5d2ae5..78e365f, review clean)
Final review fixes: complete (commit 86cc25b — R4 status default, nullable fields, passlib removed)

## Plan 1 COMPLETE
All 7 tasks done. 20 tests passing. HEAD: 86cc25b fix: Question model nullability, status default, remove passlib dep (R4/R21)
