from __future__ import annotations
from datetime import datetime
from typing import Literal
from pydantic import BaseModel


class QuestionCreate(BaseModel):
    content: str
    correct_answer: str
    wrong_answer: str | None = None
    subject: str | None = None
    question_type: str | None = None
    image_key: str | None = None
    confidence: float | None = None
    original_filename: str | None = None
    analysis: dict | None = None


class QuestionUpdate(BaseModel):
    content: str | None = None
    correct_answer: str | None = None
    wrong_answer: str | None = None
    subject: str | None = None
    question_type: str | None = None
    status: Literal["pending_review", "confirmed"] | None = None
    note: str | None = None


class QuestionOut(BaseModel):
    id: str
    user_id: str
    content: str
    correct_answer: str
    wrong_answer: str | None
    subject: str | None
    question_type: str | None
    status: str
    confidence: float | None
    note: str | None
    image_url: str | None
    image_url_expires_at: datetime | None
    ease_factor: float
    interval_days: int
    review_count: int
    next_review_at: datetime | None
    created_at: datetime
    updated_at: datetime
    analysis: dict | None = None

    model_config = {"from_attributes": True}


class QuestionListOut(BaseModel):
    items: list[QuestionOut]
    total: int
    limit: int
    offset: int
