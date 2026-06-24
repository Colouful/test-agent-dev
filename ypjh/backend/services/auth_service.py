from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.security import create_access_token, hash_password, verify_password
from backend.repositories.user_repository import UserRepository
from backend.schemas.auth import AuthResponse


class AuthService:
    def __init__(self) -> None:
        self.repo = UserRepository()

    async def register(
        self, session: AsyncSession, email: str, password: str
    ) -> AuthResponse:
        existing = await self.repo.get_by_email(session, email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "DUPLICATE_EMAIL", "message": "该邮箱已注册"},
            )
        user = await self.repo.create(session, email, hash_password(password))
        return AuthResponse(access_token=create_access_token(str(user.id)))

    async def login(
        self, session: AsyncSession, email: str, password: str
    ) -> AuthResponse:
        user = await self.repo.get_by_email(session, email)
        if user is None or not verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "INVALID_CREDENTIALS", "message": "邮箱或密码错误"},
            )
        return AuthResponse(access_token=create_access_token(str(user.id)))
