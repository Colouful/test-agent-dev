from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_session
from backend.core.s3_client import generate_presigned_url
from backend.core.security import get_current_user
from backend.models.user import User
from backend.repositories.question_repository import QuestionRepository
from backend.schemas.print_schema import PrintRequest

router = APIRouter(prefix="/print", tags=["print"])
_repo = QuestionRepository()
_TEMPLATES_DIR = Path(__file__).parent.parent.parent.parent / "templates"
_jinja_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=select_autoescape(["html"]),
)


@router.post("/preview", response_class=HTMLResponse)
async def print_preview(
    body: PrintRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> HTMLResponse:
    questions = []
    for qid in body.question_ids:
        q = await _repo.get_by_id(session, qid, current_user.id)
        if q is None:
            continue  # R1: 跨用户题目静默跳过
        image_url = None
        if q.image_key and body.show_image:
            image_url = generate_presigned_url(q.image_key, 3600)  # R23
        questions.append({
            "content": q.content,
            "correct_answer": q.correct_answer,
            "wrong_answer": q.wrong_answer,
            "subject": q.subject,
            "note": q.note,
            "image_url": image_url,
        })

    template = _jinja_env.get_template("print_preview.html")
    html = template.render(
        questions=questions,
        show_answer=body.show_answer,
        show_image=body.show_image,
        layout=body.layout,
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
    )
    return HTMLResponse(content=html)
