# EARS 触发条件索引

> **用途**：Agent 快速查阅"遇到什么情况 → 触发哪条规则/需求 → 应该做什么"。
> 原始规则叙述见 `rules/personal.md`；原始需求见 `spec/recognize/requirements.md`。
> 本文件只写触发条件，不重复解释原因。

---

## 一、规则触发条件（R1-R24）

### 数据安全与用户隔离

```
If   [Agent 要写不含 user_id 过滤的查询函数],
     the agent shall 停止并询问用户确认后再继续。 → R1 [MUST]

If   [路由函数签名中出现 user_id: str = Query(...) 或 user_id: str = Body(...)],
     the agent shall 改为 current_user: User = Depends(get_current_user)，
     从 current_user.id 取 user_id，不接受客户端传入值。 → R22 [MUST]
```

### AI 输出处理

```
If   [Bedrock 返回 JSON 中 confidence 字段缺失],
     the system shall 将 confidence 置为 0.0，不得使用任何正数默认值。 → R2 [MUST]

If   [confidence_score < 0.7],
     the system shall 将 status 设为 pending_review，不得直接入库。 → R4 [MUST]

If   [Bedrock 返回 content 或 correct_answer 为空/缺失],
     the system shall 在 schema 校验前用占位符"（识别内容为空）"替换，
     不得让 ValidationError 直接暴露给用户。 → R9 [SHOULD]

If   [图片中无任何错误标记（红叉/圈/×/✗/错）],
     the system shall 将结果标记为 status=pending_review，
     提示"未检测到错误标记，请确认是否为错题"，不得直接入库。 → R10 [MUST]

If   [Bedrock prompt 中缺少"分离印刷体题目与手写答案"的明确指令],
     the agent shall 补充分离指令后再继续，不得跳过。 → R11 [MUST]

If   [识别结果含几何图形/电路图/表格等无法完整文本化的内容（has_figure=true）],
     the system shall 保留 image_key，不得仅凭文本描述入库。 → R12 [MUST]

If   [content 含 LaTeX 标记（$/\frac/\sqrt/\int 等）且 subject=数学],
     the system shall 以 LaTeX 格式存储，前端用 KaTeX 渲染，
     不得降级为纯文本。 → R13 [SHOULD]

If   [同一 image_key 发起二次识别且已有 status=confirmed 记录],
     the system shall 将新结果标记为 pending_review，
     用户确认后旧记录标为 superseded，不得自动覆盖。 → R14 [SHOULD]

If   [content="（识别内容为空）" 且 image_key=None],
     the system shall 拒绝入库，返回 status=error，
     提示用户重新拍照。 → R15 [SHOULD]
```

### 文件上传与 S3 存储

```
If   [上传文件的 Magic Bytes 与 JPEG(FF D8 FF)/PNG(89 50 4E 47)/HEIC(ftyp) 不符],
     the system shall 返回 HTTP 415，错误码 INVALID_FILE_TYPE，
     不得依赖 Content-Type header 或文件扩展名进行校验。 → R16 [MUST]

If   [上传请求的 Content-Length 超过 20MB],
     the system shall 在读取文件内容前返回 HTTP 413，错误码 FILE_TOO_LARGE。 → R17 [MUST]

If   [Agent 要将原始文件名直接用作 S3 key],
     the agent shall 改为用 uuid4() 生成文件名，
     原始文件名只存入 original_filename 字段。 → R18 [MUST]

While [系统执行任何业务逻辑（识别/更新/软删除）],
     the system shall 不对 S3 {user_id}/original/ 路径下的文件执行覆盖或删除。 → R19 [MUST]

When  [图片上传成功需要生成 S3 key],
     the system shall 使用格式 {user_id}/original/{uuid4()}.{ext}，
     不得偏离此路径结构。 → R20 [MUST]

When  [API 响应中含图片的 Question 对象],
     the system shall 生成预签名 URL（有效期 ≤1h）作为 image_url 返回，
     并附 image_url_expires_at 时间戳，不得在响应中暴露 S3 原始路径。 → R23 [MUST]
```

### 数据存储

```
If   [Agent 要将整段识别文本作为裸字符串直接赋值给 Question 字段（如 question.content = raw_text）],
     the agent shall 停止并要求通过结构化 Question 对象存储。 → R3 [MUST]

If   [Agent 要对 Question 记录执行 session.delete() 或 DELETE FROM SQL],
     the agent shall 改为软删除：设 deleted_at=now()，
     所有查询自动过滤 WHERE deleted_at IS NULL。 → R21 [MUST]
```

### 代码架构

```
If   [Agent 要在 FastAPI 路由 handler 中写 session.query() 或 session.add()],
     the agent shall 将逻辑下沉到 service 层，
     偏离时在代码注释和 commit message 中说明原因。 → R5 [SHOULD]

If   [Agent 要在 async 函数中使用 requests/open()/time.sleep() 等同步 IO],
     the agent shall 优先替换为 async 等价品（httpx.AsyncClient/aiofiles/asyncio.sleep），
     无替代品时用 asyncio.to_thread() 包装并在注释中说明。 → R6 [SHOULD]

If   [Agent 要在 Vue 组件 <template> 或 <script setup> 中直接调用 questionsApi.xxx()],
     the agent shall 先创建对应 Composable（useXxx.ts）封装再在组件中调用。 → R7 [SHOULD]

When  [Agent 编写 Bedrock 调用/图片预处理/识别结果解析逻辑],
     the agent may 集中放置在 recognition_service.py。 → R8 [CAN]

If   [Agent 要在 service 函数体内写多行 Bedrock prompt 字符串常量],
     the agent shall 在 backend/prompts/ 创建对应 .txt 文件，
     通过文件读取方式加载，不得硬编码。 → R24 [MUST]
```

---

## 二、需求触发条件（REQ-1 至 REQ-26）

> 完整 Gherkin 场景见 `spec/recognize/requirements.md`。

### 正常流

```
When  [用户上传一张包含题目的清晰图片],
     the system shall 调用 Bedrock 识别，在 10 秒内返回候选题目。 → REQ-1

When  [Bedrock 返回 confidence >= 0.7],
     the system shall 将识别结果展示给用户确认，不直接入库。 → REQ-2

When  [用户确认识别结果无误],
     the system shall 将结构化 Question 对象入库，status=confirmed。 → REQ-3

When  [一条 Question 成功入库],
     the system shall 初始化 SM-2 参数（ease_factor=2.5），next_review_at=明天。 → REQ-4
```

### 边界条件

```
If   [Bedrock 返回 confidence < 0.7],
     the system shall 标记 status=pending_review，提示"识别不确定，请手动核对"。 → REQ-5

If   [Bedrock 返回 JSON 中不含 confidence 字段],
     the system shall 视为 0.0，触发 REQ-5 兜底流程。 → REQ-6

If   [图片分辨率低于可识别阈值（模糊/反光/纯暗）],
     the system shall 返回 confidence=0.0，error_hint="图像质量不足"，不得返回 500。 → REQ-7

If   [图片中包含多道题目],
     the system shall 识别并返回题目列表，用户逐条确认或批量丢弃。 → REQ-8

If   [题目包含数学公式],
     the system shall 在识别结果中保留 LaTeX 格式，前端用 KaTeX 渲染。 → REQ-9

While [系统使用 Bedrock 进行识别],
     the system shall 仅验证响应结构和契约，不断言 content 等具体文字内容。 → REQ-10

If   [Bedrock 返回的 subject 不在白名单（语文/数学/英语/物理/化学/生物/历史/地理/政治）],
     the system shall 将 subject 置为 None，提示用户手动选择学科。 → REQ-11
```

### 五层致命边界

```
If   [图片中题目没有任何错误标记（红叉/圈/×/✗）],
     the system shall 标记 status=pending_review，提示"未检测到错误标记"。 → REQ-12 ★★★★★

If   [一道题的学生答案部分正确（如多选题选对了部分选项）],
     the system shall 将整题标记为错题入库，wrong_answer 保留完整学生作答。 → REQ-13 ★★★★☆

If   [图片同时包含印刷体题目和手写答案],
     the system shall 印刷体存 content，手写内容存 wrong_answer，不得合并。 → REQ-14 ★★★★★

If   [题目包含几何图形/电路图/表格等无法完整文本化的内容],
     the system shall 在 image_key 中保留原始图片引用，前端展示原图。 → REQ-15 ★★★★★

If   [识别结果包含数学公式（分数/根号/上标/积分）],
     the system shall 以 LaTeX 格式存储，前端用 KaTeX 渲染。 → REQ-16 ★★★☆☆

If   [图片题目关键区域被遮挡（手指/阴影/物体），部分字段为空],
     the system shall 返回 status=pending_review，error_hint="题目内容不完整，请重新拍照或手动补全"。 → REQ-17 ★★★☆☆

If   [图片存在严重反光/过曝/倾斜（confidence < 0.3）],
     the system shall 在 error_hint 中明确说明图片质量原因，不得用通用"识别不确定"。 → REQ-18 ★★☆☆☆

While [用户对同一 image_key 发起二次识别],
     the system shall 将新结果以 pending_review 展示，用户确认后旧记录标为 superseded，
     不得自动覆盖已确认记录。 → REQ-19 ★★★★★

While [系统运行识别相关的自动化测试],
     the system shall 仅断言响应结构（字段存在性/类型/范围），
     不断言 content/correct_answer/wrong_answer 的具体文字。 → REQ-20 ★★★★★
```

### 上传与存储约束

```
If   [上传文件 Magic Bytes 与 JPEG/PNG/HEIC 特征不符],
     the system shall 返回 HTTP 415，错误码 INVALID_FILE_TYPE。 → REQ-21 ★★★★★

If   [单个上传文件超过 20MB],
     the system shall 在读取文件内容前返回 HTTP 413，错误码 FILE_TOO_LARGE。 → REQ-22 ★★★★☆

When  [图片上传成功],
     the system shall 使用 {user_id}/original/{uuid4()}.{ext} 生成 S3 key，
     原始文件名存 original_filename 字段。 → REQ-23 ★★★★☆

While [系统运行任何业务逻辑],
     the system shall 不对 S3 {user_id}/original/ 路径下的文件执行覆盖或删除。 → REQ-24 ★★★★★

When  [用户删除一条错题记录],
     the system shall 设置 deleted_at=now()，不执行物理删除，
     所有查询自动过滤 WHERE deleted_at IS NULL。 → REQ-25 ★★★★☆

When  [后端返回含图片的 Question 对象],
     the system shall 通过 generate_presigned_url() 生成图片地址（≤1h），
     响应包含 image_url 和 image_url_expires_at，禁止暴露 S3 原始路径。 → REQ-26 ★★★★★

If   [上传图片的 EXIF Orientation 标记不为 1（存在旋转信息）],
     the system shall 在送入 Bedrock 前按 EXIF 做物理旋转修正，
     旋转操作在副本上执行，不修改 S3 original/ 原图。 → REQ-27 ★★★★★

If   [Bedrock 识别结果中无可识别的题目结构（无题干/无解题内容）],
     the system shall 返回 status=error，error_hint="未识别到题目内容，请重新拍摄题目图片"，
     不得让非题目图片的识别结果进入确认流程。 → REQ-28 ★★★★☆

If   [Bedrock API 响应体不是合法 JSON（语法错误/截断/空响应体）],
     the system shall 捕获 JSONDecodeError，返回 HTTP 200，status=error，
     error_hint="识别服务返回格式异常，请重试"，不得返回 500。 → REQ-29 ★★★★★

If   [Bedrock API 返回 HTTP 429 或 503],
     the system shall 按指数退避最多重试 2 次（间隔 1s、2s），
     第 3 次仍失败则返回 status=error，error_hint="识别服务繁忙，请稍后重试"。 → REQ-30 ★★★★☆
```

---

## 三、快速诊断：触发条件速查表

| 场景关键词 | 触发规则/需求 | 级别 |
|---|---|---|
| 查询函数缺 user_id | R1, REQ-1~26（所有查询） | MUST |
| confidence 字段缺失 | R2, REQ-6 | MUST |
| 裸字符串入库 | R3 | MUST |
| confidence < 0.7 | R4, REQ-5 | MUST |
| 无错误标记图片 | R10, REQ-12 | MUST |
| 手写/印刷体混合 | R11, REQ-14 | MUST |
| 含几何图/电路图 | R12, REQ-15 | MUST |
| 重复识别同一图 | R14, REQ-19 | SHOULD |
| 上传文件类型校验 | R16, REQ-21 | MUST |
| 文件超过 20MB | R17, REQ-22 | MUST |
| S3 key 生成 | R18, R20, REQ-23 | MUST |
| 删除题目操作 | R21, REQ-25 | MUST |
| 路由接收 user_id 参数 | R22 | MUST |
| API 返回图片字段 | R23, REQ-26 | MUST |
| Prompt 字符串硬编码 | R24 | MUST |
| 断言识别文字内容 | REQ-10, REQ-20 | MUST |
| 图片 EXIF 方向非 1 | REQ-27 | MUST |
| 上传图片非题目图片 | REQ-28 | SHOULD |
| Bedrock 返回非法 JSON | REQ-29 | MUST |
| Bedrock 429/503 错误 | REQ-30 | SHOULD |
