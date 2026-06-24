import os
import pytest

os.environ["MOCK_BEDROCK"] = "true"

from backend.core.s3_client import generate_presigned_url, upload_image


def test_mock_upload_returns_valid_key():
    key = upload_image(b"fake-image-data", "user-123", "jpg")
    assert key.startswith("user-123/original/")
    assert key.endswith(".jpg")
    # UUID 格式校验
    import re
    uuid_part = key.split("/")[2].replace(".jpg", "")
    assert re.match(r"[0-9a-f-]{36}", uuid_part)


def test_mock_presigned_url_format():
    url = generate_presigned_url("user-123/original/abc.jpg")
    assert url.startswith("https://")


def test_upload_respects_r20_path_format():
    key = upload_image(b"data", "alice", "png")
    parts = key.split("/")
    assert parts[0] == "alice"       # user_id 前缀
    assert parts[1] == "original"    # original/ 层级
    assert parts[2].endswith(".png") # UUID.ext
