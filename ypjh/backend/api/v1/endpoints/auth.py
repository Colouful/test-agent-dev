from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_session
from backend.core.security import get_current_user
from backend.models.user import User
from backend.schemas.auth import AuthResponse, LoginRequest, RegisterRequest, UserResponse
from backend.schemas.common import ApiResponse
from backend.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])
_svc = AuthService()


@router.post("/register", response_model=ApiResponse[AuthResponse], status_code=201)
async def register(
    body: RegisterRequest,
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[AuthResponse]:
    result = await _svc.register(session, body.email, body.password)
    return ApiResponse(data=result)


@router.post("/login", response_model=ApiResponse[AuthResponse])
async def login(
    body: LoginRequest,
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[AuthResponse]:
    result = await _svc.login(session, body.email, body.password)
    return ApiResponse(data=result)


@router.get("/me", response_model=ApiResponse[UserResponse])
async def me(
    current_user: User = Depends(get_current_user),
) -> ApiResponse[UserResponse]:
    return ApiResponse(
        data=UserResponse(id=current_user.id, email=current_user.email)
    )
