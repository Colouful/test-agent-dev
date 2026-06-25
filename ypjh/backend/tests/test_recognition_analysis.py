import pytest
from backend.services.recognition_service import RecognitionService


def test_mock_clear_has_analysis():
    svc = RecognitionService(mock_scenario="clear")
    result = svc.recognize(b"fake", user_id="u1", image_key="test.jpg")
    assert result.status in ("high_confidence", "pending_review")
    assert result.analysis is not None
    assert "explanation" in result.analysis
    assert "knowledge_points" in result.analysis
    assert isinstance(result.analysis["knowledge_points"], list)
    assert "key_examination" in result.analysis
    assert "error_reason" in result.analysis


def test_mock_non_question_no_analysis():
    svc = RecognitionService(mock_scenario="non_question")
    result = svc.recognize(b"fake", user_id="u1", image_key="test.jpg")
    assert result.status == "error"
    assert result.analysis is None


def test_mock_blurry_no_analysis():
    svc = RecognitionService(mock_scenario="blurry")
    result = svc.recognize(b"fake", user_id="u1", image_key="test.jpg")
    # blurry scenario has no analysis key in mock response
    assert result.analysis is None


def test_recognize_upload_mock_analysis():
    from unittest.mock import patch, MagicMock
    svc = RecognitionService(mock_scenario="clear")
    with patch("backend.services.recognition_service.validate_image_bytes", return_value="jpg"), \
         patch("backend.services.recognition_service.fix_exif_orientation", side_effect=lambda x: x), \
         patch("backend.services.recognition_service.upload_image", return_value="u1/original/abc.jpg"), \
         patch("backend.services.recognition_service.generate_presigned_url", return_value="https://s3.example.com/img"):
        result = svc.recognize_upload(b"\xff\xd8\xff" + b"\x00" * 100, "u1", "test.jpg")
    assert result.candidate is not None
    assert result.candidate.analysis is not None
    assert result.candidate.analysis.explanation != ""
