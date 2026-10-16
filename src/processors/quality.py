"""Tính toán chỉ số chất lượng QA/QC (WBS 2.2).

Ánh xạ sang DAX Measures:
    #8  First_Time_Pass_Rate         → first_time_pass_rate
    #9  Rejection_Rate               → rejection_rate
    #10 Total_Defects                → total_defects
    #11 Defect_Density_Per_100F      → defect_density_per_100_frames
    #12 Avg_Defects_Per_Job          → avg_defects_per_job
    #13 Avg_mIoU_Score               → avg_miou
    #14 Avg_F1_Score                 → avg_f1

Taxonomy lỗi (readmereport.md mục 4.6):
    BOX_LOOSE / BOX_TIGHT_CLIPPED → 'box_displacement'
    MISLABELED                    → 'wrong_class'
    MISSED_OBJECT                 → 'missing_object'
    ATTRIBUTE_ERROR               → 'wrong_attr'
    các mã lạ khác                → 'unclassified' + cảnh báo log
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional, Sequence

from ._math import mean_or_none, safe_div
from .models import Defect, GroundTruthEval, Review

logger = logging.getLogger(__name__)

# Ánh xạ mã raw → 4 nhóm chuẩn hóa
_DEFECT_TAXONOMY: Dict[str, str] = {
    "BOX_LOOSE": "box_displacement",
    "BOX_TIGHT_CLIPPED": "box_displacement",
    "box_displacement": "box_displacement",
    "MISLABELED": "wrong_class",
    "wrong_class": "wrong_class",
    "MISSED_OBJECT": "missing_object",
    "missing_object": "missing_object",
    "ATTRIBUTE_ERROR": "wrong_attr",
    "wrong_attr": "wrong_attr",
}
_CANONICAL_TYPES = ("box_displacement", "wrong_class", "missing_object", "wrong_attr")


# ---------------------------------------------------------------------------
# Review-level metrics
# ---------------------------------------------------------------------------

def first_time_pass_rate(reviews: Sequence[Review]) -> Optional[float]:
    """DAX #8 – tỷ lệ job được duyệt ngay ở vòng review đầu tiên (iteration == 1).

    Trả None nếu không có review nào ở vòng 1.
    """
    first_reviews = [r for r in reviews if r.review_iteration == 1]
    if not first_reviews:
        return None
    accepted = sum(1 for r in first_reviews if r.review_decision == "Accepted")
    return safe_div(accepted, len(first_reviews))


def rejection_rate(reviews: Sequence[Review]) -> Optional[float]:
    """DAX #9 – tỷ lệ lượt review bị Reject (mọi iteration).

    Trả None nếu không có review nào.
    """
    if not reviews:
        return None
    rejected = sum(1 for r in reviews if r.review_decision == "Rejected")
    return safe_div(rejected, len(reviews))


# ---------------------------------------------------------------------------
# Defect-level metrics
# ---------------------------------------------------------------------------

def normalize_defect_type(raw_type: str) -> str:
    """Chuẩn hóa mã lỗi về 4 nhóm chuẩn; ghi cảnh báo nếu không nhận dạng được."""
    normalized = _DEFECT_TAXONOMY.get(raw_type)
    if normalized is None:
        logger.warning("Mã lỗi không nhận dạng được: '%s'; xếp vào 'unclassified'", raw_type)
        return "unclassified"
    return normalized


def total_defects(defects: Sequence[Defect]) -> int:
    """DAX #10 – tổng số lỗi do Reviewer ghi nhận."""
    return len(defects)


def defect_type_counts(defects: Sequence[Defect]) -> Dict[str, int]:
    """Đếm số lượng theo từng loại lỗi chuẩn hóa (4 nhóm + unclassified)."""
    counts: Dict[str, int] = {t: 0 for t in _CANONICAL_TYPES}
    for d in defects:
        canonical = normalize_defect_type(d.defect_type)
        counts[canonical] = counts.get(canonical, 0) + 1
    return counts


def defect_density_per_100_frames(
    n_defects: int,
    completed_frames: int,
) -> Optional[float]:
    """DAX #11 – mật độ lỗi / 100 frame hoàn thành."""
    return safe_div(n_defects * 100.0, completed_frames)


def avg_defects_per_job(
    n_defects: int,
    reviews: Sequence[Review],
) -> Optional[float]:
    """DAX #12 – trung bình số bug trên mỗi job khác nhau có review."""
    distinct_jobs = len({r.job_id for r in reviews})
    return safe_div(n_defects, distinct_jobs)


# ---------------------------------------------------------------------------
# Ground Truth metrics
# ---------------------------------------------------------------------------

def avg_miou(gt_evals: Sequence[GroundTruthEval]) -> Optional[float]:
    """DAX #13 – điểm mIoU trung bình (bỏ qua giá trị None)."""
    return mean_or_none(e.mean_iou for e in gt_evals)


def f1_from_precision_recall(
    precision: Optional[float],
    recall: Optional[float],
) -> Optional[float]:
    """Tính F1 từ Precision và Recall nếu cả hai đều có."""
    if precision is None or recall is None:
        return None
    denom = precision + recall
    return safe_div(2.0 * precision * recall, denom)


def avg_f1(gt_evals: Sequence[GroundTruthEval]) -> Optional[float]:
    """DAX #14 – F1 trung bình: dùng f1_score nếu có, không thì tính từ P/R."""
    scores: List[Optional[float]] = []
    for e in gt_evals:
        if e.f1_score is not None:
            scores.append(e.f1_score)
        else:
            scores.append(f1_from_precision_recall(e.precision, e.recall))
    return mean_or_none(scores)
