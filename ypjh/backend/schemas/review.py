from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class ReviewQueueItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    content: str
    correct_answer: str
    subject: str | None
    question_type: str | None
    image_url: str | None
    image_url_expires_at: datetime | None
    ease_factor: float
    interval_days: int
    review_count: int


class ReviewQueueOut(BaseModel):
    items: list[ReviewQueueItemOut]
    total: int


class ScoreRequest(BaseModel):
    score: int = Field(..., ge=0, le=5)


class ScoreOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    question_id: str
    score: int
    new_ease_factor: float
    new_interval_days: int
    new_review_count: int
    next_review_at: datetime


class ReviewStatsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    due_count: int
    reviewed_today: int
