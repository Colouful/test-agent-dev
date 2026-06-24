from datetime import datetime

from sqlalchemy import ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base


class ReviewLog(Base):
    __tablename__ = "review_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"))
    user_id: Mapped[str] = mapped_column(index=True)
    score: Mapped[int]
    ease_factor_before: Mapped[float]
    ease_factor_after: Mapped[float]
    interval_before: Mapped[int]
    interval_after: Mapped[int]
    reviewed_at: Mapped[datetime] = mapped_column(server_default=func.now())
