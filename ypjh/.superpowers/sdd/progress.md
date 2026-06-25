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

---

# SDD Progress Ledger — 错题本 Plan 2

## Plan
docs/superpowers/plans/2026-06-24-plan2-recognition-api.md

## Tasks
- [x] Task 1: image_utils.py (Magic Bytes, EXIF, R16/REQ-27)
- [x] Task 2: s3_client.py (R18/R20/R23)
- [x] Task 3: recognition_service.recognize_upload() + schemas/recognition.py
- [x] Task 4: api/v1/endpoints/questions_recognize.py (R17, R22)

## Minor Findings (accumulated)
- Task 2: unused imports removed inline (not a separate fix commit)
- Task 3: getattr() defensive code removed; type: ignore replaced with cast()
- Task 4: unused session dependency removed inline

## Final Review Findings (all fixed)
- Critical 1: Double upload → production always errors — fixed (image_key=None pattern)
- Critical 2: R23 violated — raw S3 key in response → replaced with presigned URL (image_key→image_url)
- Critical 3: REQ-28 non-question dead code → moved check to recognize() reading Bedrock raw response
- Important 4: PNG re-encoded as JPEG (exif_transpose clears format) → capture format before transpose
- Important 5: HEIC check too broad (matches MP4/MOV) → added _HEIC_BRANDS brand validation
- Important 6: R24 incomplete (PROMPT_PATH never loaded) → added R24 scaffold in _call_bedrock()
- Bonus: S3 error code OCR_FAILED → UPLOAD_FAILED; sys.path.insert deduplication

Final review fixes: complete (commit 3c2d431)

## Plan 2 COMPLETE
All 4 tasks done + final review fixes. 35 tests passing. HEAD: 3c2d431

---

# SDD Progress Ledger — 错题本 Plan 3

## Plan
docs/superpowers/plans/2026-06-24-plan3-crud-api.md

## Tasks
- [x] Task 1: schemas/question.py (QuestionCreate/Update/Out/ListOut)
- [x] Task 2: repositories/question_repository.py (R1/R21, user isolation, soft delete)
- [x] Task 3: services/question_service.py (presigned URLs R23)
- [x] Task 4: api/v1/endpoints/questions.py + router.py

## Minor Findings (accumulated)
- QuestionOut.user_id exposed in response (harmless, future cleanup)
- original_filename not in QuestionOut (intentional or gap — needs product decision)
- list_by_user issues two SQL queries — acceptable at current scale
- QuestionUpdate uses exclude_none (null sends ignored — may want exclude_unset)
- confidence has no 0.0–1.0 validation range on QuestionCreate

## Final Review Findings (all fixed)
- Important 1: image_key path validation — prevent cross-user S3 key injection (service layer check)
- Important 2: limit query param missing ge=1 lower bound

Final review fixes: complete (commit 9081c81)

## Plan 3 COMPLETE
All 4 tasks done + final review fixes. 53 tests passing. HEAD: 9081c81

---

# SDD Progress Ledger — 错题本 Plan 4

## Plan
docs/superpowers/plans/2026-06-24-plan4-sm2-review.md

## Tasks
- [x] Task 1: core/sm2.py (SM-2 pure algorithm)
- [x] Task 2: repositories/review_repository.py + schemas/review.py
- [x] Task 3: services/review_service.py + api/v1/endpoints/review.py + router.py

## Minor Findings (accumulated)
- C6: _PRESIGN_EXPIRES hardcoded twice — fixed (extracted constant)
- C7: redundant session.flush() before create_log — fixed

## Final Review Findings (all fixed)
- Critical C1: ScoreRequest ge=1 → ge=0 (SM-2 allows score 0)
- Critical C2: ReviewQueueOut.total was len(items); now uses true get_due_count()
- Critical C3: submit_score never set last_reviewed_at — fixed
- Important C4: Out schemas missing from_attributes=True — fixed
- Important C5: get_stats duplicated due-question predicate — refactored to delegate to get_due_count()

Final review fixes: complete (commit a44e9e6)

## Plan 4 COMPLETE
All 3 tasks done + final review fixes. 67 tests passing. HEAD: a44e9e6

---

# SDD Progress Ledger — 错题本 Plan 5

## Plan
docs/superpowers/plans/2026-06-24-plan5-print.md

## Tasks
- [x] Task 1: schemas/print_schema.py (PrintRequest)
- [x] Task 2: templates/print_preview.html (Jinja2 + KaTeX CDN)
- [x] Task 3: api/v1/endpoints/print.py + router.py

## Minor Findings (accumulated)
- Singleton _repo at module level (acceptable, stateless)
- alt text on image is hardcoded (acceptable)
- boto3 sync blocking in async (accepted — skip, MOCK_BEDROCK=true for dev/test)

## Final Review Findings (all fixed)
- Critical: MOCK_S3 variable name misleading → renamed to MOCK_BEDROCK
- Important: duplicate question_ids → deduplicated with dict.fromkeys
- Important: N+1 DB queries → replaced with get_by_ids() batch method
- Important: per-element empty string validation → Annotated[str, Field(min_length=1)]
- Important (skipped): boto3 sync blocking — accepted, dev/test uses mock mode

Final review fixes: complete (commit 7e17ddb)

## Plan 5 COMPLETE
All 3 tasks done + final review fixes. 75 tests passing. HEAD: 7e17ddb

---

# SDD Progress Ledger — 错题本 Plan 6 (Frontend)

## Plan
docs/superpowers/plans/2026-06-24-plan6-frontend.md

## Tasks
- [x] Task 1: Types, router, Tailwind config
- [x] Task 2: API client, mock index, auth store + composable
- [x] Task 3: Question mock, question store + composable
- [x] Task 4: Review/print mocks, review store + composable
- [x] Task 5: Global components (AppToast, Skeleton, QuestionCard, ReviewScoreButtons, useKatex, App.vue)
- [x] Task 6: All 7 pages

## Task Log
Task 1: complete (commits 7e17ddb..52c9729, review clean)
Task 2: complete (commits 52c9729..90c053e, review clean)
Task 3: complete (commits 90c053e..881dfb8, review clean)
Task 4: complete (commits 881dfb8..feb8688, review clean; reviewer criticals adjudicated as false positives — ApiResponse.data is T not T|null, store ref mutation is idiomatic Pinia)
Task 5: complete (commits feb8688..a5901f6, review clean)
Task 5: complete (commits feb8688..a5901f6, review clean)
Task 6: complete (commits a5901f6..32231e8, 1 critical fix — correct_answer added to ReviewQueueItemOut/ReviewQueueItem/mock/ReviewPage)

## Final Review Findings (all fixed, commit d3f2de6)
- Important: scaffold files deleted (HelloWorld, TheWelcome, WelcomeItem, icons/, views/)
- Important: index.html lang="" → zh-CN, title → 错题本
- Important: PrintPage allSelected vacuous-true on empty list — guarded with .length > 0
- Important: useReview.fetchQueue missing loading state — added loading ref + try/finally
- Minor: DashboardPage unused toast inject — removed
- Minor: UploadPage unused RecognitionResult import — removed
- Minor: RegisterPage confirm var shadows window.confirm — renamed confirmPassword
- Note: PrintPage direct apiClient — plan-mandated (brief's PrintPage.vue uses apiClient directly; usePrint.ts listed in dir structure but never defined in any task)

## Plan 6 COMPLETE
All 6 tasks done + final review fixes. 75 backend tests passing. HEAD: d3f2de6

---

# SDD Progress Ledger — 错题本 Plan 7 (Frontend-Backend Integration)

## Tasks
- [x] Task 1: Backend CORS middleware
- [ ] Task 2: Vite proxy + env files
- [ ] Task 3: Real API endpoint functions + wire composables

Task 1: complete (commits d3f2de6..35cb62d, review clean)
Task 2: complete (commits 35cb62d..34a732a, review clean; client.ts baseURL was already correct from Plan 6)
Task 3: complete (commits 34a732a..bc62ca6, review clean)
- [x] Task 3: Real API endpoint functions + wire composables

## Plan 7 COMPLETE
All 3 tasks done. 75 backend tests passing. TypeScript type-check clean. HEAD: bc62ca6
Task 1: complete (commits 84837bc..6b8c805, review clean; indicator fix inline)
Task 2: complete (commits 6b8c805..fd7c7f9, review clean)
Task 3: complete (commits fd7c7f9..c8784a2, review clean)
Task 4: complete (commits c8784a2..5517249, review clean)
Task 5: complete (build ✓, frontend restart ✓, backend ✓)

## Plan COMPLETE
All 5 tasks done. HEAD: d2f70d9

# SDD Progress Ledger — subject-tags-and-profile

## Plan
docs/superpowers/plans/2026-06-25-subject-tags-and-profile.md

## Tasks
- [x] Task 1: Bottom nav → 我的 + /profile route
- [x] Task 2: Subject tag filter + grouped list
- [x] Task 3: PATCH /auth/password backend
- [x] Task 4: ProfilePage full implementation

Task 1: complete (commits 30df55e..90029b4, review clean)
Task 2: complete (commits 90029b4..07b0c6e, review clean)
Task 3: complete (commits 07b0c6e..a5c7d28, review clean; minor: inline imports in change_password method + direct ORM query bypasses UserRepository)
Task 4: complete (commits a5c7d28..7c97d99, review clean; minor fix: dynamic import → static for mockQuestions)

Final review: clean after fix (commit c98a9e4 — cancel button clears password fields)

## subject-tags-and-profile COMPLETE
All 4 tasks done. HEAD: c98a9e4

# SDD Progress Ledger — ai-analysis

## Plan
docs/superpowers/plans/2026-06-25-ai-analysis.md

## Tasks
- [x] Task 1: Backend model + schemas (analysis field)
- [ ] Task 2: Prompt + recognition service + repository
- [ ] Task 3: Frontend types + mock + detail page + upload

Task 1: complete (commits dcf7f15..63caaff, review clean)
Task 1: complete (commits f1c949e..348bf35, review clean; minor: QuestionOut defaults are dead code — spec-inherited)
Task 2: complete (commits 348bf35..1885b34, review clean; minor fix: removed unused imports+helper from test scaffold)
Task 3: complete (commits 1885b34..481491b, review clean after fix — added cross-user+idempotent tests, moved import to module top)
Task 4: complete (commit b9ca644, review clean)
