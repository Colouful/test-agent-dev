from __future__ import annotations
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.question import Question
from backend.schemas.question import QuestionCreate, QuestionUpdate


class QuestionRepository:

    async def create(
        self, session: AsyncSession, user_id: str, data: QuestionCreate
    ) -> Question:
        q = Question(
            id=str(uuid.uuid4()),
            user_id=user_id,
            content=data.content,
            correct_answer=data.correct_answer,
            wrong_answer=data.wrong_answer,
            subject=data.subject,
            question_type=data.question_type,
            image_key=data.image_key,
            confidence=data.confidence,
            original_filename=data.original_filename,
            status="confirmed",
            ease_factor=2.5,
            interval_days=1,
            review_count=0,
        )
        session.add(q)
        await session.flush()
        return q

    async def get_by_id(
        self, session: AsyncSession, question_id: str, user_id: str
    ) -> Question | None:
        stmt = (
            select(Question)
            .where(
                Question.id == question_id,
                Question.user_id == user_id,  # R1: 用户隔离
                Question.deleted_at.is_(None),  # R21: 软删除过滤
            )
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_user(
        self,
        session: AsyncSession,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Question], int]:
        base = select(Question).where(
            Question.user_id == user_id,  # R1
            Question.deleted_at.is_(None),  # R21
        )
        count_stmt = select(func.count()).select_from(base.subquery())
        total: int = (await session.execute(count_stmt)).scalar_one()
        items_stmt = base.order_by(Question.created_at.desc()).limit(limit).offset(offset)
        items = list((await session.execute(items_stmt)).scalars().all())
        return items, total

    async def update(
        self, session: AsyncSession, question: Question, data: QuestionUpdate
    ) -> Question:
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(question, field, value)
        question.updated_at = datetime.now(timezone.utc)
        await session.flush()
        return question

    async def soft_delete(
        self, session: AsyncSession, question: Question
    ) -> None:
        question.deleted_at = datetime.now(timezone.utc)
        await session.flush()
