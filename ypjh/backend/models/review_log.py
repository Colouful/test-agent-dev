from datetime import datetime

from sqlalchemy import ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base


class ReviewLog(Base):
    __tablename__ = "review_logs"

    id: Mapped[str] = mapped_column(primary_key=True)
    question_id: Mapped[str] = mapped_column(ForeignKey("questions.id"))
    user_id: Mapped[str] = mapped_column(index=True)
    score: Mapped[int]
    prev_ease_factor: Mapped[float]
    new_ease_factor: Mapped[float]
    prev_interval: Mapped[int]
    new_interval: Mapped[int]
    reviewed_at: Mapped[datetime] = mapped_column(server_default=func.now())
