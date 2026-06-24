from __future__ import annotations

import io
from pathlib import Path

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "recognize_question.txt"

# Magic Bytes 特征
_JPEG_MAGIC = b"\xff\xd8\xff"
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"

# HEIC brand identifiers (avoids matching MP4/MOV which also use ISOBMFF/ftyp)
_HEIC_BRANDS = frozenset({b"heic", b"heix", b"mif1", b"msf1", b"MiHE", b"MiHB"})


def validate_image_bytes(data: bytes) -> str:
    """校验 Magic Bytes，返回扩展名。失败抛 ValueError(INVALID_FILE_TYPE)。"""
    if data[:3] == _JPEG_MAGIC:
        return "jpg"
    if data[:8] == _PNG_MAGIC:
        return "png"
    # HEIC: ftyp box + known HEIC brand identifier (avoids matching MP4/MOV)
    if len(data) >= 12 and data[4:8] == b"ftyp" and data[8:12] in _HEIC_BRANDS:
        return "heic"
    raise ValueError("INVALID_FILE_TYPE")


def fix_exif_orientation(data: bytes) -> bytes:
    """按 EXIF Orientation 物理旋转图片（REQ-27）。失败降级返回原字节。"""
    try:
        from PIL import Image, ImageOps

        img = Image.open(io.BytesIO(data))
        original_format = img.format  # capture before exif_transpose clears it
        img = ImageOps.exif_transpose(img)  # type: ignore[assignment]
        buf = io.BytesIO()
        img.save(buf, format=original_format or "JPEG")
        return buf.getvalue()
    except Exception:
        return data  # 降级：无法处理时返回原始字节
