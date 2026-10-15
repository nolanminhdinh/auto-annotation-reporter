"""Thuật toán phân khúc thành viên – Final Annotator Segmentation (WBS 2.4).

Ánh xạ sang mục 4.1 – 4.4 của PROJECT_ANALYTICS_SPEC.md.

Thứ tự đánh giá từ nhóm 1 → 7 (khớp đặc tả bảng 4.4):
    1  FAST_AND_FAULTY   – siêu nhanh AND rủi ro cao
    2  NEEDS_RETRAINING  – chậm AND rủi ro cao
    3  SLOW_BUT_STEADY   – chậm AND chất lượng đạt
    4  STAR_ANNOTATOR    – nhanh/đạt AND chất lượng đạt
    5  ONBOARDING        – thâm niên ≤ 14 ngày AND jobs ≤ 10
    6  INACTIVE          – active_hours_7d == 0
    7  CORE_PERFORMER    – các trường hợp còn lại

Khoảng hở bảng 4.4 (giả định #5): vận tốc 20–59 f/h AND rủi ro cao
không thuộc nhóm 1–4 → rơi vào CORE_PERFORMER.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Sequence

from .annotator_stats import AnnotatorStats
from .config import THRESHOLDS


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class VelocitySegment(str, Enum):
    """Mục 4.1 – Phân khúc vận tốc."""
    SUPER_FAST = "Vận tốc siêu nhanh"
    ON_TARGET   = "Vận tốc đạt chuẩn"
    AVERAGE     = "Vận tốc trung bình"
    SLOW        = "Vận tốc chậm / Cần hỗ trợ"


class QualityRiskFlag(str, Enum):
    """Mục 4.2 – Cờ rủi ro chất lượng."""
    HIGH_RISK  = "Rủi ro chất lượng cao"
    ACCEPTABLE = "Chất lượng đạt chuẩn"


class FinalSegment(str, Enum):
    """Mục 4.4 – 7 nhóm phân khúc cuối."""
    FAST_AND_FAULTY  = "Nguy cơ gán ẩu (Fast & Faulty)"
    NEEDS_RETRAINING = "Cần đào tạo lại (Low Skill / Bottleneck)"
    SLOW_BUT_STEADY  = "Cầu toàn quá mức (Slow but Steady)"
    STAR_ANNOTATOR   = "Nhân sự nòng cốt (Star Annotator)"
    ONBOARDING       = "Nhân sự mới đang làm quen (Onboarding)"
    INACTIVE         = "Ngủ đông / Không hoạt động (Inactive)"
    CORE_PERFORMER   = "Nhân sự nền tảng (Core Performer)"

    @property
    def priority(self) -> int:
        """Số thứ tự ưu tiên (1 = cao nhất)."""
        _order = [
            "FAST_AND_FAULTY", "NEEDS_RETRAINING", "SLOW_BUT_STEADY",
            "STAR_ANNOTATOR", "ONBOARDING", "INACTIVE", "CORE_PERFORMER",
        ]
        return _order.index(self.name) + 1

    @property
    def short_label(self) -> str:
        """Nhãn ngắn khớp tên slicer Power BI."""
        _labels = {
            "FAST_AND_FAULTY": "Nguy cơ gán ẩu",
            "NEEDS_RETRAINING": "Cần đào tạo lại",
            "SLOW_BUT_STEADY": "Cầu toàn quá mức",
            "STAR_ANNOTATOR": "Nhân sự nòng cốt",
            "ONBOARDING": "Nhân sự mới",
            "INACTIVE": "Không hoạt động",
            "CORE_PERFORMER": "Nhân sự nền tảng",
        }
        return _labels[self.name]

    @property
    def action(self) -> str:
        """Hành động can thiệp theo bảng 4.4."""
        _actions = {
            "FAST_AND_FAULTY": "Đình chỉ giao batch mới; yêu cầu rà soát lại 100% job đã nộp.",
            "NEEDS_RETRAINING": "Gửi đào tạo lại 1-on-1; chỉ giao task đơn giản.",
            "SLOW_BUT_STEADY": "Hướng dẫn phím tắt CVAT; hỗ trợ AI Pre-annotation.",
            "STAR_ANNOTATOR": "Khen thưởng & thăng cấp; giao lô ca khó hoặc đào tạo Reviewer.",
            "ONBOARDING": "Theo dõi sát; review 100% trong 10 job đầu.",
            "INACTIVE": "Thu hồi tài khoản/job; tái phân bổ cho thành viên khác.",
            "CORE_PERFORMER": "Duy trì tiến độ chuẩn; giao việc theo kế hoạch định kỳ.",
        }
        return _actions[self.name]


# ---------------------------------------------------------------------------
# Intermediate classification result
# ---------------------------------------------------------------------------

@dataclass
class AnnotatorClassification:
    annotator_id: str
    velocity_segment: VelocitySegment
    quality_risk_flag: QualityRiskFlag
    final_segment: FinalSegment


# ---------------------------------------------------------------------------
# Core classification functions
# ---------------------------------------------------------------------------

def classify_velocity(stats: AnnotatorStats) -> VelocitySegment:
    """Mục 4.1 – phân khúc vận tốc từ avg_frames_per_hour.

    None → coi là 0 (theo ngữ nghĩa NULL của SQL trong đặc tả).
    """
    fps = stats.avg_frames_per_hour or 0.0
    if fps >= THRESHOLDS.velocity_super_fast:
        return VelocitySegment.SUPER_FAST
    if fps >= THRESHOLDS.velocity_on_target:
        return VelocitySegment.ON_TARGET
    if fps >= THRESHOLDS.velocity_average:
        return VelocitySegment.AVERAGE
    return VelocitySegment.SLOW


def classify_quality_risk(stats: AnnotatorStats) -> QualityRiskFlag:
    """Mục 4.2 – cờ rủi ro chất lượng.

    Rủi ro cao nếu:
        FTPR < 0.80  OR  rejection_rate >= 0.20  OR  F1 < 0.85
    Theo giả định: FTPR/Rejection None không kích hoạt cờ; F1 None → 1.0.
    """
    ftpr = stats.first_time_pass_rate      # None không kích hoạt
    rr   = stats.rejection_rate            # None không kích hoạt
    f1   = stats.mean_f1_score if stats.mean_f1_score is not None else 1.0  # ISNULL → 1.0

    if (
        (ftpr is not None and ftpr < THRESHOLDS.ftpr_risk_threshold)
        or (rr is not None and rr >= THRESHOLDS.rejection_risk_threshold)
        or f1 < THRESHOLDS.f1_risk_threshold
    ):
        return QualityRiskFlag.HIGH_RISK
    return QualityRiskFlag.ACCEPTABLE


def classify_annotator(stats: AnnotatorStats) -> AnnotatorClassification:
    """Phân khúc toàn diện một annotator, đánh giá tuần tự từ nhóm 1 → 7."""
    vel  = classify_velocity(stats)
    qual = classify_quality_risk(stats)

    # Nhóm 1: Siêu nhanh AND rủi ro cao
    if vel == VelocitySegment.SUPER_FAST and qual == QualityRiskFlag.HIGH_RISK:
        final = FinalSegment.FAST_AND_FAULTY

    # Nhóm 2: Chậm AND rủi ro cao
    elif vel == VelocitySegment.SLOW and qual == QualityRiskFlag.HIGH_RISK:
        final = FinalSegment.NEEDS_RETRAINING

    # Nhóm 3: Chậm AND chất lượng đạt
    elif vel == VelocitySegment.SLOW and qual == QualityRiskFlag.ACCEPTABLE:
        final = FinalSegment.SLOW_BUT_STEADY

    # Nhóm 4: Nhanh/đạt AND chất lượng đạt
    elif vel in (VelocitySegment.SUPER_FAST, VelocitySegment.ON_TARGET) and qual == QualityRiskFlag.ACCEPTABLE:
        final = FinalSegment.STAR_ANNOTATOR

    # Nhóm 5: Onboarding (thâm niên ≤ 14 ngày AND ≤ 10 job completed)
    elif (
        stats.tenure_days is not None
        and stats.tenure_days <= THRESHOLDS.onboarding_days
        and stats.total_jobs_completed <= THRESHOLDS.onboarding_max_jobs
    ):
        final = FinalSegment.ONBOARDING

    # Nhóm 6: Inactive (không có giờ trong 7 ngày gần nhất)
    elif stats.active_hours_7d == 0:
        final = FinalSegment.INACTIVE

    # Nhóm 7: Các trường hợp còn lại
    else:
        final = FinalSegment.CORE_PERFORMER

    return AnnotatorClassification(
        annotator_id=stats.annotator_id,
        velocity_segment=vel,
        quality_risk_flag=qual,
        final_segment=final,
    )


def segment_annotators(stats_list: Sequence[AnnotatorStats]) -> List[AnnotatorClassification]:
    """Phân khúc toàn bộ danh sách annotator."""
    return [classify_annotator(s) for s in stats_list]
