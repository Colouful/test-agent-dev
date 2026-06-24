import pytest
from backend.core.image_utils import fix_exif_orientation, validate_image_bytes

JPEG_MAGIC = b"\xff\xd8\xff\xe0" + b"\x00" * 100
PNG_MAGIC = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
FAKE_SCRIPT = b"#!/bin/bash\necho hello" + b"\x00" * 100


def test_jpeg_magic_bytes_accepted():
    ext = validate_image_bytes(JPEG_MAGIC)
    assert ext == "jpg"


def test_png_magic_bytes_accepted():
    ext = validate_image_bytes(PNG_MAGIC)
    assert ext == "png"


def test_non_image_rejected():
    with pytest.raises(ValueError, match="INVALID_FILE_TYPE"):
        validate_image_bytes(FAKE_SCRIPT)


def test_exif_fix_returns_bytes():
    # 无效图片字节也应返回 bytes（降级不崩）
    result = fix_exif_orientation(JPEG_MAGIC)
    assert isinstance(result, bytes)
