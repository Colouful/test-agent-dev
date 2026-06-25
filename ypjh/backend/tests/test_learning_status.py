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


@pytest.mark.asyncio
async def test_set_learning_status_forward_ok(session: AsyncSession):
    svc = QuestionService()
    out = await svc.create(session, "u1", QuestionCreate(content="题目", correct_answer="答案"))
    # 先推到 待订正
    await svc.set_error_type(session, out.id, "u1", "计算错误")
    # 再推到 待巩固
    updated = await svc.set_learning_status(session, out.id, "u1", "待巩固")
    assert updated.learning_status == "待巩固"


@pytest.mark.asyncio
async def test_set_learning_status_backward_raises(session: AsyncSession):
    from fastapi import HTTPException
    svc = QuestionService()
    out = await svc.create(session, "u1", QuestionCreate(content="题目", correct_answer="答案"))
    await svc.set_error_type(session, out.id, "u1", "计算错误")
    await svc.set_learning_status(session, out.id, "u1", "待巩固")
    with pytest.raises(HTTPException) as exc:
        await svc.set_learning_status(session, out.id, "u1", "待分析")
    assert exc.value.status_code == 400
    assert exc.value.detail["code"] == "INVALID_STATUS_TRANSITION"


@pytest.mark.asyncio
async def test_pending_correction_count_in_stats(session: AsyncSession):
    from backend.services.review_service import ReviewService
    svc = QuestionService()
    rsvc = ReviewService()
    # 创建两道题，一道推进，一道停在待分析
    await svc.create(session, "u1", QuestionCreate(content="题1", correct_answer="答1"))
    out2 = await svc.create(session, "u1", QuestionCreate(content="题2", correct_answer="答2"))
    await svc.set_error_type(session, out2.id, "u1", "计算错误")
    stats = await rsvc.get_stats(session, "u1")
    # 待分析 的题不算待订正，只有 learning_status="待分析" 才需要被标记
    assert hasattr(stats, "pending_correction_count")
    assert stats.pending_correction_count == 1  # 题1 是 待分析，尚未标注错因


@pytest.mark.asyncio
async def test_set_learning_status_cross_user_raises(session: AsyncSession):
    from fastapi import HTTPException
    svc = QuestionService()
    out = await svc.create(session, "u1", QuestionCreate(content="题目", correct_answer="答案"))
    await svc.set_error_type(session, out.id, "u1", "计算错误")
    await svc.set_learning_status(session, out.id, "u1", "待巩固")
    with pytest.raises(HTTPException) as exc:
        await svc.set_learning_status(session, out.id, "u2", "待复习")
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_set_learning_status_same_status_idempotent(session: AsyncSession):
    svc = QuestionService()
    out = await svc.create(session, "u1", QuestionCreate(content="题目", correct_answer="答案"))
    await svc.set_error_type(session, out.id, "u1", "计算错误")
    await svc.set_learning_status(session, out.id, "u1", "待巩固")
    # calling again with same status should not raise
    updated = await svc.set_learning_status(session, out.id, "u1", "待巩固")
    assert updated.learning_status == "待巩固"
