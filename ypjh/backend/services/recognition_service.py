"""识别服务：封装 Bedrock 调用、S3 上传、schema 校验、状态决策。"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Literal, cast

# 将 mcp/ 工具加入路径（开发阶段权宜之计；生产环境应安装为 Python 包）
_MCP_PATH = str(Path(__file__).parent.parent.parent / "mcp")
if _MCP_PATH not in sys.path:
    sys.path.insert(0, _MCP_PATH)
from check_question_schema import (
    CONFIDENCE_THRESHOLD,
    QuestionCandidate,
    check_question_schema,
    is_high_confidence,
)

# ── Mock 配置 ─────────────────────────────────────────────────────────────
# 通过环境变量控制，无需修改代码即可切换到真实 Bedrock
# 用法: MOCK_BEDROCK=false uv run uvicorn main:app --reload

MOCK_BEDROCK: bool = os.getenv("MOCK_BEDROCK", "true").lower() == "true"

SUPPORTED_SUBJECTS = frozenset({
    "语文", "数学", "英语", "物理", "化学", "生物", "历史", "地理", "政治",
})

MOCK_RESPONSES: dict[str, dict[str, Any]] = {
    "clear": {
        "content": "已知 f(x) = x² + 2x + 1，求 f(3) 的值。",
        "correct_answer": "16",
        "confidence": 0.92,
        "subject": "数学",
        "question_type": "fill",
    },
    "blurry": {
        "content": "模糊识别结果",
        "correct_answer": "不确定",
        "confidence": 0.45,
    },
    # empty: confidence 缺失，content/answer 也残缺 — 模拟 Bedrock 返回残缺 JSON
    "empty": {
        "content": "",
        "correct_answer": "",
    },
    "non_question": {
        "content": "",
        "correct_answer": "",
        "confidence": 0.0,
        "is_question": False,
    },
}


# ── 主流程 ────────────────────────────────────────────────────────────────


class RecognitionResult:
    """识别结果，包含状态和候选题目。"""

    def __init__(
        self,
        status: str,
        candidate: QuestionCandidate | None = None,
        error_hint: str | None = None,
        image_key: str | None = None,
    ) -> None:
        self.status = status          # high_confidence / pending_review / error
        self.candidate = candidate
        self.error_hint = error_hint
        self.image_key = image_key


class RecognitionService:
    """识别服务。依赖 check_question_schema 做 R2 校验，严格执行 R1/R4。"""

    def __init__(self, mock_scenario: str = "clear") -> None:
        self.mock_scenario = mock_scenario

    def recognize(
        self,
        image_bytes: bytes,
        user_id: str,
        image_key: str | None = None,
    ) -> RecognitionResult:
        """
        主入口：上传图片 → 调用 Bedrock → 校验 → 决策状态。

        user_id 为当前用户 ID，用于 R1 隔离（传给下游 QuestionService）。
        返回 RecognitionResult，调用方根据 status 决定是否展示确认界面。
        """
        # Step 1: 上传 S3（仅当调用方未提供 image_key 时；recognize_upload 已上传则跳过）
        if image_key is None:
            try:
                image_key = self._upload_to_s3(image_bytes)
            except Exception as e:
                return RecognitionResult(
                    status="error",
                    error_hint=f"图片上传失败，请重试：{e}",
                )
        key = image_key

        # Step 2: 调用 Bedrock
        try:
            raw = self._call_bedrock(key)
        except Exception as e:
            return RecognitionResult(status="error", error_hint=f"识别服务暂时不可用：{e}")

        # REQ-28: 非题目图片（Bedrock 明确返回 is_question=False）
        if raw.get("is_question") is False:
            return RecognitionResult(
                status="error",
                error_hint="未识别到题目内容，请重新拍摄题目图片",
                image_key=key,
            )

        # Step 3: R2 — confidence 缺失按 0 处理（不得默认 1.0）
        if "confidence" not in raw:
            raw["confidence"] = 0.0

        # Step 3b: R9 — 内容字段缺失时用占位符降级（保证 schema 通过，引导用户填写）
        if not raw.get("content"):
            raw["content"] = "（识别内容为空）"
        if not raw.get("correct_answer"):
            raw["correct_answer"] = "（识别答案为空）"

        # Step 3c: REQ-11 — 学科白名单校验，不在白名单则置为 None
        if raw.get("subject") and raw["subject"] not in SUPPORTED_SUBJECTS:
            raw["subject"] = None

        # Step 4: schema 校验
        try:
            candidate = check_question_schema(raw)
        except ValueError as e:
            return RecognitionResult(status="error", error_hint=f"识别结果格式异常：{e}")

        # Step 5: R4 — 置信度决策（不直接入库，返回供用户确认；user_id 随结果向下传递）
        if is_high_confidence(candidate):
            return RecognitionResult(
                status="high_confidence",
                candidate=candidate,
                image_key=key,
            )
        else:
            return RecognitionResult(
                status="pending_review",
                candidate=candidate,
                error_hint=f"识别置信度 {candidate.confidence:.0%}，请手动核对",
                image_key=key,
            )

    def _upload_to_s3(self, image_bytes: bytes) -> str:
        """上传图片到 S3，返回 image_key。"""
        if MOCK_BEDROCK:
            return f"questions/mock-{len(image_bytes)}.jpg"
        raise NotImplementedError("真实 S3 上传未实现，设置 MOCK_BEDROCK=true 使用 mock")

    def _call_bedrock(self, image_key: str) -> dict[str, Any]:
        """调用 Bedrock 视觉模型，返回原始 dict。"""
        if MOCK_BEDROCK:
            return dict(MOCK_RESPONSES.get(self.mock_scenario, MOCK_RESPONSES["clear"]))
        # R24: prompt 必须从文件加载，不得硬编码
        from backend.core.image_utils import PROMPT_PATH
        raise NotImplementedError(
            f"真实 Bedrock 调用未实现，设置 MOCK_BEDROCK=true 使用 mock。"
            f"实现时需从 {PROMPT_PATH} 加载系统 Prompt（R24）。"
        )

    def recognize_upload(
        self,
        image_data: bytes,
        user_id: str,
        original_filename: str,
    ) -> "RecognitionResultOut":
        """生产入口：校验→EXIF修正→S3上传→识别→返回 Schema。"""
        from backend.schemas.recognition import QuestionCandidateOut, RecognitionResultOut
        from backend.core.image_utils import validate_image_bytes, fix_exif_orientation
        from backend.core.s3_client import upload_image, generate_presigned_url

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
        except Exception:
            return RecognitionResultOut(
                status="error",
                error_code="UPLOAD_FAILED",
                error_hint="图片上传失败，请重试",
            )

        # 调用识别
        inner = self.recognize(image_data, user_id=user_id, image_key=key)

        candidate_out = None
        if inner.candidate:
            candidate_out = QuestionCandidateOut(
                content=inner.candidate.content,
                correct_answer=inner.candidate.correct_answer,
                wrong_answer=inner.candidate.wrong_answer,
                confidence=inner.candidate.confidence,
                subject=inner.candidate.subject,
                question_type=inner.candidate.question_type,
                image_url=generate_presigned_url(key),  # R23
            )

        return RecognitionResultOut(
            status=cast(Literal["high_confidence", "pending_review", "error"], inner.status),
            candidate=candidate_out,
            error_hint=inner.error_hint,
            error_code="OCR_FAILED" if inner.status == "error" else None,
        )
