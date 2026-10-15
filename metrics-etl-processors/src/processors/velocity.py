"""Tính toán vận tốc gán nhãn và tiến độ batch (WBS 2.1).

Ánh xạ sang 20 DAX Measures (PROJECT_ANALYTICS_SPEC.md mục 5):
    #1  Total_Completed_Frames      → total_completed_frames
    #2  Total_Objects_Created       → total_objects_created
    #3  Total_Active_Hours          → total_active_hours
    #4  Velocity_Frames_Per_Hour    → velocity_frames_per_hour
    #5  Velocity_Objects_Per_Hour   → velocity_objects_per_hour
    #6  Avg_Time_Per_Frame_Mins     → avg_time_per_frame_minutes
    #7  Avg_Time_Per_Object_Secs    → avg_time_per_object_seconds
    #19 System_Avg_Velocity         → velocity_frames_per_hour(tất cả job)
    #20 Project_Progress_Pct        → progress_ratio  (× 100 khi export CSV)

Lưu ý 4.1 (readmereport.md): Velocity_Frames_Per_Hour lấy frame của job
**completed** chia cho giờ của **mọi job**. Giữ nguyên để khớp DAX hiện tại.
Nếu Lead sửa DAX, đổi bằng tham số hours_basis="completed".
"""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date, datetime, timezone
from typing import Iterable, List, Optional, Sequence

from .config import THRESHOLDS
from ._math import safe_div
from .models import Job

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Aggregate helpers
# ---------------------------------------------------------------------------

def total_completed_frames(jobs: Sequence[Job]) -> int:
    """DAX #1 – tổng frame của job có status == 'completed'."""
    return sum(j.total_frames for j in jobs if j.status == "completed")


def total_objects_created(jobs: Sequence[Job]) -> int:
    """DAX #2 – tổng đối tượng đã gán (mọi job, mọi status)."""
    return sum(j.total_objects for j in jobs)


def total_active_hours(jobs: Sequence[Job]) -> float:
    """DAX #3 – tổng giờ thao tác thực tế (mọi job, không lọc status)."""
    return sum(j.active_time_hours for j in jobs)


# ---------------------------------------------------------------------------
# Velocity measures
# ---------------------------------------------------------------------------

def velocity_frames_per_hour(
    jobs: Sequence[Job],
    *,
    hours_basis: str = "all",
) -> Optional[float]:
    """DAX #4 / #19 – vận tốc frames/giờ.

    hours_basis='all' (mặc định, khớp DAX): mẫu số là giờ của MỌI job.
    hours_basis='completed': mẫu số là giờ của job completed.
    """
    completed = total_completed_frames(jobs)
    if hours_basis == "completed":
        hours = sum(j.active_time_hours for j in jobs if j.status == "completed")
    else:
        hours = total_active_hours(jobs)
    return safe_div(completed, hours)


def velocity_objects_per_hour(jobs: Sequence[Job]) -> Optional[float]:
    """DAX #5 – số đối tượng gán nhãn / giờ."""
    return safe_div(total_objects_created(jobs), total_active_hours(jobs))


def avg_time_per_frame_minutes(jobs: Sequence[Job]) -> Optional[float]:
    """DAX #6 – phút trung bình để hoàn tất 1 frame (giờ × 60 / frame completed)."""
    hours = total_active_hours(jobs)
    frames = total_completed_frames(jobs)
    result = safe_div(hours * 60.0, frames)
    return result


def avg_time_per_object_seconds(jobs: Sequence[Job]) -> Optional[float]:
    """DAX #7 – giây trung bình để vẽ xong 1 đối tượng (giờ × 3600 / objects)."""
    hours = total_active_hours(jobs)
    objects = total_objects_created(jobs)
    return safe_div(hours * 3600.0, objects)


# ---------------------------------------------------------------------------
# Progress & ETA
# ---------------------------------------------------------------------------

def progress_ratio(
    completed_frames: int,
    target_frames: Optional[int],
) -> Optional[float]:
    """DAX #20 – tỷ số 0–1; nhân 100 khi ghi CSV (cột progress_pct)."""
    if not target_frames:
        return None
    return safe_div(completed_frames, target_frames)


def backlog_frames(
    completed_frames: int,
    target_frames: Optional[int],
) -> Optional[int]:
    """Số frame còn tồn đọng."""
    if target_frames is None:
        return None
    return max(0, target_frames - completed_frames)


def completed_frames_per_day(
    jobs: Sequence[Job],
    as_of: date,
    window_days: int = THRESHOLDS.eta_window_days,
) -> float:
    """Trung bình frame hoàn thành/ngày trong cửa sổ N ngày gần nhất."""
    daily: dict[date, int] = defaultdict(int)
    for j in jobs:
        if j.status == "completed" and j.date_key is not None:
            daily[j.date_key] += j.total_frames

    # Chỉ lấy N ngày trong cửa sổ
    from datetime import timedelta
    cutoff = as_of - timedelta(days=window_days - 1)
    relevant = [v for d, v in daily.items() if cutoff <= d <= as_of]
    if not relevant:
        return 0.0
    return sum(relevant) / window_days


def projected_completion_date(
    backlog: Optional[int],
    frames_per_day: float,
    as_of: date,
) -> Optional[date]:
    """Dự báo ngày hoàn thành dựa trên backlog và vận tốc ngày."""
    from datetime import timedelta
    if backlog is None or backlog <= 0 or frames_per_day <= 0:
        return None
    import math
    days_needed = backlog / frames_per_day
    return as_of + timedelta(days=math.ceil(days_needed))


# ---------------------------------------------------------------------------
# Event log (lọc idle)
# ---------------------------------------------------------------------------

def active_seconds_from_events(
    timestamps: Iterable[datetime],
    idle_gap_seconds: int = THRESHOLDS.idle_gap_seconds,
) -> float:
    """Tính giờ làm việc thực từ event log, bỏ khoảng trống > idle_gap_seconds.

    timestamps: list datetime (UTC hoặc naive → coi là UTC).
    Trả về tổng giây hoạt động thực.
    """
    sorted_ts = sorted(t.replace(tzinfo=timezone.utc) if t.tzinfo is None else t
                       for t in timestamps)
    active = 0.0
    for i in range(1, len(sorted_ts)):
        delta = (sorted_ts[i] - sorted_ts[i - 1]).total_seconds()
        if delta <= idle_gap_seconds:
            active += delta
    return active
