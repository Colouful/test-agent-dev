import pytest
from backend.services.recognition_service import RecognitionService


def test_mock_clear_has_new_analysis():
    """MOCK 'clear' scenario 必须返回新格式 analysis（含 solution_summary 等）"""
    svc = RecognitionService(mock_scenario="clear")
    result = svc.recognize(b"fake", user_id="u1", image_key="test.jpg")
    assert result.status in ("high_confidence", "pending_review")
    assert result.analysis is not None
    # 新必填字段
    assert "solution_summary" in result.analysis
    assert "solution_steps" in result.analysis
    assert isinstance(result.analysis["solution_steps"], list)
    assert len(result.analysis["solution_steps"]) >= 1
    assert "knowledge_points" in result.analysis
    kp = result.analysis["knowledge_points"]
    assert isinstance(kp, dict)
    assert "core" in kp and "prerequisite" in kp and "related" in kp
    assert "key_examination" in result.analysis
    assert "error_analysis" in result.analysis
    ea = result.analysis["error_analysis"]
    assert "type" in ea and "reason" in ea and "improvement" in ea


def test_mock_clear_has_practice_questions():
    svc = RecognitionService(mock_scenario="clear")
    result = svc.recognize(b"fake", user_id="u1", image_key="test.jpg")
    assert result.analysis is not None
    pqs = result.analysis.get("practice_questions", [])
    assert isinstance(pqs, list)
    assert len(pqs) >= 1
    pq = pqs[0]
    assert "content" in pq and "answer" in pq and "explanation" in pq


def test_mock_non_question_no_analysis():
    svc = RecognitionService(mock_scenario="non_question")
    result = svc.recognize(b"fake", user_id="u1", image_key="test.jpg")
    assert result.status == "error"
    assert result.analysis is None


def test_mock_blurry_no_analysis():
    svc = RecognitionService(mock_scenario="blurry")
    result = svc.recognize(b"fake", user_id="u1", image_key="test.jpg")
    assert result.analysis is None


def test_analysis_missing_required_key_returns_null():
    """analysis dict 缺少 solution_summary 时应返回 null（R2）"""
    from unittest.mock import patch
    svc = RecognitionService(mock_scenario="clear")
    bad_analysis = {
        # solution_summary 缺失
        "solution_steps": [{"step": 1, "title": "步骤", "content": "内容"}],
        "knowledge_points": {"core": [], "prerequisite": [], "related": []},
        "key_examination": "考查",
        "error_analysis": {"type": "计算错误", "reason": "出错", "improvement": []},
    }
    broken_response = {
        "content": "题目", "correct_answer": "答案", "confidence": 0.9,
        "subject": "数学", "question_type": "fill", "analysis": bad_analysis,
    }
    with patch.object(svc, "_call_bedrock", return_value=broken_response):
        result = svc.recognize(b"fake", user_id="u1", image_key="test.jpg")
    assert result.analysis is None


def test_recognize_upload_mock_has_new_analysis():
    from unittest.mock import patch
    svc = RecognitionService(mock_scenario="clear")
    with patch("backend.services.recognition_service.validate_image_bytes", return_value="jpg"), \
         patch("backend.services.recognition_service.fix_exif_orientation", side_effect=lambda x: x), \
         patch("backend.services.recognition_service.upload_image", return_value="u1/original/abc.jpg"), \
         patch("backend.services.recognition_service.generate_presigned_url", return_value="https://s3.example.com/img"):
        result = svc.recognize_upload(b"\xff\xd8\xff" + b"\x00" * 100, "u1", "test.jpg")
    assert result.candidate is not None
    assert result.candidate.analysis is not None
    assert result.candidate.analysis.solution_summary != ""
    assert len(result.candidate.analysis.solution_steps) >= 1
    assert len(result.candidate.analysis.practice_questions) >= 1
