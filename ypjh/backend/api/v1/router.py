from fastapi import APIRouter

from backend.api.v1.endpoints.auth import router as auth_router
from backend.api.v1.endpoints.questions import router as questions_router
from backend.api.v1.endpoints.questions_recognize import router as recognize_router

v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(auth_router)
v1_router.include_router(recognize_router)
v1_router.include_router(questions_router)
