from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field


class PrintRequest(BaseModel):
    question_ids: list[str] = Field(..., min_length=1, max_length=50)
    show_answer: bool = True
    show_image: bool = True
    layout: Literal["single", "double"] = "single"
