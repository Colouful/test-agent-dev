from __future__ import annotations

import io
from pathlib import Path

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "recognize_question.txt"

# Magic Bytes 特征
_JPEG_MAGIC = b"\xff\xd8\xff"
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def validate_image_bytes(data: bytes) -> str:
    """校验 Magic Bytes，返回扩展名。失败抛 ValueError(INVALID_FILE_TYPE)。"""
    if data[:3] == _JPEG_MAGIC:
        return "jpg"
    if data[:8] == _PNG_MAGIC:
        return "png"
    # HEIC: 字节偏移 4-7 含 ASCII 'ftyp'
    if len(data) >= 8 and data[4:8] == b"ftyp":
        return "heic"
    raise ValueError("INVALID_FILE_TYPE")


def fix_exif_orientation(data: bytes) -> bytes:
    """按 EXIF Orientation 物理旋转图片（REQ-27）。失败降级返回原字节。"""
    try:
        from PIL import Image, ImageOps  # type: ignore[import-untyped]

        img = Image.open(io.BytesIO(data))
        img = ImageOps.exif_transpose(img)
        buf = io.BytesIO()
        fmt = img.format or "JPEG"
        img.save(buf, format=fmt)
        return buf.getvalue()
    except Exception:
        return data  # 降级：无法处理时返回原始字节
