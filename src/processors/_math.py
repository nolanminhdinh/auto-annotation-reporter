"""Hàm trợ giúp toán học nội bộ.

Tất định, không side-effect, không import gì ngoài stdlib.
"""
from __future__ import annotations

from typing import Iterable, Optional


def safe_div(numerator: float, denominator: float) -> Optional[float]:
    """Chia an toàn: trả None khi mẫu số = 0 (thay vì ZeroDivisionError hoặc inf).

    Tương đương DAX DIVIDE(a, b, BLANK()) — không trả 0 để tránh số liệu giả.
    """
    if denominator == 0:
        return None
    return numerator / denominator


def mean_or_none(values: Iterable[Optional[float]]) -> Optional[float]:
    """Trung bình cộng bỏ qua None; trả None nếu không có giá trị nào."""
    nums = [v for v in values if v is not None]
    if not nums:
        return None
    return sum(nums) / len(nums)
