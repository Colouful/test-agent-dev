from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_session
from backend.core.security import get_current_user
from backend.models.user import User
from backend.schemas.common import ApiResponse
from backend.schemas.recognition import RecognitionResultOut
from backend.services.recognition_service import RecognitionService

router = APIRouter(tags=["recognition"])
MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20MB (R17)


@router.post(
    "/questions/recognize",
    response_model=ApiResponse[RecognitionResultOut],
)
async def recognize_question(
    request: Request,
    image: UploadFile,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[RecognitionResultOut]:
    # R17: 20MB 上限，在读取内容前检查 Content-Length
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={"code": "FILE_TOO_LARGE", "message": "文件大小不能超过 20MB"},
        )

    data = await image.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={"code": "FILE_TOO_LARGE", "message": "文件大小不能超过 20MB"},
        )

    svc = RecognitionService()
    result = svc.recognize_upload(
        image_data=data,
        user_id=current_user.id,
        original_filename=image.filename or "unknown",
    )
    return ApiResponse(data=result)
