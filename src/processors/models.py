"""Dataclass đầu vào cho tầng processors.

Tên trường bám sát Data Dictionary (PROJECT_ANALYTICS_SPEC.md mục 3).
Không import gì ngoài stdlib để giữ nguyên tắc Python thuần.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional


# ---------------------------------------------------------------------------
# Dimension dataclasses
# ---------------------------------------------------------------------------

@dataclass
class Annotator:
    """Bảng dim_annotators."""
    annotator_id: str
    full_name: str = ""
    role: str = "Annotator"              # 'Annotator' | 'Reviewer' | 'Core'
    joined_date: Optional[date] = None


@dataclass
class Label:
    """Bảng dim_classes_labels."""
    label_id: int
    label_name: str
    label_category: str = ""
    color_hex: str = ""


# ---------------------------------------------------------------------------
# Fact dataclasses
# ---------------------------------------------------------------------------

@dataclass
class Job:
    """Bảng fact_job_sessions.

    active_time_hours = 0.0 khi snapshot không cung cấp log sự kiện.
    date_key = None khi job chưa completed.
    """
    job_id: int
    task_id: int
    annotator_id: Optional[str]
    status: str                          # 'annotation' | 'validation' | 'completed'
    total_frames: int
    total_objects: int
    active_time_hours: float = 0.0
    date_key: Optional[date] = None


@dataclass
class Review:
    """Bảng fact_qa_reviews."""
    review_id: str
    job_id: int
    reviewer_id: str
    review_iteration: int                # 1 = lần đầu, 2 = sau khi sửa, ...
    review_decision: str                 # 'Accepted' | 'Rejected'
    reviewed_at: Optional[datetime] = None


@dataclass
class Defect:
    """Bảng fact_qa_defects."""
    defect_id: str
    review_id: str
    frame_idx: int
    label_id: Optional[int]
    defect_type: str                     # 'box_displacement' | 'wrong_class' | 'missing_object' | 'wrong_attr'
    severity: str = "Minor"             # 'Blocker' | 'Major' | 'Minor'
    cvat_deep_link: str = ""


@dataclass
class GroundTruthEval:
    """Bảng fact_ground_truth_eval."""
    eval_id: str
    job_id: int
    mean_iou: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1_score: Optional[float] = None
