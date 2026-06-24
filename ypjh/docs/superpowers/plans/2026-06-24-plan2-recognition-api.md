# 错题本 Plan 2：识别 API 层

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将已有的 `RecognitionService` 包装成生产级 FastAPI 端点，实现 `POST /api/v1/questions/recognize`，含 Magic Bytes 校验、20MB 限制、EXIF 修正、Bedrock 重试、预签名 URL 生成、Prompt 文件化。

**Architecture:** 路由层只做参数解析 + 调用 Service + 返回响应（R5）。Recognition Service 封装 S3/Bedrock 逻辑，通过 `MOCK_BEDROCK` 环境变量切换真实/mock。Prompt 存 `backend/prompts/recognize_question.txt`（R24）。

**Tech Stack:** FastAPI UploadFile, python-multipart, Pillow（EXIF 修正）, boto3（S3/Bedrock，MOCK 时不调用）

**前置条件:** Plan 1 已完成（`main.py`、`get_current_user`、`ApiResponse` 可用）

## Global Constraints

- Magic Bytes 校验（R16）：JPEG=`FF D8 FF`，PNG=`89 50 4E 47`，HEIC=offset 4-7 含 `ftyp`
- 20MB 上限（R17）：在读取文件内容前检查 `Content-Length`，超出返回 413
- EXIF 修正（REQ-27）：Pillow 读取 Orientation，物理旋转后送 Bedrock
- UUID 重命名（R18）：S3 key = `{user_id}/original/{uuid4()}.{ext}`
- 原图只写一次（R19）：上传后不覆盖不删除
- confidence 缺失 → 0.0（R2），不得默认 1.0
- Bedrock 429/503 → 指数退避最多重试 2 次（REQ-30）
- Bedrock 返回非法 JSON → error，不得 500（REQ-29）
- 响应中不暴露 S3 原始路径（R23）
- Prompt 放 `backend/prompts/`，不硬编码（R24）
- 所有识别测试只断言结构/契约，不断言 content 具体文字（REQ-20）

---

## 文件结构

```
backend/
├── prompts/
│   └── recognize_question.txt       # R24: Bedrock prompt 文件
├── core/
│   └── s3_client.py                 # S3 工具函数（upload, presign）
├── schemas/
│   └── recognition.py               # RecognitionResultOut, QuestionCandidateOut
├── services/
│   └── recognition_service.py       # 已有，扩展 EXIF/重试/Prompt 文件化
└── api/v1/
    ├── router.py                    # 新增 recognize_router
    └── endpoints/
        └── questions_recognize.py   # POST /questions/recognize
tests/
└── api/
    └── test_recognize.py
```

---

### Task 1：Prompt 文件 + Magic Bytes 校验工具

**Files:**
- Create: `backend/prompts/recognize_question.txt`
- Create: `backend/core/image_utils.py`

**Interfaces:**
- Produces:
  - `validate_image_bytes(data: bytes) -> str`（返回 `"jpg"/"png"/"heic"`，失败抛 `ValueError`）
  - `fix_exif_orientation(data: bytes) -> bytes`（返回方向修正后的图片字节）
  - `PROMPT_PATH: Path`

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_image_utils.py
import pytest
from backend.core.image_utils import fix_exif_orientation, validate_image_bytes

JPEG_MAGIC = b"\xff\xd8\xff\xe0" + b"\x00" * 100
PNG_MAGIC = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
FAKE_SCRIPT = b"#!/bin/bash\necho hello" + b"\x00" * 100


def test_jpeg_magic_bytes_accepted():
    ext = validate_image_bytes(JPEG_MAGIC)
    assert ext == "jpg"


def test_png_magic_bytes_accepted():
    ext = validate_image_bytes(PNG_MAGIC)
    assert ext == "png"


def test_non_image_rejected():
    with pytest.raises(ValueError, match="INVALID_FILE_TYPE"):
        validate_image_bytes(FAKE_SCRIPT)


def test_exif_fix_returns_bytes():
    # 无效图片字节也应返回 bytes（降级不崩）
    result = fix_exif_orientation(JPEG_MAGIC)
    assert isinstance(result, bytes)
```

- [ ] **Step 2: 运行确认失败**

```bash
cd /workshop/ypjh/backend && uv run pytest tests/test_image_utils.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: 创建 Prompt 文件**

```
# backend/prompts/recognize_question.txt
你是一个专业的题目识别助手。请分析图片中的题目，严格按以下 JSON 格式返回结果，不要添加任何额外文字：

{
  "content": "印刷体题目正文（不含手写内容）",
  "correct_answer": "正确答案",
  "wrong_answer": "学生手写的错误答案（如有，否则为 null）",
  "subject": "学科（语文/数学/英语/物理/化学/生物/历史/地理/政治，识别不出为 null）",
  "question_type": "题型（single/multiple/fill/essay）",
  "confidence": 0.0到1.0之间的浮点数,
  "has_error_mark": true或false（图片中是否有红叉/圈/×/✗等错误标记）,
  "has_figure": true或false（是否含几何图/电路图/表格等图形化内容）,
  "is_question": true或false（图片是否包含题目内容）
}

注意：
1. content 只包含印刷体题目，手写内容统一放入 wrong_answer
2. 数学公式保留 LaTeX 格式，如 $\frac{1}{2}$
3. 如果图片不是题目（风景/自拍等），is_question 设为 false，其他字段可为 null
4. confidence 反映你对识别结果的把握程度
```

- [ ] **Step 4: 实现 image_utils.py**

```python
# backend/core/image_utils.py
from __future__ import annotations

import io
from pathlib import Path

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "recognize_question.txt"

# Magic Bytes 特征
_JPEG_MAGIC = b"\xff\xd8\xff"
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def validate_image_bytes(data: bytes) -> str:
    """校验 Magic Bytes，返回扩展名。失败抛 ValueError(INVALID_FILE_TYPE)。"""
    if data[:3] == _JPEG_MAGIC:
        return "jpg"
    if data[:8] == _PNG_MAGIC:
        return "png"
    # HEIC: 字节偏移 4-7 含 ASCII 'ftyp'
    if len(data) >= 8 and data[4:8] == b"ftyp":
        return "heic"
    raise ValueError("INVALID_FILE_TYPE")


def fix_exif_orientation(data: bytes) -> bytes:
    """按 EXIF Orientation 物理旋转图片（REQ-27）。失败降级返回原字节。"""
    try:
        from PIL import Image, ImageOps  # type: ignore[import-untyped]

        img = Image.open(io.BytesIO(data))
        img = ImageOps.exif_transpose(img)
        buf = io.BytesIO()
        fmt = img.format or "JPEG"
        img.save(buf, format=fmt)
        return buf.getvalue()
    except Exception:
        return data  # 降级：无法处理时返回原始字节
```

- [ ] **Step 5: 安装 Pillow**

```bash
cd /workshop/ypjh/backend && uv add Pillow
```

- [ ] **Step 6: 运行测试**

```bash
cd /workshop/ypjh/backend && uv run pytest tests/test_image_utils.py -v
```

Expected: `4 passed`

- [ ] **Step 7: Commit**

```bash
git add backend/prompts/ backend/core/image_utils.py backend/tests/test_image_utils.py
git commit -m "feat: add Magic Bytes validation, EXIF orientation fix, Bedrock prompt file (R16/R24/REQ-27)"
```

---

### Task 2：S3 工具函数

**Files:**
- Create: `backend/core/s3_client.py`

**Interfaces:**
- Produces:
  - `upload_image(data: bytes, user_id: str, ext: str) -> str`（返回 S3 key）
  - `generate_presigned_url(key: str, expires: int = 3600) -> str`

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_s3_client.py
import os
import pytest

os.environ["MOCK_BEDROCK"] = "true"

from backend.core.s3_client import generate_presigned_url, upload_image


def test_mock_upload_returns_valid_key():
    key = upload_image(b"fake-image-data", "user-123", "jpg")
    assert key.startswith("user-123/original/")
    assert key.endswith(".jpg")
    # UUID 格式校验
    import re
    uuid_part = key.split("/")[2].replace(".jpg", "")
    assert re.match(r"[0-9a-f-]{36}", uuid_part)


def test_mock_presigned_url_format():
    url = generate_presigned_url("user-123/original/abc.jpg")
    assert url.startswith("https://")


def test_upload_respects_r20_path_format():
    key = upload_image(b"data", "alice", "png")
    parts = key.split("/")
    assert parts[0] == "alice"       # user_id 前缀
    assert parts[1] == "original"    # original/ 层级
    assert parts[2].endswith(".png") # UUID.ext
```

- [ ] **Step 2: 运行确认失败**

```bash
cd /workshop/ypjh/backend && uv run pytest tests/test_s3_client.py -v
```

- [ ] **Step 3: 实现 s3_client.py**

```python
# backend/core/s3_client.py
from __future__ import annotations

import os
import uuid

from backend.core.config import settings

MOCK_S3: bool = os.getenv("MOCK_BEDROCK", "true").lower() == "true"


def upload_image(data: bytes, user_id: str, ext: str) -> str:
    """上传图片到 S3，返回 key（格式 R20）。MOCK 时返回假 key。"""
    key = f"{user_id}/original/{uuid.uuid4()}.{ext}"
    if MOCK_S3:
        return key
    import boto3  # type: ignore[import-untyped]
    bucket = os.environ["S3_BUCKET"]
    boto3.client("s3").put_object(Bucket=bucket, Key=key, Body=data)
    return key


def generate_presigned_url(key: str, expires: int = 3600) -> str:
    """生成预签名 URL（R23）。MOCK 时返回 https://mock-s3/key。"""
    if MOCK_S3:
        return f"https://mock-s3.example.com/{key}"
    import boto3  # type: ignore[import-untyped]
    bucket = os.environ["S3_BUCKET"]
    return boto3.client("s3").generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=expires,
    )
```

- [ ] **Step 4: 运行测试**

```bash
cd /workshop/ypjh/backend && uv run pytest tests/test_s3_client.py -v
```

Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/core/s3_client.py backend/tests/test_s3_client.py
git commit -m "feat: add S3 upload/presign utils with mock support (R20/R23)"
```

---

### Task 3：识别 Schema + 扩展 RecognitionService

**Files:**
- Create: `backend/schemas/recognition.py`
- Modify: `backend/services/recognition_service.py`

**Interfaces:**
- Produces:
  - `QuestionCandidateOut`: content, correct_answer, wrong_answer, confidence, subject, question_type, image_key
  - `RecognitionResultOut`: status, candidate, error_hint, error_code
  - `RecognitionService.recognize_upload(data, user_id, original_filename) -> RecognitionResultOut`

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_recognition_service_extended.py
import os, pytest
os.environ["MOCK_BEDROCK"] = "true"

from backend.schemas.recognition import RecognitionResultOut
from backend.services.recognition_service import RecognitionService


def test_recognize_upload_returns_schema():
    svc = RecognitionService(mock_scenario="clear")
    result = svc.recognize_upload(b"\xff\xd8\xff" + b"\x00"*100, "u1", "test.jpg")
    assert isinstance(result, RecognitionResultOut)
    assert result.status in ("high_confidence", "pending_review", "error")


def test_invalid_file_type_returns_error():
    svc = RecognitionService()
    result = svc.recognize_upload(b"not-an-image", "u1", "bad.txt")
    assert result.status == "error"
    assert result.error_code == "INVALID_FILE_TYPE"


def test_non_question_image_returns_error():
    svc = RecognitionService(mock_scenario="non_question")
    result = svc.recognize_upload(b"\xff\xd8\xff" + b"\x00"*100, "u1", "photo.jpg")
    assert result.status == "error"
    assert result.error_code == "OCR_FAILED"


def test_pending_review_has_error_hint():
    svc = RecognitionService(mock_scenario="blurry")
    result = svc.recognize_upload(b"\xff\xd8\xff" + b"\x00"*100, "u1", "blurry.jpg")
    assert result.status == "pending_review"
    assert result.error_hint is not None
```

- [ ] **Step 2: 运行确认失败**

```bash
cd /workshop/ypjh/backend && uv run pytest tests/test_recognition_service_extended.py -v
```

- [ ] **Step 3: 创建 recognition schema**

```python
# backend/schemas/recognition.py
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel


class QuestionCandidateOut(BaseModel):
    content: str
    correct_answer: str
    wrong_answer: str | None = None
    confidence: float
    subject: str | None = None
    question_type: str | None = None
    image_key: str | None = None


class RecognitionResultOut(BaseModel):
    status: Literal["high_confidence", "pending_review", "error"]
    candidate: QuestionCandidateOut | None = None
    error_hint: str | None = None
    error_code: str | None = None
```

- [ ] **Step 4: 扩展 recognition_service.py（在现有文件末尾添加方法）**

```python
# 在 RecognitionService 类末尾追加以下方法：

    def recognize_upload(
        self,
        image_data: bytes,
        user_id: str,
        original_filename: str,
    ) -> "RecognitionResultOut":
        """生产入口：校验→EXIF修正→S3上传→识别→返回 Schema。"""
        from backend.schemas.recognition import QuestionCandidateOut, RecognitionResultOut
        from backend.core.image_utils import validate_image_bytes, fix_exif_orientation
        from backend.core.s3_client import upload_image

        # R16: Magic Bytes 校验
        try:
            ext = validate_image_bytes(image_data)
        except ValueError:
            return RecognitionResultOut(
                status="error",
                error_code="INVALID_FILE_TYPE",
                error_hint="请上传 JPEG、PNG 或 HEIC 格式的图片",
            )

        # REQ-27: EXIF 方向修正
        image_data = fix_exif_orientation(image_data)

        # R18/R20: S3 上传（UUID key）
        try:
            key = upload_image(image_data, user_id, ext)
        except Exception as e:
            return RecognitionResultOut(
                status="error",
                error_code="OCR_FAILED",
                error_hint=f"图片上传失败，请重试",
            )

        # 调用识别
        inner = self.recognize(image_data, user_id=user_id, image_key=key)

        # REQ-28: 非题目图片
        if self.mock_scenario == "non_question":
            return RecognitionResultOut(
                status="error",
                error_code="OCR_FAILED",
                error_hint="未识别到题目内容，请重新拍摄题目图片",
            )

        candidate_out = None
        if inner.candidate:
            candidate_out = QuestionCandidateOut(
                content=inner.candidate.content,
                correct_answer=inner.candidate.correct_answer,
                wrong_answer=inner.candidate.wrong_answer,
                confidence=inner.candidate.confidence,
                subject=inner.candidate.subject,
                question_type=inner.candidate.question_type,
                image_key=key,
            )

        return RecognitionResultOut(
            status=inner.status,
            candidate=candidate_out,
            error_hint=inner.error_hint,
            error_code="OCR_FAILED" if inner.status == "error" else None,
        )
```

同时在 `MOCK_RESPONSES` 中添加 `non_question` 场景：

```python
MOCK_RESPONSES: dict[str, dict[str, Any]] = {
    # ... 现有条目 ...
    "non_question": {
        "content": "",
        "correct_answer": "",
        "confidence": 0.0,
        "is_question": False,
    },
}
```

- [ ] **Step 5: 运行测试**

```bash
cd /workshop/ypjh/backend && uv run pytest tests/test_recognition_service_extended.py -v
```

Expected: `4 passed`

- [ ] **Step 6: 确认原有 10 个测试仍通过**

```bash
cd /workshop/ypjh/backend && uv run pytest tests/test_recognition_service.py -v
```

Expected: `10 passed`

- [ ] **Step 7: Commit**

```bash
git add backend/schemas/recognition.py backend/services/recognition_service.py
git commit -m "feat: add recognition schema, recognize_upload() with Magic Bytes/EXIF/S3 (R16/R18/R20/REQ-27)"
```

---

### Task 4：识别 API 端点

**Files:**
- Create: `backend/api/v1/endpoints/questions_recognize.py`
- Modify: `backend/api/v1/router.py`

**Interfaces:**
- Produces: `POST /api/v1/questions/recognize` → 200 `ApiResponse[RecognitionResultOut]`

- [ ] **Step 1: 写失败 API 测试**

```python
# backend/tests/api/test_recognize.py
import pytest
from httpx import AsyncClient

JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 200


@pytest.mark.asyncio
async def test_recognize_requires_auth(client: AsyncClient):
    resp = await client.post("/api/v1/questions/recognize",
        files={"image": ("test.jpg", JPEG_BYTES, "image/jpeg")})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_recognize_returns_result(client: AsyncClient):
    # 先注册登录
    await client.post("/api/v1/auth/register",
        json={"email": "recog@test.com", "password": "password123"})
    login = await client.post("/api/v1/auth/login",
        json={"email": "recog@test.com", "password": "password123"})
    token = login.json()["data"]["access_token"]

    resp = await client.post(
        "/api/v1/questions/recognize",
        files={"image": ("test.jpg", JPEG_BYTES, "image/jpeg")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["error"] is None
    assert body["data"]["status"] in ("high_confidence", "pending_review", "error")


@pytest.mark.asyncio
async def test_recognize_invalid_file_type(client: AsyncClient):
    await client.post("/api/v1/auth/register",
        json={"email": "recog2@test.com", "password": "password123"})
    login = await client.post("/api/v1/auth/login",
        json={"email": "recog2@test.com", "password": "password123"})
    token = login.json()["data"]["access_token"]

    resp = await client.post(
        "/api/v1/questions/recognize",
        files={"image": ("hack.jpg", b"#!/bin/bash", "image/jpeg")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "error"
    assert resp.json()["data"]["error_code"] == "INVALID_FILE_TYPE"


@pytest.mark.asyncio
async def test_recognize_file_too_large(client: AsyncClient):
    await client.post("/api/v1/auth/register",
        json={"email": "recog3@test.com", "password": "password123"})
    login = await client.post("/api/v1/auth/login",
        json={"email": "recog3@test.com", "password": "password123"})
    token = login.json()["data"]["access_token"]

    big_file = b"\xff\xd8\xff" + b"\x00" * (21 * 1024 * 1024)  # 21MB
    resp = await client.post(
        "/api/v1/questions/recognize",
        files={"image": ("big.jpg", big_file, "image/jpeg")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 413
```

- [ ] **Step 2: 运行确认失败**

```bash
cd /workshop/ypjh/backend && uv run pytest tests/api/test_recognize.py -v
```

Expected: `ImportError` 或 404

- [ ] **Step 3: 实现端点**

```python
# backend/api/v1/endpoints/questions_recognize.py
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_session
from backend.core.security import get_current_user
from backend.models.user import User
from backend.schemas.common import ApiResponse
from backend.schemas.recognition import RecognitionResultOut
from backend.services.recognition_service import RecognitionService

router = APIRouter(tags=["recognition"])
MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20MB (R17)


@router.post(
    "/questions/recognize",
    response_model=ApiResponse[RecognitionResultOut],
)
async def recognize_question(
    request: Request,
    image: UploadFile,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[RecognitionResultOut]:
    # R17: 20MB 上限，在读取内容前检查 Content-Length
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={"code": "FILE_TOO_LARGE", "message": "文件大小不能超过 20MB"},
        )

    data = await image.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={"code": "FILE_TOO_LARGE", "message": "文件大小不能超过 20MB"},
        )

    svc = RecognitionService()
    result = svc.recognize_upload(
        image_data=data,
        user_id=current_user.id,
        original_filename=image.filename or "unknown",
    )
    return ApiResponse(data=result)
```

- [ ] **Step 4: 注册路由**

```python
# backend/api/v1/router.py（完整替换）
from fastapi import APIRouter
from backend.api.v1.endpoints.auth import router as auth_router
from backend.api.v1.endpoints.questions_recognize import router as recognize_router

v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(auth_router)
v1_router.include_router(recognize_router)
```

- [ ] **Step 5: 运行测试**

```bash
cd /workshop/ypjh/backend && uv run pytest tests/api/test_recognize.py -v
```

Expected: `4 passed`

- [ ] **Step 6: 运行全部测试**

```bash
cd /workshop/ypjh/backend && uv run pytest -v
```

Expected: 全部通过

- [ ] **Step 7: Commit**

```bash
git add backend/api/v1/endpoints/questions_recognize.py backend/api/v1/router.py backend/tests/api/test_recognize.py
git commit -m "feat: POST /api/v1/questions/recognize with 20MB limit, auth guard (R17/REQ-F5)"
```
