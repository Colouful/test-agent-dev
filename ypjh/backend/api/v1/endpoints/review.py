from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_session
from backend.core.security import get_current_user
from backend.models.user import User
from backend.schemas.common import ApiResponse
from backend.schemas.review import ReviewQueueOut, ReviewStatsOut, ScoreOut, ScoreRequest
from backend.services.review_service import ReviewService

router = APIRouter(prefix="/review", tags=["review"])
_svc = ReviewService()


@router.get("/queue", response_model=ApiResponse[ReviewQueueOut])
async def get_review_queue(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[ReviewQueueOut]:
    result = await _svc.get_queue(session, current_user.id)
    return ApiResponse(data=result)


@router.post("/{question_id}/score", response_model=ApiResponse[ScoreOut])
async def submit_score(
    question_id: str,
    body: ScoreRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[ScoreOut]:
    result = await _svc.submit_score(session, question_id, current_user.id, body.score)
    return ApiResponse(data=result)


@router.get("/stats", response_model=ApiResponse[ReviewStatsOut])
async def get_review_stats(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[ReviewStatsOut]:
    result = await _svc.get_stats(session, current_user.id)
    return ApiResponse(data=result)
