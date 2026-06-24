from __future__ import annotations


def calculate_next_review(
    score: int,
    ease_factor: float,
    interval_days: int,
    review_count: int,
) -> tuple[float, int, int]:
    """SM-2 算法核心。返回 (new_ease_factor, new_interval_days, new_review_count)。"""
    if score < 3:
        # 失败：重置间隔，EF 不变
        return ease_factor, 1, 0

    # 成功
    new_count = review_count + 1
    if new_count == 1:
        new_interval = 1
    elif new_count == 2:
        new_interval = 6
    else:
        new_interval = round(interval_days * ease_factor)

    new_ef = ease_factor + (0.1 - (5 - score) * (0.08 + (5 - score) * 0.02))
    new_ef = max(1.3, new_ef)

    return new_ef, new_interval, new_count
