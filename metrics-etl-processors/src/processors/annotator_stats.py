"""Dataclass trung gian AnnotatorStats – gom chỉ số theo từng annotator (WBS 2.4).

Được dùng làm đầu vào cho segmentation.py.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Dict, List, Optional, Sequence

from .config import THRESHOLDS
from ._math import safe_div
from .models import Annotator, GroundTruthEval, Job, Review

logger = logging.getLogger(__name__)


@dataclass
class AnnotatorStats:
    """Tổng hợp chỉ số của một annotator tại thời điểm as_of."""
    annotator_id: str
    full_name: str

    # Tiến độ
    total_jobs_completed: int = 0
    total_frames_completed: int = 0
    total_objects: int = 0
    total_active_hours: float = 0.0

    # Vận tốc
    avg_frames_per_hour: Optional[float] = None   # frames/giờ
    avg_objects_per_hour: Optional[float] = None

    # Thâm niên
    tenure_days: Optional[int] = None             # None nếu không có joined_date

    # Hoạt động gần đây
    active_hours_7d: float = 0.0                  # giờ trong 7 ngày gần nhất

    # Chất lượng
    first_time_pass_rate: Optional[float] = None  # None nếu chưa có review
    rejection_rate: Optional[float] = None
    mean_f1_score: Optional[float] = None         # None nếu không có GT


def build_annotator_stats(
    annotators: Sequence[Annotator],
    jobs: Sequence[Job],
    reviews: Sequence[Review],
    gt_evals: Sequence[GroundTruthEval] = (),
    *,
    as_of: date,
    inactive_window_days: int = THRESHOLDS.inactive_window_days,
) -> List[AnnotatorStats]:
    """Xây dựng AnnotatorStats cho từng annotator từ danh sách jobs/reviews/gt.

    annotators: danh sách annotator (từ dim_annotators hoặc snapshot).
    jobs: tất cả fact_job_sessions.
    reviews: tất cả fact_qa_reviews.
    gt_evals: fact_ground_truth_eval (có thể rỗng).
    as_of: ngày tính chỉ số (thường là ngày snapshot).
    """
    # Index theo annotator_id
    jobs_by_annotator: Dict[str, List[Job]] = {a.annotator_id: [] for a in annotators}
    for j in jobs:
        if j.annotator_id in jobs_by_annotator:
            jobs_by_annotator[j.annotator_id].append(j)
        elif j.annotator_id is not None:
            # Job được giao cho người không trong danh sách annotators
            logger.warning("Job %d có annotator_id '%s' không tìm thấy trong danh sách annotator; bỏ qua",
                           j.job_id, j.annotator_id)

    # Index reviews theo job_id để lọc theo annotator
    reviews_by_job: Dict[int, List[Review]] = {}
    for r in reviews:
        reviews_by_job.setdefault(r.job_id, []).append(r)

    # Index GT evals theo job_id
    gt_by_job: Dict[int, List[GroundTruthEval]] = {}
    for e in gt_evals:
        gt_by_job.setdefault(e.job_id, []).append(e)

    # Cửa sổ 7 ngày gần nhất
    cutoff_inactive = as_of - timedelta(days=inactive_window_days - 1)

    stats_list: List[AnnotatorStats] = []
    for ann in annotators:
        a_jobs = jobs_by_annotator[ann.annotator_id]
        completed_jobs = [j for j in a_jobs if j.status == "completed"]
        total_hours = sum(j.active_time_hours for j in a_jobs)
        total_frames = sum(j.total_frames for j in completed_jobs)
        total_objects = sum(j.total_objects for j in a_jobs)

        # Vận tốc
        avg_fps = safe_div(total_frames, total_hours)
        avg_ops = safe_div(total_objects, total_hours)

        # Hoạt động trong 7 ngày gần nhất (xấp xỉ bằng giờ của job nộp trong cửa sổ)
        hours_7d = sum(
            j.active_time_hours for j in a_jobs
            if j.date_key is not None and j.date_key >= cutoff_inactive
        )

        # Thâm niên
        tenure = None
        if ann.joined_date is not None:
            tenure = (as_of - ann.joined_date).days

        # Chất lượng: gom review của các job do annotator này thực hiện
        a_job_ids = {j.job_id for j in a_jobs}
        a_reviews: List[Review] = []
        for jid in a_job_ids:
            a_reviews.extend(reviews_by_job.get(jid, []))

        ftpr = None
        rr = None
        if a_reviews:
            first_reviews = [r for r in a_reviews if r.review_iteration == 1]
            if first_reviews:
                accepted_first = sum(1 for r in first_reviews if r.review_decision == "Accepted")
                ftpr = safe_div(accepted_first, len(first_reviews))
            rejected = sum(1 for r in a_reviews if r.review_decision == "Rejected")
            rr = safe_div(rejected, len(a_reviews))

        # Ground Truth F1
        a_gt: List[GroundTruthEval] = []
        for jid in a_job_ids:
            a_gt.extend(gt_by_job.get(jid, []))

        f1_vals = []
        for e in a_gt:
            if e.f1_score is not None:
                f1_vals.append(e.f1_score)
            elif e.precision is not None and e.recall is not None:
                denom = e.precision + e.recall
                if denom > 0:
                    f1_vals.append(2 * e.precision * e.recall / denom)
        mean_f1 = (sum(f1_vals) / len(f1_vals)) if f1_vals else None

        stats_list.append(AnnotatorStats(
            annotator_id=ann.annotator_id,
            full_name=ann.full_name,
            total_jobs_completed=len(completed_jobs),
            total_frames_completed=total_frames,
            total_objects=total_objects,
            total_active_hours=total_hours,
            avg_frames_per_hour=avg_fps,
            avg_objects_per_hour=avg_ops,
            tenure_days=tenure,
            active_hours_7d=hours_7d,
            first_time_pass_rate=ftpr,
            rejection_rate=rr,
            mean_f1_score=mean_f1,
        ))

    return stats_list
