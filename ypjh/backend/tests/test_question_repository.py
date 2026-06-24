import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.repositories.question_repository import QuestionRepository
from backend.schemas.question import QuestionCreate, QuestionUpdate


@pytest.mark.asyncio
async def test_create_question(session: AsyncSession):
    repo = QuestionRepository()
    q = await repo.create(session, "user-1", QuestionCreate(
        content="1+1=?", correct_answer="2"
    ))
    assert q.id is not None
    assert q.user_id == "user-1"
    assert q.deleted_at is None
    assert q.ease_factor == 2.5
    assert q.interval_days == 1


@pytest.mark.asyncio
async def test_get_by_id_user_isolation(session: AsyncSession):
    repo = QuestionRepository()
    q = await repo.create(session, "user-1", QuestionCreate(
        content="题目", correct_answer="答案"
    ))
    # 跨用户查询返回 None（R1）
    result = await repo.get_by_id(session, q.id, "user-2")
    assert result is None
    # 正确用户可以找到
    result = await repo.get_by_id(session, q.id, "user-1")
    assert result is not None


@pytest.mark.asyncio
async def test_list_by_user_excludes_deleted(session: AsyncSession):
    repo = QuestionRepository()
    q1 = await repo.create(session, "user-1", QuestionCreate(
        content="题目1", correct_answer="A"
    ))
    q2 = await repo.create(session, "user-1", QuestionCreate(
        content="题目2", correct_answer="B"
    ))
    await repo.soft_delete(session, q2)

    items, total = await repo.list_by_user(session, "user-1", limit=10, offset=0)
    assert total == 1
    assert items[0].id == q1.id


@pytest.mark.asyncio
async def test_soft_delete_sets_deleted_at(session: AsyncSession):
    repo = QuestionRepository()
    q = await repo.create(session, "user-1", QuestionCreate(
        content="题目", correct_answer="答案"
    ))
    await repo.soft_delete(session, q)
    assert q.deleted_at is not None


@pytest.mark.asyncio
async def test_update_question(session: AsyncSession):
    repo = QuestionRepository()
    q = await repo.create(session, "user-1", QuestionCreate(
        content="原内容", correct_answer="答案"
    ))
    updated = await repo.update(session, q, QuestionUpdate(content="新内容"))
    assert updated.content == "新内容"
