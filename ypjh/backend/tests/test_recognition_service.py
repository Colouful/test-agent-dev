"""
识别服务测试 — 严格遵守 REQ-10：
- 验结构和契约，不断言具体识别文字内容
- 验置信度范围，不断言具体数值
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.recognition_service import RecognitionService


class TestRecognitionStructure:
    """验结构：响应格式契约。"""

    def test_result_has_status_field(self) -> None:
        svc = RecognitionService(mock_scenario="clear")
        result = svc.recognize(b"fake-image-bytes", user_id="test-user")
        assert result.status in ("high_confidence", "pending_review", "error")

    def test_high_confidence_has_candidate(self) -> None:
        svc = RecognitionService(mock_scenario="clear")
        result = svc.recognize(b"fake-image-bytes", user_id="test-user")
        assert result.status == "high_confidence"
        assert result.candidate is not None

    def test_candidate_content_nonempty(self) -> None:
        svc = RecognitionService(mock_scenario="clear")
        result = svc.recognize(b"fake-image-bytes", user_id="test-user")
        assert result.candidate is not None
        assert len(result.candidate.content) > 0  # 非空，不断言具体内容

    def test_candidate_correct_answer_nonempty(self) -> None:
        svc = RecognitionService(mock_scenario="clear")
        result = svc.recognize(b"fake-image-bytes", user_id="test-user")
        assert result.candidate is not None
        assert len(result.candidate.correct_answer) > 0  # 非空，不断言具体内容

    def test_confidence_in_valid_range(self) -> None:
        svc = RecognitionService(mock_scenario="clear")
        result = svc.recognize(b"fake-image-bytes", user_id="test-user")
        assert result.candidate is not None
        assert 0.0 <= result.candidate.confidence <= 1.0  # 范围，不断言具体值


class TestRecognitionContracts:
    """验契约：R2/R4 业务规则。"""

    def test_r4_low_confidence_returns_pending_review(self) -> None:
        """R4：低置信度不得直接入库，必须标记 pending_review。"""
        svc = RecognitionService(mock_scenario="blurry")
        result = svc.recognize(b"blurry-image", user_id="test-user")
        assert result.status == "pending_review"

    def test_r4_pending_review_has_error_hint(self) -> None:
        """R4：pending_review 状态必须有用户可读的提示。"""
        svc = RecognitionService(mock_scenario="blurry")
        result = svc.recognize(b"blurry-image", user_id="test-user")
        assert result.error_hint is not None
        assert len(result.error_hint) > 0

    def test_r2_missing_confidence_treated_as_zero(self) -> None:
        """R2：confidence 缺失时，结果应为 pending_review（按 0 处理），不得 error。"""
        svc = RecognitionService(mock_scenario="empty")
        result = svc.recognize(b"empty-response-image", user_id="test-user")
        # confidence=0.0 < 0.7 → pending_review，不应该 error
        assert result.status == "pending_review"

    def test_r2_missing_confidence_not_high_confidence(self) -> None:
        """R2：confidence 缺失时，绝不能是 high_confidence（即不得默认 1.0）。"""
        svc = RecognitionService(mock_scenario="empty")
        result = svc.recognize(b"empty-response-image", user_id="test-user")
        assert result.status != "high_confidence"

    def test_image_key_present_on_success(self) -> None:
        """识别成功时必须返回 image_key（S3 存储位置）。"""
        svc = RecognitionService(mock_scenario="clear")
        result = svc.recognize(b"fake-image-bytes", user_id="test-user")
        assert result.image_key is not None
        assert len(result.image_key) > 0
