from __future__ import annotations
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.question import Question
from backend.models.review_log import ReviewLog


class ReviewRepository:

    async def get_due_questions(
        self, session: AsyncSession, user_id: str, limit: int = 20
    ) -> list[Question]:
        now = datetime.now(timezone.utc)
        stmt = (
            select(Question)
            .where(
                Question.user_id == user_id,         # R1
                Question.deleted_at.is_(None),        # R21
                Question.next_review_at <= now,
            )
            .order_by(Question.next_review_at.asc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def create_log(
        self,
        session: AsyncSession,
        user_id: str,
        question_id: str,
        score: int,
        prev_ease_factor: float,
        new_ease_factor: float,
        prev_interval: int,
        new_interval: int,
    ) -> ReviewLog:
        log = ReviewLog(
            id=str(uuid.uuid4()),
            user_id=user_id,
            question_id=question_id,
            score=score,
            prev_ease_factor=prev_ease_factor,
            new_ease_factor=new_ease_factor,
            prev_interval=prev_interval,
            new_interval=new_interval,
            reviewed_at=datetime.now(timezone.utc),
        )
        session.add(log)
        await session.flush()
        return log

    async def get_due_count(
        self, session: AsyncSession, user_id: str
    ) -> int:
        now = datetime.now(timezone.utc)
        stmt = select(func.count()).select_from(Question).where(
            Question.user_id == user_id,
            Question.deleted_at.is_(None),
            Question.next_review_at <= now,
        )
        return (await session.execute(stmt)).scalar_one()

    async def get_stats(
        self, session: AsyncSession, user_id: str
    ) -> dict[str, int]:
        due_count = await self.get_due_count(session, user_id)

        now = datetime.now(timezone.utc)
        # 今日已复习
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        reviewed_stmt = select(func.count()).select_from(ReviewLog).where(
            ReviewLog.user_id == user_id,
            ReviewLog.reviewed_at >= today_start,
        )
        reviewed_today: int = (await session.execute(reviewed_stmt)).scalar_one()

        return {"due_count": due_count, "reviewed_today": reviewed_today}
