import os
import pytest

os.environ["MOCK_BEDROCK"] = "true"

from sqlalchemy.ext.asyncio import AsyncSession
from backend.services.question_service import QuestionService
from backend.schemas.question import QuestionCreate
from httpx import AsyncClient
from backend.core.security import get_current_user
from backend.models.user import User
from unittest.mock import AsyncMock


@pytest.mark.asyncio
async def test_new_question_has_learning_status_待分析(session: AsyncSession):
    svc = QuestionService()
    out = await svc.create(session, "u1", QuestionCreate(content="题目", correct_answer="答案"))
    assert out.learning_status == "待分析"
    assert out.user_error_type is None


@pytest.mark.asyncio
async def test_learning_status_returned_in_list(session: AsyncSession):
    svc = QuestionService()
    await svc.create(session, "u1", QuestionCreate(content="题目", correct_answer="答案"))
    result = await svc.get_list(session, "u1")
    assert result.items[0].learning_status == "待分析"


def _mock_user(uid: str):
    user = User()
    user.id = uid
    user.email = f"{uid}@test.com"
    return user


@pytest.mark.asyncio
async def test_set_error_type_transitions_to_待订正(session: AsyncSession):
    svc = QuestionService()
    out = await svc.create(session, "u1", QuestionCreate(content="题目", correct_answer="答案"))
    updated = await svc.set_error_type(session, out.id, "u1", "计算错误")
    assert updated.user_error_type == "计算错误"
    assert updated.learning_status == "待订正"


@pytest.mark.asyncio
async def test_set_error_type_invalid_value_raises(session: AsyncSession):
    from fastapi import HTTPException
    svc = QuestionService()
    out = await svc.create(session, "u1", QuestionCreate(content="题目", correct_answer="答案"))
    with pytest.raises(HTTPException) as exc:
        await svc.set_error_type(session, out.id, "u1", "无效错因")
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_set_error_type_cross_user_raises(session: AsyncSession):
    from fastapi import HTTPException
    svc = QuestionService()
    out = await svc.create(session, "u1", QuestionCreate(content="题目", correct_answer="答案"))
    with pytest.raises(HTTPException) as exc:
        await svc.set_error_type(session, out.id, "u2", "计算错误")
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_set_error_type_already_待订正_only_updates_type(session: AsyncSession):
    svc = QuestionService()
    out = await svc.create(session, "u1", QuestionCreate(content="题目", correct_answer="答案"))
    await svc.set_error_type(session, out.id, "u1", "计算错误")
    updated = await svc.set_error_type(session, out.id, "u1", "概念混淆")
    assert updated.user_error_type == "概念混淆"
    assert updated.learning_status == "待订正"  # 不倒退
