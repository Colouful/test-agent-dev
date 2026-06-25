from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_session
from backend.core.security import get_current_user
from backend.models.user import User
from backend.schemas.common import ApiResponse
from backend.schemas.question import (
    ErrorTypeUpdate,
    LearningStatusUpdate,
    QuestionCreate,
    QuestionListOut,
    QuestionOut,
    QuestionUpdate,
)
from backend.services.question_service import QuestionService

router = APIRouter(prefix="/questions", tags=["questions"])
_svc = QuestionService()


@router.get("", response_model=ApiResponse[QuestionListOut])
async def list_questions(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[QuestionListOut]:
    result = await _svc.get_list(session, current_user.id, limit, offset)
    return ApiResponse(data=result)


@router.post("", response_model=ApiResponse[QuestionOut], status_code=201)
async def create_question(
    body: QuestionCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[QuestionOut]:
    result = await _svc.create(session, current_user.id, body)
    return ApiResponse(data=result)


@router.get("/{question_id}", response_model=ApiResponse[QuestionOut])
async def get_question(
    question_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[QuestionOut]:
    result = await _svc.get_one(session, question_id, current_user.id)
    return ApiResponse(data=result)


@router.patch("/{question_id}", response_model=ApiResponse[QuestionOut])
async def update_question(
    question_id: str,
    body: QuestionUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[QuestionOut]:
    result = await _svc.update(session, question_id, current_user.id, body)
    return ApiResponse(data=result)


@router.delete("/{question_id}", status_code=204)
async def delete_question(
    question_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    await _svc.delete(session, question_id, current_user.id)


@router.patch("/{question_id}/error-type", response_model=ApiResponse[QuestionOut])
async def set_error_type(
    question_id: str,
    body: ErrorTypeUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[QuestionOut]:
    result = await _svc.set_error_type(session, question_id, current_user.id, body.user_error_type)
    return ApiResponse(data=result)


@router.patch("/{question_id}/learning-status", response_model=ApiResponse[QuestionOut])
async def set_learning_status(
    question_id: str,
    body: LearningStatusUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[QuestionOut]:
    result = await _svc.set_learning_status(session, question_id, current_user.id, body.learning_status)
    return ApiResponse(data=result)
