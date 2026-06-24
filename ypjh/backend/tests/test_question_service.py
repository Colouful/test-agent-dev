import os, pytest
os.environ["MOCK_BEDROCK"] = "true"

from sqlalchemy.ext.asyncio import AsyncSession
from backend.services.question_service import QuestionService
from backend.schemas.question import QuestionCreate, QuestionUpdate


@pytest.mark.asyncio
async def test_create_returns_out_schema(session: AsyncSession):
    svc = QuestionService()
    out = await svc.create(session, "user-1", QuestionCreate(
        content="题目", correct_answer="答案"
    ))
    assert out.id is not None
    assert out.image_url is None      # 无图片时为 None


@pytest.mark.asyncio
async def test_create_with_image_returns_presigned_url(session: AsyncSession):
    svc = QuestionService()
    out = await svc.create(session, "user-1", QuestionCreate(
        content="题目", correct_answer="答案",
        image_key="user-1/original/abc.jpg",
    ))
    # R23: 响应包含 presigned URL
    assert out.image_url is not None
    assert out.image_url.startswith("https://")
    assert out.image_url_expires_at is not None


@pytest.mark.asyncio
async def test_get_one_not_found_raises(session: AsyncSession):
    from fastapi import HTTPException
    svc = QuestionService()
    with pytest.raises(HTTPException) as exc_info:
        await svc.get_one(session, "nonexistent-id", "user-1")
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_then_not_found(session: AsyncSession):
    from fastapi import HTTPException
    svc = QuestionService()
    out = await svc.create(session, "user-1", QuestionCreate(
        content="题目", correct_answer="答案"
    ))
    await svc.delete(session, out.id, "user-1")
    with pytest.raises(HTTPException):
        await svc.get_one(session, out.id, "user-1")
