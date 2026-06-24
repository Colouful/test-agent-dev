from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, Field


class ReviewQueueItemOut(BaseModel):
    id: str
    content: str
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
    score: int = Field(..., ge=1, le=5)


class ScoreOut(BaseModel):
    question_id: str
    score: int
    new_ease_factor: float
    new_interval_days: int
    new_review_count: int
    next_review_at: datetime


class ReviewStatsOut(BaseModel):
    due_count: int
    reviewed_today: int
