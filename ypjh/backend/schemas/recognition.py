from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class SolutionStep(BaseModel):
    step: int
    title: str
    content: str


class KnowledgePoints(BaseModel):
    core: list[str] = []
    prerequisite: list[str] = []
    related: list[str] = []


class ErrorAnalysis(BaseModel):
    type: str
    reason: str
    improvement: list[str] = []


class PracticeQuestion(BaseModel):
    content: str
    answer: str
    explanation: str


class AnalysisOut(BaseModel):
    solution_summary: str
    solution_steps: list[SolutionStep]
    knowledge_points: KnowledgePoints
    key_examination: str
    error_analysis: ErrorAnalysis
    common_mistakes: list[str] = []
    practice_questions: list[PracticeQuestion] = []


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
