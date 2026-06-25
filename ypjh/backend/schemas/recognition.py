from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class AnalysisOut(BaseModel):
    explanation: str
    knowledge_points: list[str]
    key_examination: str
    error_reason: str


class QuestionCandidateOut(BaseModel):
    content: str
    correct_answer: str
    wrong_answer: str | None = None
    confidence: float
    subject: str | None = None
    question_type: str | None = None
    image_url: str | None = None  # R23: presigned URL, never raw S3 key
    analysis: AnalysisOut | None = None


class RecognitionResultOut(BaseModel):
    status: Literal["high_confidence", "pending_review", "error"]
    candidate: QuestionCandidateOut | None = None
    error_hint: str | None = None
    error_code: str | None = None
