import pytest
from backend.core.sm2 import calculate_next_review


# --- 失败路径（score < 3）---
def test_score_1_resets_interval():
    ef, interval, count = calculate_next_review(
        score=1, ease_factor=2.5, interval_days=6, review_count=3
    )
    assert interval == 1
    assert count == 0
    assert ef == 2.5  # 失败时不修改 EF


def test_score_2_resets_interval():
    ef, interval, count = calculate_next_review(
        score=2, ease_factor=2.5, interval_days=10, review_count=5
    )
    assert interval == 1
    assert count == 0


# --- 成功路径（score >= 3）---
def test_score_3_first_review():
    ef, interval, count = calculate_next_review(
        score=3, ease_factor=2.5, interval_days=1, review_count=0
    )
    assert count == 1
    assert interval == 1


def test_score_3_second_review():
    ef, interval, count = calculate_next_review(
        score=3, ease_factor=2.5, interval_days=1, review_count=1
    )
    assert count == 2
    assert interval == 6


def test_score_5_third_review():
    ef, interval, count = calculate_next_review(
        score=5, ease_factor=2.5, interval_days=6, review_count=2
    )
    assert count == 3
    assert interval == round(6 * 2.5)  # 15
    assert ef > 2.5  # score=5 时 EF 增长


def test_ease_factor_minimum_1_3():
    # score=1 时 EF 不变，但 score=3 且初始 EF=1.4 时不应低于 1.3
    ef, _, _ = calculate_next_review(
        score=3, ease_factor=1.4, interval_days=1, review_count=0
    )
    assert ef >= 1.3


def test_ease_factor_never_below_floor():
    # 连续低分后 EF 不低于 1.3
    ef = 1.31
    for _ in range(10):
        ef, _, _ = calculate_next_review(
            score=3, ease_factor=ef, interval_days=1, review_count=0
        )
    assert ef >= 1.3
