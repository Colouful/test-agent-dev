"""
领域工具：校验 Bedrock 识别结果是否符合错题本 Schema。

用途：
- 在识别结果入库前调用
- confidence 缺失时报错（不得默认 1.0）
- 返回标准化的 QuestionCandidate 或抛出 ValidationError
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field, ValidationError, field_validator


CONFIDENCE_THRESHOLD = 0.7


class QuestionCandidate(BaseModel):
    """Bedrock 识别结果的标准 Schema。"""

    content: str = Field(..., min_length=1, description="题目正文")
    correct_answer: str = Field(..., min_length=1, description="正确答案")
    confidence: float = Field(..., ge=0.0, le=1.0, description="识别置信度，缺失时必须显式传 0.0")
    subject: str | None = Field(None, description="学科（可选，识别不出时为 None）")
    question_type: str | None = Field(None, description="题型：single/multiple/fill/essay")
    wrong_answer: str | None = Field(None, description="用户的错误答案（图片中识别到时填入）")
    analysis: str | None = Field(None, description="解析（可选）")

    @field_validator("confidence", mode="before")
    @classmethod
    def confidence_must_be_explicit(cls, v: Any) -> float:
        # confidence 字段必须显式传入，不允许隐式缺失
        if v is None:
            raise ValueError(
                "confidence 字段缺失。按 R2 规则，必须显式传入 0.0，不得隐式省略。"
            )
        return float(v)


def check_question_schema(raw: dict[str, Any]) -> QuestionCandidate:
    """
    校验 Bedrock 识别结果。

    调用方必须在调用 Bedrock 后立即调用此函数，传入原始 JSON dict。
    confidence 缺失时调用方必须传入 raw["confidence"] = 0.0，不得省略。

    返回：QuestionCandidate（通过校验）
    抛出：ValueError / ValidationError（校验失败，不得入库）
    """
    if not isinstance(raw, dict):
        raise ValueError(f"识别结果必须是 dict，实际收到 {type(raw).__name__}")

    # R2：confidence 缺失按 0 处理（调用方职责：在传入前补充此字段）
    if "confidence" not in raw:
        raise ValueError(
            "R2 违规：Bedrock 返回中 confidence 字段缺失。"
            "调用方必须在传入前显式设置 raw['confidence'] = 0.0，不得跳过。"
        )

    try:
        candidate = QuestionCandidate(**raw)
    except ValidationError as e:
        raise ValueError(f"识别结果 Schema 校验失败：{e}") from e

    return candidate


def is_high_confidence(candidate: QuestionCandidate) -> bool:
    """判断识别结果是否达到直接入库的置信度阈值。"""
    return candidate.confidence >= CONFIDENCE_THRESHOLD


# ── CLI 调用（用于 MCP 工具集成和手动测试）──────────────────────────

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法: python check_question_schema.py '<json_string>'")
        sys.exit(1)

    raw_input = json.loads(sys.argv[1])
    try:
        result = check_question_schema(raw_input)
        status = "HIGH_CONFIDENCE" if is_high_confidence(result) else "LOW_CONFIDENCE_PENDING"
        print(json.dumps({
            "status": status,
            "confidence": result.confidence,
            "content_length": len(result.content),
            "has_answer": bool(result.correct_answer),
        }, ensure_ascii=False, indent=2))
    except ValueError as err:
        print(json.dumps({"status": "SCHEMA_ERROR", "error": str(err)}, ensure_ascii=False, indent=2))
        sys.exit(1)
