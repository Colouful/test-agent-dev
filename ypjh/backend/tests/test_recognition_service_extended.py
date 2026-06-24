import os
import pytest

os.environ["MOCK_BEDROCK"] = "true"

from backend.schemas.recognition import RecognitionResultOut
from backend.services.recognition_service import RecognitionService


def test_recognize_upload_returns_schema():
    svc = RecognitionService(mock_scenario="clear")
    result = svc.recognize_upload(b"\xff\xd8\xff" + b"\x00" * 100, "u1", "test.jpg")
    assert isinstance(result, RecognitionResultOut)
    assert result.status in ("high_confidence", "pending_review", "error")
    if result.candidate:
        assert result.candidate.image_key is not None
        assert result.candidate.image_key.startswith("u1/original/")


def test_invalid_file_type_returns_error():
    svc = RecognitionService()
    result = svc.recognize_upload(b"not-an-image", "u1", "bad.txt")
    assert result.status == "error"
    assert result.error_code == "INVALID_FILE_TYPE"


def test_non_question_image_returns_error():
    svc = RecognitionService(mock_scenario="non_question")
    result = svc.recognize_upload(b"\xff\xd8\xff" + b"\x00" * 100, "u1", "photo.jpg")
    assert result.status == "error"
    assert result.error_code == "OCR_FAILED"


def test_pending_review_has_error_hint():
    svc = RecognitionService(mock_scenario="blurry")
    result = svc.recognize_upload(b"\xff\xd8\xff" + b"\x00" * 100, "u1", "blurry.jpg")
    assert result.status == "pending_review"
    assert result.error_hint is not None
