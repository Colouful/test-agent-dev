import pytest
from pydantic import ValidationError
from backend.schemas.recognition import (
    AnalysisOut, SolutionStep, KnowledgePoints,
    ErrorAnalysis, PracticeQuestion, QuestionCandidateOut,
)
from backend.schemas.question import QuestionCreate, QuestionOut
from datetime import datetime


def test_solution_step_valid():
    s = SolutionStep(step=1, title="判断增减性", content="k>0，图像上升")
    assert s.step == 1
    assert s.title == "判断增减性"


def test_knowledge_points_defaults():
    kp = KnowledgePoints(core=["一次函数"])
    assert kp.prerequisite == []
    assert kp.related == []


def test_error_analysis_valid():
    ea = ErrorAnalysis(type="条件遗漏", reason="忽略截距条件", improvement=["先看 k 再看 b"])
    assert ea.type == "条件遗漏"
    assert len(ea.improvement) == 1


def test_practice_question_valid():
    pq = PracticeQuestion(content="已知 y=2x-1，图像在哪些象限？", answer="一三四象限", explanation="k>0上升，b<0截距负")
    assert pq.answer == "一三四象限"


def test_analysis_out_valid():
    a = AnalysisOut(
        solution_summary="先看 k 再看 b",
        solution_steps=[SolutionStep(step=1, title="判断增减性", content="k>0上升")],
        knowledge_points=KnowledgePoints(core=["一次函数"]),
        key_examination="考查 k、b 对图像的影响",
        error_analysis=ErrorAnalysis(type="条件遗漏", reason="忽略截距", improvement=["看截距"]),
    )
    assert a.solution_summary == "先看 k 再看 b"
    assert len(a.solution_steps) == 1
    assert a.common_mistakes == []
    assert a.practice_questions == []


def test_analysis_out_missing_required():
    with pytest.raises(ValidationError):
        AnalysisOut(
            solution_summary="思路",
            solution_steps=[],
            knowledge_points=KnowledgePoints(core=[]),
            # key_examination 缺失 → ValidationError
            error_analysis=ErrorAnalysis(type="计算错误", reason="x", improvement=[]),
        )


def test_candidate_out_with_new_analysis():
    a = AnalysisOut(
        solution_summary="代入计算",
        solution_steps=[SolutionStep(step=1, title="代入", content="x=3 代入得 16")],
        knowledge_points=KnowledgePoints(core=["函数求值"]),
        key_examination="考查代入求值",
        error_analysis=ErrorAnalysis(type="计算错误", reason="漏算", improvement=["逐项代入"]),
        practice_questions=[PracticeQuestion(content="求 f(2)", answer="3", explanation="代入得 3")],
    )
    c = QuestionCandidateOut(content="题目", correct_answer="答案", confidence=0.9, analysis=a)
    assert c.analysis is not None
    assert c.analysis.key_examination == "考查代入求值"
    assert len(c.analysis.practice_questions) == 1


def test_candidate_out_analysis_none():
    c = QuestionCandidateOut(content="题目", correct_answer="答案", confidence=0.8)
    assert c.analysis is None


def test_question_create_with_analysis():
    q = QuestionCreate(
        content="题目",
        correct_answer="答案",
        analysis={
            "solution_summary": "思路",
            "solution_steps": [{"step": 1, "title": "步骤", "content": "内容"}],
            "knowledge_points": {"core": ["知识点"], "prerequisite": [], "related": []},
            "key_examination": "考查",
            "error_analysis": {"type": "计算错误", "reason": "出错", "improvement": []},
        },
    )
    assert q.analysis is not None


def test_question_create_analysis_none():
    q = QuestionCreate(content="题目", correct_answer="答案")
    assert q.analysis is None
