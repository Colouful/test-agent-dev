import os
import pytest

os.environ["MOCK_BEDROCK"] = "true"

from sqlalchemy.ext.asyncio import AsyncSession
from backend.services.question_service import QuestionService
from backend.schemas.question import QuestionCreate


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
