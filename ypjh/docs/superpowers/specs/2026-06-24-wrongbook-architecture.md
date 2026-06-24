# 错题本（Wrongbook）架构设计文档

**版本**：1.0  
**日期**：2026-06-24  
**来源**：基于 `2026-06-24-wrongbook-master-srs.md` + `2026-06-24-wrongbook-fullstack-design.md` + Plan 1-7  
**状态**：权威参考，勿直接修改（以 SRS 为准）

---

## 目录

1. [系统整体架构](#1-系统整体架构)
2. [技术栈层次图](#2-技术栈层次图)
3. [后端目录结构与模块依赖](#3-后端目录结构与模块依赖)
4. [前端目录结构与模块依赖](#4-前端目录结构与模块依赖)
5. [数据模型关系图](#5-数据模型关系图)
6. [Question 状态机](#6-question-状态机)
7. [识别主线数据流](#7-识别主线数据流)
8. [识别接口序列图](#8-识别接口序列图)
9. [认证流程序列图](#9-认证流程序列图)
10. [CRUD 操作流程](#10-crud-操作流程)
11. [SM-2 复习算法流程](#11-sm-2-复习算法流程)
12. [复习模块序列图](#12-复习模块序列图)
13. [打印模块流程](#13-打印模块流程)
14. [前端路由与页面结构](#14-前端路由与页面结构)
15. [前端识别状态机](#15-前端识别状态机)
16. [前端组件依赖图](#16-前端组件依赖图)
17. [错误处理层次](#17-错误处理层次)
18. [安全边界与用户隔离](#18-安全边界与用户隔离)
19. [实现顺序与依赖关系](#19-实现顺序与依赖关系)
20. [API 端点全览](#20-api-端点全览)

---

## 1. 系统整体架构

系统由三大部分组成：Vue 3 前端、FastAPI 后端、AWS 外部服务（S3 + Bedrock）。

```mermaid
graph TB
    subgraph 用户端
        U[学生用户\n浏览器]
    end

    subgraph 前端 Vue 3
        FE_ROUTER[Vue Router v4]
        FE_STORE[Pinia Store]
        FE_API[Axios HTTP Client\nBearer token interceptor]
        FE_MOCK[Mock Layer\nVITE_USE_MOCK=true]
    end

    subgraph 后端 FastAPI
        BE_AUTH[认证模块\nJWT HS256]
        BE_RECOGNIZE[识别模块\nrecognition_service]
        BE_CRUD[CRUD 模块\nquestion_service]
        BE_SM2[SM-2 复习模块\nreview_service]
        BE_PRINT[打印模块\nprint_service]
        BE_REPO[Repository 层\n所有 DB 操作含 user_id]
        BE_DB[(SQLite / DynamoDB\ncuotiben-questions)]
    end

    subgraph AWS 外部服务
        S3[AWS S3\n原图持久化]
        BEDROCK[AWS Bedrock\nAI 识别]
    end

    U --> FE_ROUTER
    FE_ROUTER --> FE_STORE
    FE_STORE --> FE_API
    FE_API -.->|VITE_USE_MOCK=true| FE_MOCK
    FE_API -->|HTTPS /api/v1/| BE_AUTH
    FE_API -->|HTTPS /api/v1/| BE_RECOGNIZE
    FE_API -->|HTTPS /api/v1/| BE_CRUD
    FE_API -->|HTTPS /api/v1/| BE_SM2
    FE_API -->|HTTPS /api/v1/| BE_PRINT

    BE_AUTH --> BE_REPO
    BE_RECOGNIZE --> BE_REPO
    BE_CRUD --> BE_REPO
    BE_SM2 --> BE_REPO
    BE_PRINT --> BE_REPO
    BE_REPO --> BE_DB

    BE_RECOGNIZE -->|上传原图| S3
    BE_RECOGNIZE -->|识别请求| BEDROCK
    BE_CRUD -->|预签名 URL| S3
```

---

## 2. 技术栈层次图

```mermaid
graph LR
    subgraph 前端层
        direction TB
        VUE[Vue 3\nscript setup lang=ts]
        PINIA[Pinia\n状态管理]
        ROUTER[Vue Router v4\n路由守卫]
        AXIOS[Axios\ninterceptor 自动注入 token]
        KATEX[KaTeX\n数学公式离线渲染]
        VITEST[Vitest\n单元测试]
    end

    subgraph 后端层
        direction TB
        FASTAPI[FastAPI\nPython 3.12 async]
        PYDANTIC[Pydantic v2\n数据校验]
        SQLA[SQLAlchemy 2\nasync session]
        JOSE[python-jose\nJWT HS256]
        PASSLIB[passlib bcrypt\ncost=12]
        PYTEST[pytest + httpx\nAPI 测试]
    end

    subgraph 存储层
        SQLITE[SQLite\n开发环境]
        DYNAMO[DynamoDB\n生产环境]
        S3STORE[AWS S3\n图片存储]
    end

    subgraph AI 层
        BEDROCKL[AWS Bedrock\nMOCK_BEDROCK=true 可 mock]
        PROMPT[prompts/\nrecognize_question.txt]
    end

    VUE --> PINIA
    VUE --> ROUTER
    VUE --> AXIOS
    VUE --> KATEX
    VUE --> VITEST

    FASTAPI --> PYDANTIC
    FASTAPI --> SQLA
    FASTAPI --> JOSE
    FASTAPI --> PASSLIB
    FASTAPI --> PYTEST

    SQLA --> SQLITE
    SQLA --> DYNAMO
    FASTAPI --> S3STORE

    FASTAPI --> BEDROCKL
    BEDROCKL --> PROMPT
```

---

## 3. 后端目录结构与模块依赖

```mermaid
graph TD
    subgraph backend/
        MAIN[main.py\nFastAPI app 入口]

        subgraph core/
            CONFIG[config.py\nSettings env vars]
            DATABASE[database.py\nasync engine + get_session]
            SECURITY[security.py\nJWT + bcrypt + get_current_user]
        end

        subgraph models/
            BASE[base.py\nDeclarativeBase]
            USER_M[user.py\nUser ORM]
            QUESTION_M[question.py\nQuestion ORM + SM-2 字段]
            REVIEWLOG_M[review_log.py\nReviewLog ORM]
        end

        subgraph schemas/
            COMMON[common.py\nApiResponse T]
            AUTH_S[auth.py\nRegisterRequest LoginRequest AuthResponse]
            QUESTION_S[question.py\nQuestionCreate Update Out ListOut]
            RECOG_S[recognition.py\nRecognitionResultOut CandidateOut]
            REVIEW_S[review.py\nReviewQueueOut ScoreRequest StatsOut]
            PRINT_S[print_.py\nPrintRequest]
        end

        subgraph repositories/
            USER_R[user_repository.py\nget_by_email create]
            QUESTION_R[question_repository.py\n所有查询带 user_id R1]
            REVIEW_R[review_repository.py\nReviewLog 只追加]
        end

        subgraph services/
            AUTH_SVC[auth_service.py\nregister login]
            QUESTION_SVC[question_service.py\ncreate update delete list]
            RECOG_SVC[recognition_service.py\nMagic Bytes S3 Bedrock]
            REVIEW_SVC[review_service.py\nSM-2 calculate_next_review]
            PRINT_SVC[print_service.py\nHTML 生成 KaTeX]
        end

        subgraph api/v1/endpoints/
            AUTH_EP[auth.py\nPOST register login]
            QUESTION_EP[questions.py\nCRUD + recognize]
            REVIEW_EP[review.py\nqueue score stats]
            PRINT_EP[print_.py\nPOST preview]
        end

        subgraph prompts/
            PROMPT_FILE[recognize_question.txt\nR24 禁止硬编码]
        end
    end

    MAIN --> AUTH_EP
    MAIN --> QUESTION_EP
    MAIN --> REVIEW_EP
    MAIN --> PRINT_EP

    AUTH_EP --> AUTH_SVC
    QUESTION_EP --> QUESTION_SVC
    QUESTION_EP --> RECOG_SVC
    REVIEW_EP --> REVIEW_SVC
    PRINT_EP --> PRINT_SVC

    AUTH_SVC --> USER_R
    QUESTION_SVC --> QUESTION_R
    RECOG_SVC --> QUESTION_R
    REVIEW_SVC --> REVIEW_R
    REVIEW_SVC --> QUESTION_R
    PRINT_SVC --> QUESTION_R

    USER_R --> USER_M
    QUESTION_R --> QUESTION_M
    REVIEW_R --> REVIEWLOG_M

    USER_M --> BASE
    QUESTION_M --> BASE
    REVIEWLOG_M --> BASE

    BASE --> DATABASE
    DATABASE --> CONFIG
    AUTH_EP --> SECURITY
    QUESTION_EP --> SECURITY
    REVIEW_EP --> SECURITY
    PRINT_EP --> SECURITY
    SECURITY --> CONFIG

    RECOG_SVC --> PROMPT_FILE
```

---

## 4. 前端目录结构与模块依赖

```mermaid
graph TD
    subgraph frontend/src/
        subgraph pages/
            LOGIN_P[LoginPage.vue]
            REGISTER_P[RegisterPage.vue]
            HOME_P[HomePage.vue\n错题列表]
            UPLOAD_P[UploadPage.vue\n上传识别确认]
            DETAIL_P[QuestionDetailPage.vue]
            REVIEW_P[ReviewPage.vue]
            PRINT_P[PrintPage.vue]
        end

        subgraph components/
            QCARD[QuestionCard.vue\nKaTeX 渲染]
            RECOG_PREV[RecognitionPreview.vue\nhigh_confidence pending_review]
            DROPZONE[UploadDropzone.vue\n文件校验拖拽]
            REVIEW_CARD[ReviewCard.vue\n答案翻转评分]
        end

        subgraph composables/
            USE_AUTH[useAuth.ts]
            USE_QUESTIONS[useQuestions.ts]
            USE_RECOG[useRecognition.ts\n状态机 idle→done]
            USE_REVIEW[useReview.ts]
        end

        subgraph stores/
            AUTH_STORE[useAuthStore.ts\ntoken localStorage]
            QUESTION_STORE[useQuestionStore.ts]
        end

        subgraph api/
            CLIENT[client.ts\nAxios 实例 interceptor]
            AUTH_API[auth.ts]
            QUESTIONS_API[questions.ts]
            REVIEW_API[review.ts]
            PRINT_API[print.ts]
            subgraph __mocks__/
                MOCK_AUTH[auth.ts]
                MOCK_QUESTIONS[questions.ts]
                MOCK_REVIEW[review.ts]
                MOCK_PRINT[print.ts]
            end
        end

        subgraph types/
            MODELS_T[models.ts\nQuestion RecognitionResult TS 类型]
        end

        ROUTER_FILE[router/index.ts\n路由守卫 beforeEach]
    end

    HOME_P --> QCARD
    HOME_P --> USE_QUESTIONS
    UPLOAD_P --> DROPZONE
    UPLOAD_P --> RECOG_PREV
    UPLOAD_P --> USE_RECOG
    DETAIL_P --> QCARD
    DETAIL_P --> USE_QUESTIONS
    REVIEW_P --> REVIEW_CARD
    REVIEW_P --> USE_REVIEW
    PRINT_P --> USE_QUESTIONS

    USE_AUTH --> AUTH_STORE
    USE_QUESTIONS --> QUESTION_STORE
    USE_RECOG --> QUESTIONS_API
    USE_REVIEW --> REVIEW_API

    AUTH_STORE --> AUTH_API
    QUESTION_STORE --> QUESTIONS_API

    AUTH_API --> CLIENT
    QUESTIONS_API --> CLIENT
    REVIEW_API --> CLIENT
    PRINT_API --> CLIENT

    CLIENT -.->|VITE_USE_MOCK=true| MOCK_AUTH
    CLIENT -.->|VITE_USE_MOCK=true| MOCK_QUESTIONS
    CLIENT -.->|VITE_USE_MOCK=true| MOCK_REVIEW
    CLIENT -.->|VITE_USE_MOCK=true| MOCK_PRINT

    ROUTER_FILE --> AUTH_STORE
```

---

## 5. 数据模型关系图

```mermaid
erDiagram
    User {
        string id PK "UUID v4"
        string email UK "唯一索引"
        string hashed_password "bcrypt cost=12"
        datetime created_at
        datetime deleted_at "NULL=未删除 软删除"
    }

    Question {
        int id PK "autoincrement"
        string user_id FK "来自 JWT sub 严格隔离 R1"
        string subject "学科白名单 or NULL"
        string question_type "single/multiple/fill/essay"
        string content "结构化存储 R3"
        string wrong_answer "手写答案分离 R11"
        string correct_answer
        string analysis
        int difficulty "1-5"
        float confidence_score "ARCH-2 不得 NULL"
        string image_key "S3路径 user_id/original/uuid.ext R20"
        string original_filename "R18 不入S3路径"
        string status "confirmed/pending_review/superseded"
        float ease_factor "SM-2 初始2.5"
        int review_count "SM-2"
        int interval_days "SM-2 当前间隔天"
        datetime next_review_at "NULL=从未复习"
        datetime last_reviewed_at
        datetime created_at
        datetime updated_at
        datetime deleted_at "R21 软删除"
    }

    ReviewLog {
        int id PK
        int question_id FK
        string user_id "冗余存储 避免跨用户JOIN泄露"
        int score "1-5 SM-2评分"
        float ease_factor_before "调试用"
        float ease_factor_after
        int interval_before
        int interval_after
        datetime reviewed_at
    }

    User ||--o{ Question : "拥有 user_id隔离"
    Question ||--o{ ReviewLog : "产生 追加不修改"
    User ||--o{ ReviewLog : "冗余user_id"
```

---

## 6. Question 状态机

```mermaid
stateDiagram-v2
    [*] --> 识别返回

    state 识别返回 {
        high_confidence : confidence ≥ 0.7
        pending_review : confidence < 0.7\n或无错误标记\n或非题目图片
        error : Bedrock 失败\n或非法 JSON\n或非图片文件
    }

    high_confidence --> confirmed : 用户确认
    pending_review --> confirmed : 用户核对确认
    pending_review --> 丢弃 : 用户拒绝
    error --> 丢弃 : 不入库

    confirmed --> superseded : 重新识别同一image_key\n旧记录标记
    confirmed --> confirmed : 用户编辑\nupdated_at更新
    confirmed --> 软删除 : deleted_at = now()\nR21 禁止物理删除

    软删除 --> [*]
    丢弃 --> [*]
    superseded --> [*]

    note right of confirmed
        SM-2 初始化
        ease_factor=2.5
        interval_days=1
        next_review_at=now()+1d
    end note
```

---

## 7. 识别主线数据流

```mermaid
flowchart TD
    A[用户选择图片\nUploadPage] --> B{本地校验\n文件类型 + 大小}
    B -->|不合法| ERR0[前端提示错误\n不发请求]
    B -->|合法| C[POST /api/v1/questions/recognize\nmultipart/form-data]

    C --> D{Magic Bytes 校验\nR16 JPEG/PNG/HEIC}
    D -->|失败| ERR1[415 INVALID_FILE_TYPE]
    D -->|通过| E{Content-Length\nR17 ≤ 20MB}
    E -->|超出| ERR2[413 FILE_TOO_LARGE]
    E -->|通过| F[EXIF 旋转修正\nREQ-27 送Bedrock前执行]

    F --> G[S3 上传原图\nkey: user_id/original/uuid.ext R20]
    G -->|失败| ERR3[status=error\nerror_hint=图片上传失败]
    G -->|成功| H[Bedrock 识别\nMAX_RETRY=2 指数退避 REQ-30]

    H -->|429/503 重试超限| ERR4[status=error\nOCR_RATE_LIMITED]
    H -->|非法 JSON 响应| ERR5[status=error\nOCR_FORMAT_ERROR REQ-29]
    H -->|识别成功| I{Schema 校验\nconfidence 缺失→0.0 R2}

    I --> J{非题目图片？\nREQ-28}
    J -->|是| ERR6[status=error\n不进入确认流程]
    J -->|否| K{无错误标记？\nR10 REQ-12}
    K -->|是| L[status=pending_review\nerror_hint=未检测到错误标记]

    K -->|否| M{confidence < 0.7?\nR4}
    M -->|是| N[status=pending_review]
    M -->|否| O[status=high_confidence]

    L --> P[返回 RecognitionResultOut\n不入库]
    N --> P
    O --> P

    P --> Q[前端 confirming 状态\nRecognitionPreview 展示]
    Q --> R{用户确认/编辑}
    R -->|拒绝| S[丢弃 不入库]
    R -->|确认| T[POST /api/v1/questions\n创建 Question 记录]

    T --> U{二次识别同image_key?\nREQ-19}
    U -->|是| V[旧记录 status→superseded]
    U -->|否| W[SM-2 初始化\nease_factor=2.5 next_review_at=now+1d]
    V --> W
    W --> X[HTTP 201 返回 QuestionOut]
    X --> Y[跳转 QuestionDetailPage]
```

---

## 8. 识别接口序列图

```mermaid
sequenceDiagram
    participant U as 用户浏览器
    participant FE as Vue 前端
    participant BE as FastAPI 后端
    participant S3 as AWS S3
    participant BD as AWS Bedrock

    U->>FE: 选择/拖拽图片
    FE->>FE: 本地校验 类型+大小
    FE->>BE: POST /api/v1/questions/recognize\nAuthorization: Bearer <token>

    BE->>BE: JWT 验证 提取 user_id
    BE->>BE: Magic Bytes 校验 R16
    BE->>BE: Content-Length 校验 R17
    BE->>BE: EXIF 旋转修正 REQ-27

    BE->>S3: PutObject user_id/original/uuid.ext
    S3-->>BE: 上传成功 image_key

    BE->>BD: InvokeModel 附带图片 + prompt
    Note over BD: MOCK_BEDROCK=true 时跳过

    alt Bedrock 失败 (429/503)
        BD-->>BE: 限流错误
        BE->>BD: 重试 最多2次 指数退避
        BD-->>BE: 仍失败
        BE-->>FE: {status: "error", error_code: "OCR_RATE_LIMITED"}
    else Bedrock 返回非法 JSON
        BD-->>BE: 非法 JSON
        BE-->>FE: {status: "error", error_code: "OCR_FORMAT_ERROR"}
    else 识别成功
        BD-->>BE: JSON 候选结果
        BE->>BE: Schema 校验\nconfidence 缺失→0.0
        BE-->>FE: RecognitionResultOut\n{status, candidate, error_hint}
    end

    FE->>FE: 切换状态机→confirming
    FE->>U: 展示 RecognitionPreview\nhigh_confidence绿 / pending_review黄

    U->>FE: 编辑确认
    FE->>BE: POST /api/v1/questions\n{candidate fields}
    BE->>BE: SM-2 初始化
    BE-->>FE: 201 {id, ...QuestionOut}
    FE->>FE: 切换状态机→done
    FE->>U: 跳转题目详情页
```

---

## 9. 认证流程序列图

```mermaid
sequenceDiagram
    participant U as 用户
    participant FE as Vue 前端
    participant BE as FastAPI 后端
    participant DB as SQLite/DynamoDB

    rect rgb(220, 240, 255)
        Note over U,DB: 注册流程
        U->>FE: 填写邮箱 + 密码(≥8位)
        FE->>FE: 本地校验 密码长度/一致性
        FE->>BE: POST /api/v1/auth/register\n{email, password}
        BE->>DB: SELECT user WHERE email=? AND deleted_at IS NULL
        DB-->>BE: 无记录
        BE->>BE: bcrypt hash(password, rounds=12)
        BE->>DB: INSERT User {id=uuid4(), email, hashed_password}
        DB-->>BE: 成功
        BE->>BE: create_access_token(user.id)\nJWT HS256 有效期24h
        BE-->>FE: 201 {access_token, token_type, expires_in}
        FE->>FE: localStorage.wrongbook_token = token
        FE->>U: 跳转 /
    end

    rect rgb(255, 240, 220)
        Note over U,DB: 登录流程
        U->>FE: 填写邮箱 + 密码
        FE->>BE: POST /api/v1/auth/login\n{email, password}
        BE->>DB: SELECT user WHERE email=?
        DB-->>BE: User 记录
        BE->>BE: bcrypt.checkpw(password, hashed)
        alt 密码正确
            BE->>BE: create_access_token(user.id)
            BE-->>FE: 200 {access_token}
            FE->>FE: 存 token 跳转目标页
        else 密码错误或邮箱不存在
            BE-->>FE: 401 {code: "INVALID_CREDENTIALS"}\n防枚举 两种情况同一响应
            FE->>U: 表单提示"邮箱或密码错误"\n密码框不清空
        end
    end

    rect rgb(220, 255, 220)
        Note over U,DB: 受保护端点访问
        FE->>BE: GET /api/v1/questions\nAuthorization: Bearer <token>
        BE->>BE: 从 header 提取 token
        BE->>BE: jwt.decode(token, SECRET_KEY)
        alt token 有效
            BE->>BE: user_id = payload["sub"]
            BE->>DB: 所有查询带 WHERE user_id=? R1
            DB-->>BE: 结果
            BE-->>FE: 200 数据
        else token 过期
            BE-->>FE: 401 {code: "TOKEN_EXPIRED"}
            FE->>FE: Axios interceptor\n清除 token 跳转 /login
        else token 无效
            BE-->>FE: 401 {code: "TOKEN_INVALID"}
            FE->>FE: 同上
        end
    end
```

---

## 10. CRUD 操作流程

```mermaid
flowchart LR
    subgraph 列表 GET /questions
        L1[JWT 验证\n提取 user_id] --> L2[QuestionRepository\nWHERE user_id=? AND deleted_at IS NULL]
        L2 --> L3{过滤参数\nsubject difficulty status}
        L3 --> L4[分页\npage page_size default=20]
        L4 --> L5[返回 QuestionListOut\nitems total page page_size]
    end

    subgraph 详情 GET /questions/id
        D1[JWT 验证] --> D2[Repository.get_by_id\nWHERE id=? AND user_id=? AND deleted_at IS NULL]
        D2 --> D3{结果?}
        D3 -->|无| D4[404 NOT_FOUND]
        D3 -->|user_id不符| D5[403 FORBIDDEN R1]
        D3 -->|有| D6[生成预签名 URL\n有效期≤1h R23]
        D6 --> D7[返回 QuestionOut\nimage_url + image_url_expires_at]
    end

    subgraph 更新 PATCH /questions/id
        U1[JWT 验证] --> U2[获取记录 + 用户校验]
        U2 --> U3{字段过滤\n只读字段静默忽略\nuser_id confidence_score image_key}
        U3 --> U4[Pydantic 校验\nsubject白名单 difficulty范围]
        U4 --> U5[UPDATE + updated_at=now()]
        U5 --> U6[返回更新后 QuestionOut]
    end

    subgraph 软删除 DELETE /questions/id
        DEL1[JWT 验证] --> DEL2[获取记录 + 用户校验]
        DEL2 --> DEL3{已删除?}
        DEL3 -->|是| DEL4[404 NOT_FOUND]
        DEL3 -->|否| DEL5[UPDATE deleted_at=now()\nR21 禁止物理删除]
        DEL5 --> DEL6[204 No Content]
    end
```

---

## 11. SM-2 复习算法流程

```mermaid
flowchart TD
    START([用户提交评分\n1-5分]) --> VAL{评分范围校验\nge=1 le=5}
    VAL -->|超出范围| ERR[422 INVALID_SCORE]
    VAL -->|合法| FETCH[获取 Question\n校验 user_id R1]

    FETCH --> SCORE{score < 3?}

    subgraph 失败路径 score 1-2
        SCORE -->|是| F1[new_review_count = 0\nnew_interval = 1\nnew_ef = ease_factor 不变]
    end

    subgraph 成功路径 score 3-5
        SCORE -->|否| S1{review_count\n当前值?}
        S1 -->|==0 首次| S2[new_interval = 1]
        S1 -->|==1| S3[new_interval = 6]
        S1 -->|>1| S4[new_interval = round\ninterval_days × ease_factor]
        S2 --> S5[new_review_count = review_count + 1]
        S3 --> S5
        S4 --> S5
        S5 --> S6[new_ef = ef + 0.1 - 5-score × 0.08 + 5-score × 0.02\nmax 1.3 下限]
    end

    F1 --> SAVE
    S6 --> SAVE

    SAVE[UPDATE Question\nease_factor new_ef\ninterval_days new_interval\nreview_count new_count\nnext_review_at = now + new_interval days\nlast_reviewed_at = now]

    SAVE --> LOG[INSERT ReviewLog\n记录变更前后 EF + interval\n只追加 不修改]

    LOG --> RESP[返回 ReviewScoreResponse\nquestion_id score\nease_factor_after interval_days_after\nnext_review_at review_count]
```

---

## 12. 复习模块序列图

```mermaid
sequenceDiagram
    participant U as 用户
    participant FE as Vue 前端
    participant BE as FastAPI 后端
    participant DB as 数据库

    U->>FE: 进入 /review

    FE->>BE: GET /api/v1/review/queue
    BE->>DB: SELECT WHERE user_id=?\nAND next_review_at <= now() OR next_review_at IS NULL\nAND status='confirmed'\nAND deleted_at IS NULL\nORDER BY next_review_at ASC
    DB-->>BE: 待复习题目列表
    BE-->>FE: ReviewQueueOut {items, total, message?}

    alt 队列为空
        FE->>U: 展示"今日任务完成🎉"
    else 有待复习题
        FE->>U: 展示第1题\n隐藏答案和解析

        U->>FE: 点击"查看答案"
        FE->>U: 显示 correct_answer + analysis\n展示 5个评分按钮

        U->>FE: 点击评分按钮(1-5)
        FE->>BE: POST /api/v1/review/{id}/score\n{score: N}
        BE->>BE: SM-2 calculate_next_review
        BE->>DB: UPDATE Question SM-2字段
        BE->>DB: INSERT ReviewLog
        DB-->>BE: 成功
        BE-->>FE: ReviewScoreResponse
        FE->>U: 加载下一题 或 完成页

        U->>FE: 查看统计
        FE->>BE: GET /api/v1/review/stats
        BE->>DB: 统计今日完成/总数/连续天数
        DB-->>BE: 统计数据
        BE-->>FE: ReviewStatsOut
        FE->>U: 展示"🔥 连续N天"等统计
    end
```

---

## 13. 打印模块流程

```mermaid
flowchart TD
    A[用户进入 /print] --> B[加载错题列表\n多选模式]
    B --> C{选择题目\nmax 50道 REQ-P1}
    C -->|超出50| D[禁用更多选择\n提示最多50道]
    C -->|未选择| E[预览按钮禁用]
    C -->|已选择| F[配置打印选项\n布局 card/list/compact\n是否含答案]

    F --> G[POST /api/v1/print/preview\n{question_ids layout include_answer include_analysis}]

    G --> H[JWT 验证\n过滤掉非当前用户题目 R1\n不报错静默过滤]

    H --> I{遍历 question_ids\n获取 Question 记录}

    I --> J{含 image_key?}
    J -->|是| K[生成预签名 URL\n标注图片有效期1h REQ-P3]
    J -->|否| L[跳过 img 标签]

    K --> M{含 LaTeX?}
    L --> M
    M -->|是| N[嵌入 KaTeX 离线资源\nCSS + JS REQ-P2]
    M -->|否| O[纯文本渲染]

    N --> P{布局选择}
    O --> P

    P -->|card| Q[每题独立卡片\npage-break-inside:avoid REQ-P4]
    P -->|list| R[A4 紧凑列表]
    P -->|compact| S[双栏布局]

    Q --> T{include_answer?}
    R --> T
    S --> T
    T -->|true| U[追加答案 + 解析\n分隔线区分 REQ-P5]
    T -->|false| V[不含答案内容]

    U --> W[返回 text/html\nContent-Type: text/html P95≤5s]
    V --> W
    W --> X[前端 window.open 新标签页]
```

---

## 14. 前端路由与页面结构

```mermaid
graph TD
    subgraph 路由守卫 beforeEach
        GUARD{localStorage\nwrongbook_token?}
    end

    subgraph 公开路由
        LOGIN[/login\nLoginPage.vue\n已登录→跳/]
        REGISTER[/register\nRegisterPage.vue]
    end

    subgraph 受保护路由 需要 token
        HOME[/\nHomePage.vue\n错题列表 无限滚动]
        UPLOAD[/upload\nUploadPage.vue\n拍照识别确认]
        DETAIL[/questions/:id\nQuestionDetailPage.vue\n详情+编辑+删除]
        REVIEW[/review\nReviewPage.vue\nSM-2 复习队列]
        PRINT[/print\nPrintPage.vue\n多选打印]
    end

    GUARD -->|无 token| LOGIN
    GUARD -->|有 token| HOME

    HOME -->|点击上传按钮| UPLOAD
    HOME -->|点击题目卡片| DETAIL
    HOME -->|点击复习入口| REVIEW
    HOME -->|点击打印入口| PRINT

    UPLOAD -->|识别确认完成| DETAIL
    DETAIL -->|编辑保存| DETAIL
    DETAIL -->|软删除确认| HOME

    LOGIN -->|登录成功 redirect| HOME
    REGISTER -->|注册成功| HOME

    subgraph Axios Interceptor
        AXIOS_401[401 响应\n→清除 token\n→跳转 /login]
        AXIOS_NET[网络错误\n→Toast 网络异常]
    end
```

---

## 15. 前端识别状态机

```mermaid
stateDiagram-v2
    [*] --> idle : 页面加载

    idle : idle\n显示 DropZone 上传区域
    uploading : uploading\n进度条 正在上传...\n禁用上传按钮
    recognizing : recognizing\nspinner AI识别中...
    confirming : confirming\n展示 RecognitionPreview\nhigh_confidence绿色\npending_review黄色
    saving : saving\n保存中... 禁用确认按钮
    done : done\nToast 保存成功\n跳转题目详情
    error : error\n显示 error_hint\n重试按钮

    idle --> uploading : 用户选择合法文件\n点击上传
    uploading --> recognizing : S3 上传成功
    uploading --> error : 上传失败\n或文件校验失败
    recognizing --> confirming : Bedrock 返回\nstatus != error
    recognizing --> error : Bedrock 返回\nstatus == error
    confirming --> saving : 用户确认\nPOST /api/v1/questions
    confirming --> idle : 用户取消
    saving --> done : 201 创建成功
    saving --> error : 网络错误
    error --> idle : 点击重试

    note right of confirming
        high_confidence: 字段预填 绿标签
        pending_review: 字段可编辑 黄警告
        两种状态均可编辑修正
    end note

    note right of error
        页面刷新→重置为 idle
        不持久化上传状态
    end note
```

---

## 16. 前端组件依赖图

```mermaid
graph TD
    subgraph UploadPage.vue
        UP_STATE[useRecognition\n状态机]
        UP_DROP[UploadDropzone.vue\n拖拽+校验]
        UP_PREV[RecognitionPreview.vue\n候选结果确认卡]
    end

    subgraph RecognitionPreview.vue
        PREV_CONF[high_confidence\n绿色标签 badge-green]
        PREV_PEND[pending_review\n黄色警告 badge-yellow]
        PREV_IMG[图片展示\nimage_url 预签名 R23]
        PREV_SUBJ[学科下拉\n白名单必选]
        PREV_EDIT[可编辑字段\n修正识别错误]
    end

    subgraph HomePage.vue
        HOME_LIST[QuestionCard 列表]
        HOME_FILTER[学科/难度过滤\n重新请求不缓存]
        HOME_EMPTY[空状态引导文案]
    end

    subgraph QuestionDetailPage.vue
        DETAIL_KATEX[KaTeX 渲染\n$...$ 公式]
        DETAIL_IMG[原图展示\nimage_url 点击放大]
        DETAIL_EDIT[编辑模式\nPATCH 保存]
        DETAIL_DEL[删除确认对话框\n软删除]
        DETAIL_REFRESH[URL 到期刷新\n距到期<60s 自动刷新]
    end

    subgraph ReviewPage.vue
        REV_CARD[ReviewCard.vue\n答案翻转]
        REV_SCORE[5个评分按钮\n1完全不会..5完全掌握]
        REV_STATS[今日统计\n🔥连续天数]
    end

    subgraph PrintPage.vue
        PRINT_SELECT[多选题目\nmax 50]
        PRINT_CONFIG[布局/答案配置]
        PRINT_PREVIEW[window.open\n新标签页]
    end

    UP_DROP --> UP_STATE
    UP_PREV --> UP_STATE
    UP_STATE -->|POST recognize| BE_API([后端 API])
    UP_STATE -->|POST questions| BE_API

    HOME_LIST --> BE_API
    HOME_FILTER --> BE_API

    DETAIL_KATEX --> KATEX_LIB([KaTeX 离线库])
    DETAIL_IMG --> S3_URL([预签名 URL])
    DETAIL_EDIT --> BE_API
    DETAIL_DEL --> BE_API
    DETAIL_REFRESH --> BE_API

    REV_CARD --> BE_API
    REV_SCORE --> BE_API
    REV_STATS --> BE_API

    PRINT_SELECT --> BE_API
    PRINT_PREVIEW --> BE_API
```

---

## 17. 错误处理层次

```mermaid
graph TD
    subgraph 前端错误处理
        FE1[本地校验层\n文件类型 文件大小 表单字段]
        FE2[Axios Request Interceptor\n注入 Bearer token]
        FE3[Axios Response Interceptor\n401→清除token→跳/login]
        FE4[组件层\nstatus=error→error_hint+重试\npending_review→黄色警告]
        FE5[全局 Toast\n网络错误 请重试]
    end

    subgraph 后端错误处理
        BE1[路由层 FastAPI\nPydantic 422 自动校验]
        BE2[HTTPException Handler\nmain.py 统一格式化\ndata=null error={code message}]
        BE3[全局 Exception Handler\n500 不暴露 stack trace]
        BE4[业务降级\nBedrock/S3失败→status=error\n不抛5xx]
    end

    subgraph 语义错误码
        EC1[INVALID_CREDENTIALS 401]
        EC2[TOKEN_EXPIRED 401]
        EC3[TOKEN_INVALID 401]
        EC4[DUPLICATE_EMAIL 409]
        EC5[FORBIDDEN 403 R1跨用户]
        EC6[NOT_FOUND 404]
        EC7[INVALID_FILE_TYPE 415]
        EC8[FILE_TOO_LARGE 413]
        EC9[OCR_FAILED 200 业务错误]
        EC10[OCR_FORMAT_ERROR 200]
        EC11[OCR_RATE_LIMITED 200]
        EC12[INVALID_SCORE 422]
        EC13[VALIDATION_ERROR 422]
    end

    FE1 -->|不合法不发请求| 用户提示
    FE2 --> 后端
    后端 --> BE1
    BE1 --> BE2
    BE2 -->|统一格式| FE3
    BE3 --> FE5
    BE4 -->|降级响应| FE4

    BE2 --> EC1
    BE2 --> EC2
    BE2 --> EC3
    BE2 --> EC4
    BE2 --> EC5
    BE2 --> EC6
    BE2 --> EC7
    BE2 --> EC8
    BE2 --> EC9
    BE2 --> EC10
    BE2 --> EC11
    BE2 --> EC12
    BE2 --> EC13
```

---

## 18. 安全边界与用户隔离

```mermaid
graph TD
    subgraph 安全约束全景
        R1[R1 用户数据隔离\n所有DB查询含WHERE user_id=?\nBOLA 防御]
        R16[R16 Magic Bytes 校验\n不信任 Content-Type\n拒绝非图片文件]
        R17[R17 20MB 上限\nContent-Length前置检查\n不读入内存]
        R18[R18 UUID重命名\n原始文件名存 original_filename\n不入S3路径]
        R19[R19 S3 original/只写一次\n禁止覆盖或删除原图]
        R20[R20 S3 key格式\nuser_id/original/uuid.ext]
        R21[R21 软删除\ndeleted_at=now()\n禁止物理删除]
        R22[R22 user_id来源\n只从JWT sub提取\n拒绝客户端传入]
        R23[R23 预签名URL\n≤1h有效期\n不暴露S3原始路径]
        R24[R24 Prompt外置\nprompts/目录\n禁止硬编码]
        BCRYPT[密码存储\nbcrypt cost=12\n$2b$12$开头]
        JWT24H[JWT 24h有效期\nHS256 SECRET_KEY]
        ENUM[防枚举攻击\n邮箱不存在和密码错误\n返回同一错误码]
    end

    subgraph 数据访问控制
        REQ[HTTP 请求] --> JWT_CHECK[JWT 验证\nget_current_user]
        JWT_CHECK -->|提取 user_id| REPO[Repository 层]
        REPO -->|WHERE user_id=?| DB[(数据库)]
        REPO -->|额外校验| OWN{question.user_id\n== current_user.id?}
        OWN -->|否| FORBIDDEN[403 FORBIDDEN]
        OWN -->|是| DATA[返回数据]
    end

    subgraph S3 访问控制
        UPLOAD[上传] -->|PutObject\nkey=user_id/original/uuid| S3B[(S3 Bucket\n禁公开访问)]
        DOWNLOAD[下载] -->|GeneratePresignedUrl\n≤1h R23| PRESIGN[预签名 URL]
        S3B -->|禁止| PUBLIC[公网直接访问]
    end
```

---

## 19. 实现顺序与依赖关系

```mermaid
graph LR
    P1[Plan 1\n后端基础+认证\nUser ORM\nJWT bcrypt\n/auth/register\n/auth/login]

    P2[Plan 2\n识别 API\nS3上传\nBedrock Mock\n/questions/recognize]

    P3[Plan 3\nCRUD API\nQuestion CRUD\n分页过滤\n软删除\n预签名URL]

    P4[Plan 4\nSM-2 复习\nReviewLog ORM\nSM-2算法\n/review/queue\n/review/id/score]

    P5[Plan 5\n打印模块\nKaTeX集成\nHTML生成\n/print/preview]

    P6[Plan 6\n前端\nVue3组件\nMock层\n状态机]

    P7[Plan 7\n前后端联调\n集成测试\nE2E验证]

    P1 --> P2
    P1 --> P3
    P2 --> P3
    P3 --> P4
    P3 --> P5
    P1 --> P6
    P6 -.->|mock并行| P2
    P6 -.->|mock并行| P3
    P6 -.->|mock并行| P4
    P6 -.->|mock并行| P5
    P2 --> P7
    P3 --> P7
    P4 --> P7
    P5 --> P7
    P6 --> P7

    style P1 fill:#4CAF50,color:#fff
    style P2 fill:#2196F3,color:#fff
    style P3 fill:#2196F3,color:#fff
    style P4 fill:#FF9800,color:#fff
    style P5 fill:#9C27B0,color:#fff
    style P6 fill:#F44336,color:#fff
    style P7 fill:#607D8B,color:#fff
```

---

## 20. API 端点全览

```mermaid
graph LR
    subgraph 认证 /api/v1/auth
        A1[POST /register\n201 AuthResponse\n无需认证]
        A2[POST /login\n200 AuthResponse\n无需认证]
    end

    subgraph 题目 /api/v1/questions
        Q1[POST /recognize\n200 RecognitionResultOut\n需要JWT\n不入库]
        Q2[POST /\n201 QuestionOut\n需要JWT\n确认入库]
        Q3[GET /\n200 QuestionListOut\n需要JWT\n分页+过滤]
        Q4[GET /:id\n200 QuestionOut\n需要JWT\n含预签名URL]
        Q5[PATCH /:id\n200 QuestionOut\n需要JWT\n可选字段更新]
        Q6[DELETE /:id\n204 No Content\n需要JWT\n软删除]
    end

    subgraph 复习 /api/v1/review
        R1[GET /queue\n200 ReviewQueueOut\n需要JWT\nnext_review_at<=now]
        R2[POST /:id/score\n200 ReviewScoreResponse\n需要JWT\n1-5分SM-2]
        R3[GET /stats\n200 ReviewStatsOut\n需要JWT\n今日/累计/连续]
    end

    subgraph 打印 /api/v1/print
        P1[POST /preview\ntext/html\n需要JWT\nmax50题]
    end

    JWT[JWT Middleware\nget_current_user\nDepends] --> Q1
    JWT --> Q2
    JWT --> Q3
    JWT --> Q4
    JWT --> Q5
    JWT --> Q6
    JWT --> R1
    JWT --> R2
    JWT --> R3
    JWT --> P1
```

---

## 附录：关键业务边界矩阵

| 层 | 致命性 | 边界场景 | 处理决策 | 规则/REQ |
|---|---|---|---|---|
| 筛选层 | ★★★★★ | 无错误标记图片 | `pending_review` + 提示 | R10 / REQ-12 |
| 内容层 | ★★★★★ | 手写答案混入题干 | `wrong_answer` 分离 | R11 / REQ-14 |
| 内容层 | ★★★★★ | 几何图/电路图 | 强制保留 `image_key` | R12 / REQ-15 |
| AI特性层 | ★★★★★ | Bedrock confidence 缺失 | 默认 0.0 不得 1.0 | R2 / REQ-6 |
| AI特性层 | ★★★★★ | 重复识别同一图片 | 旧记录 `superseded` | R14 / REQ-19 |
| AI特性层 | ★★★★★ | Bedrock 返回非法 JSON | `status=error` 不抛500 | REQ-29 |
| 安全层 | ★★★★★ | user_id 从 JWT sub 提取 | 禁止客户端传入 | R22 |
| 安全层 | ★★★★★ | 跨用户访问资源 | 403 FORBIDDEN | R1 |
| 图像层 | ★★★★★ | EXIF 旋转 | 送 Bedrock 前修正 | REQ-27 |
| 文件层 | ★★★★★ | 非图片文件伪装 | Magic Bytes 校验 | R16 |
