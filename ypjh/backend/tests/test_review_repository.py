import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from backend.repositories.review_repository import ReviewRepository
from backend.repositories.question_repository import QuestionRepository
from backend.schemas.question import QuestionCreate


@pytest.mark.asyncio
async def test_get_due_questions_returns_overdue(session: AsyncSession):
    qrepo = QuestionRepository()
    rrepo = ReviewRepository()

    # 创建一道已到期题目（next_review_at = 昨天）
    q = await qrepo.create(session, "user-1", QuestionCreate(
        content="题目", correct_answer="答案"
    ))
    q.next_review_at = datetime.now(timezone.utc) - timedelta(days=1)
    await session.flush()

    due = await rrepo.get_due_questions(session, "user-1", limit=10)
    assert len(due) == 1
    assert due[0].id == q.id


@pytest.mark.asyncio
async def test_get_due_questions_user_isolation(session: AsyncSession):
    qrepo = QuestionRepository()
    rrepo = ReviewRepository()
    q = await qrepo.create(session, "user-1", QuestionCreate(
        content="题目", correct_answer="答案"
    ))
    q.next_review_at = datetime.now(timezone.utc) - timedelta(hours=1)
    await session.flush()

    # user-2 不应看到 user-1 的题目（R1）
    due = await rrepo.get_due_questions(session, "user-2", limit=10)
    assert len(due) == 0


@pytest.mark.asyncio
async def test_create_log_records_review(session: AsyncSession):
    qrepo = QuestionRepository()
    rrepo = ReviewRepository()
    q = await qrepo.create(session, "user-1", QuestionCreate(
        content="题目", correct_answer="答案"
    ))
    log = await rrepo.create_log(
        session,
        user_id="user-1",
        question_id=q.id,
        score=4,
        prev_ease_factor=2.5,
        new_ease_factor=2.6,
        prev_interval=1,
        new_interval=6,
    )
    assert log.score == 4
    assert log.user_id == "user-1"
