from __future__ import annotations
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.s3_client import generate_presigned_url
from backend.repositories.question_repository import QuestionRepository
from backend.schemas.question import (
    QuestionCreate,
    QuestionListOut,
    QuestionOut,
    QuestionUpdate,
)

_repo = QuestionRepository()
_PRESIGN_EXPIRES = 3600  # R23: ≤1h


def _to_out(question) -> QuestionOut:
    image_url = None
    image_url_expires_at = None
    if question.image_key:
        image_url = generate_presigned_url(question.image_key, _PRESIGN_EXPIRES)
        image_url_expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=_PRESIGN_EXPIRES
        )
    return QuestionOut(
        id=question.id,
        user_id=question.user_id,
        content=question.content,
        correct_answer=question.correct_answer,
        wrong_answer=question.wrong_answer,
        subject=question.subject,
        question_type=question.question_type,
        status=question.status,
        confidence=question.confidence,
        note=question.note,
        image_url=image_url,
        image_url_expires_at=image_url_expires_at,
        ease_factor=question.ease_factor,
        interval_days=question.interval_days,
        review_count=question.review_count,
        next_review_at=question.next_review_at,
        created_at=question.created_at,
        updated_at=question.updated_at,
        analysis=question.analysis,
        learning_status=question.learning_status,
        user_error_type=question.user_error_type,
    )


class QuestionService:

    async def get_list(
        self,
        session: AsyncSession,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> QuestionListOut:
        items, total = await _repo.list_by_user(session, user_id, limit, offset)
        return QuestionListOut(
            items=[_to_out(q) for q in items],
            total=total,
            limit=limit,
            offset=offset,
        )

    async def get_one(
        self, session: AsyncSession, question_id: str, user_id: str
    ) -> QuestionOut:
        q = await _repo.get_by_id(session, question_id, user_id)
        if q is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "NOT_FOUND", "message": "题目不存在"},
            )
        return _to_out(q)

    async def create(
        self, session: AsyncSession, user_id: str, data: QuestionCreate
    ) -> QuestionOut:
        # Validate image_key belongs to this user (prevent cross-user S3 path injection)
        if data.image_key and not data.image_key.startswith(f"{user_id}/"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": "INVALID_IMAGE_KEY", "message": "image_key 路径不合法"},
            )
        q = await _repo.create(session, user_id, data)
        await session.commit()
        return _to_out(q)

    async def update(
        self,
        session: AsyncSession,
        question_id: str,
        user_id: str,
        data: QuestionUpdate,
    ) -> QuestionOut:
        q = await _repo.get_by_id(session, question_id, user_id)
        if q is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "NOT_FOUND", "message": "题目不存在"},
            )
        updated = await _repo.update(session, q, data)
        await session.commit()
        return _to_out(updated)

    async def delete(
        self, session: AsyncSession, question_id: str, user_id: str
    ) -> None:
        q = await _repo.get_by_id(session, question_id, user_id)
        if q is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "NOT_FOUND", "message": "题目不存在"},
            )
        await _repo.soft_delete(session, q)
        await session.commit()
