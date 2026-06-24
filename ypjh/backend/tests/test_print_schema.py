import pytest
from pydantic import ValidationError
from backend.schemas.print_schema import PrintRequest


def test_print_request_defaults():
    req = PrintRequest(question_ids=["id1", "id2"])
    assert req.show_answer is True
    assert req.show_image is True
    assert req.layout == "single"


def test_print_request_max_50():
    with pytest.raises(ValidationError):
        PrintRequest(question_ids=[f"id{i}" for i in range(51)])


def test_print_request_empty_ids():
    with pytest.raises(ValidationError):
        PrintRequest(question_ids=[])


def test_print_request_layout_validation():
    with pytest.raises(ValidationError):
        PrintRequest(question_ids=["id1"], layout="invalid")
