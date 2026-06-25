from __future__ import annotations
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.s3_client import generate_presigned_url
from backend.core.sm2 import calculate_next_review
from backend.repositories.question_repository import QuestionRepository
from backend.repositories.review_repository import ReviewRepository
from backend.schemas.review import (
    ReviewQueueItemOut,
    ReviewQueueOut,
    ReviewStatsOut,
    ScoreOut,
)

_qrepo = QuestionRepository()
_rrepo = ReviewRepository()
_PRESIGN_EXPIRES = 3600


class ReviewService:

    async def get_queue(
        self, session: AsyncSession, user_id: str, limit: int = 20
    ) -> ReviewQueueOut:
        questions = await _rrepo.get_due_questions(session, user_id, limit)
        true_total = await _rrepo.get_due_count(session, user_id)
        items = []
        for q in questions:
            image_url = None
            expires_at = None
            if q.image_key:
                image_url = generate_presigned_url(q.image_key, _PRESIGN_EXPIRES)
                expires_at = datetime.now(timezone.utc) + timedelta(seconds=_PRESIGN_EXPIRES)
            items.append(ReviewQueueItemOut(
                id=q.id,
                content=q.content,
                correct_answer=q.correct_answer,
                subject=q.subject,
                question_type=q.question_type,
                image_url=image_url,
                image_url_expires_at=expires_at,
                ease_factor=q.ease_factor,
                interval_days=q.interval_days,
                review_count=q.review_count,
            ))
        return ReviewQueueOut(items=items, total=true_total)

    async def submit_score(
        self,
        session: AsyncSession,
        question_id: str,
        user_id: str,
        score: int,
    ) -> ScoreOut:
        q = await _qrepo.get_by_id(session, question_id, user_id)
        if q is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail={"code": "NOT_FOUND", "message": "题目不存在"})

        prev_ef = q.ease_factor
        prev_interval = q.interval_days
        new_ef, new_interval, new_count = calculate_next_review(
            score, prev_ef, prev_interval, q.review_count
        )
        next_review_at = datetime.now(timezone.utc) + timedelta(days=new_interval)

        # 更新题目 SM-2 字段
        q.ease_factor = new_ef
        q.interval_days = new_interval
        q.review_count = new_count
        q.next_review_at = next_review_at
        q.last_reviewed_at = datetime.now(timezone.utc)

        # 记录复习日志
        await _rrepo.create_log(
            session,
            user_id=user_id,
            question_id=question_id,
            score=score,
            prev_ease_factor=prev_ef,
            new_ease_factor=new_ef,
            prev_interval=prev_interval,
            new_interval=new_interval,
        )

        await session.commit()

        return ScoreOut(
            question_id=question_id,
            score=score,
            new_ease_factor=new_ef,
            new_interval_days=new_interval,
            new_review_count=new_count,
            next_review_at=next_review_at,
        )

    async def get_stats(
        self, session: AsyncSession, user_id: str
    ) -> ReviewStatsOut:
        stats = await _rrepo.get_stats(session, user_id)
        return ReviewStatsOut(**stats)
