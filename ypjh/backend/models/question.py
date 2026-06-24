from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[str] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(index=True)
    subject: Mapped[str | None] = mapped_column(default=None)
    question_type: Mapped[str | None] = mapped_column(default=None)
    content: Mapped[str]
    correct_answer: Mapped[str]
    wrong_answer: Mapped[str | None] = mapped_column(default=None)
    note: Mapped[str | None] = mapped_column(default=None)
    confidence: Mapped[float] = mapped_column(default=0.0)
    image_key: Mapped[str | None] = mapped_column(default=None)
    original_filename: Mapped[str | None] = mapped_column(default=None)
    status: Mapped[str] = mapped_column(default="pending_review")
    ease_factor: Mapped[float] = mapped_column(default=2.5)
    review_count: Mapped[int] = mapped_column(default=0)
    interval_days: Mapped[int] = mapped_column(default=1)
    next_review_at: Mapped[datetime | None] = mapped_column(default=None)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(default=None)
