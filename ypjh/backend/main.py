from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from backend.api.v1.router import v1_router
from backend.core.database import create_tables


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Import all models to ensure Base.metadata is populated
    import backend.models  # noqa: F401

    await create_tables()
    yield


app = FastAPI(title="错题本 API", version="0.1.0", lifespan=lifespan)
app.include_router(v1_router)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, dict) and "code" in detail:
        error = detail
    else:
        error = {"code": "HTTP_ERROR", "message": str(detail)}
    return JSONResponse(
        status_code=exc.status_code,
        content={"data": None, "error": error},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "data": None,
            "error": {"code": "VALIDATION_ERROR", "message": str(exc.errors())},
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # 生产环境不暴露 stack trace
    return JSONResponse(
        status_code=500,
        content={
            "data": None,
            "error": {"code": "INTERNAL_ERROR", "message": "服务器内部错误"},
        },
    )
