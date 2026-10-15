"""Processors package – tầng tính toán chỉ số ETL.

Import các sub-module theo thứ tự phụ thuộc:
    models → config → _math → geometry / velocity / quality
    → annotator_stats → segmentation
"""
from . import geometry, velocity, quality, segmentation
from .annotator_stats import build_annotator_stats, AnnotatorStats
from .models import Annotator, Defect, GroundTruthEval, Job, Label, Review
from .config import THRESHOLDS, Thresholds
from .segmentation import (
    VelocitySegment,
    QualityRiskFlag,
    FinalSegment,
    AnnotatorClassification,
    classify_annotator,
    segment_annotators,
)

__all__ = [
    # sub-modules
    "geometry", "velocity", "quality", "segmentation",
    # stats builder
    "build_annotator_stats", "AnnotatorStats",
    # models
    "Annotator", "Defect", "GroundTruthEval", "Job", "Label", "Review",
    # config
    "THRESHOLDS", "Thresholds",
    # segmentation types
    "VelocitySegment", "QualityRiskFlag", "FinalSegment",
    "AnnotatorClassification", "classify_annotator", "segment_annotators",
]
