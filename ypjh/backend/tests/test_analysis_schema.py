import pytest
from pydantic import ValidationError
from backend.schemas.recognition import AnalysisOut, QuestionCandidateOut
from backend.schemas.question import QuestionCreate, QuestionOut
from datetime import datetime


def test_analysis_out_valid():
    a = AnalysisOut(
        explanation="解题过程",
        knowledge_points=["三角函数", "象限"],
        key_examination="考查象限判断",
        error_reason="忽略负号",
    )
    assert a.explanation == "解题过程"
    assert a.knowledge_points == ["三角函数", "象限"]


def test_analysis_out_missing_field():
    with pytest.raises(ValidationError):
        AnalysisOut(explanation="x", knowledge_points=[], key_examination="y")
        # error_reason missing → ValidationError


def test_candidate_out_with_analysis():
    c = QuestionCandidateOut(
        content="题目",
        correct_answer="答案",
        confidence=0.9,
        analysis=AnalysisOut(
            explanation="解析",
            knowledge_points=["知识点"],
            key_examination="考查",
            error_reason="原因",
        ),
    )
    assert c.analysis is not None
    assert c.analysis.error_reason == "原因"


def test_candidate_out_analysis_none():
    c = QuestionCandidateOut(content="题目", correct_answer="答案", confidence=0.8)
    assert c.analysis is None


def test_question_create_with_analysis():
    q = QuestionCreate(
        content="题目",
        correct_answer="答案",
        analysis={"explanation": "x", "knowledge_points": [], "key_examination": "y", "error_reason": "z"},
    )
    assert q.analysis is not None


def test_question_create_analysis_none():
    q = QuestionCreate(content="题目", correct_answer="答案")
    assert q.analysis is None
