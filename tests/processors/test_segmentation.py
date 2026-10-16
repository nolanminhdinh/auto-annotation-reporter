"""Unit tests cho module segmentation (WBS 2.4)."""
from __future__ import annotations

import unittest
from src.processors.annotator_stats import AnnotatorStats
from src.processors.segmentation import (
    FinalSegment,
    QualityRiskFlag,
    VelocitySegment,
    classify_annotator,
    classify_quality_risk,
    classify_velocity,
)


class TestSegmentation(unittest.TestCase):
    def test_velocity_segmentation(self) -> None:
        self.assertEqual(classify_velocity(AnnotatorStats(annotator_id="u", full_name="U", avg_frames_per_hour=80.0)), VelocitySegment.SUPER_FAST)
        self.assertEqual(classify_velocity(AnnotatorStats(annotator_id="u", full_name="U", avg_frames_per_hour=50.0)), VelocitySegment.ON_TARGET)
        self.assertEqual(classify_velocity(AnnotatorStats(annotator_id="u", full_name="U", avg_frames_per_hour=30.0)), VelocitySegment.AVERAGE)
        self.assertEqual(classify_velocity(AnnotatorStats(annotator_id="u", full_name="U", avg_frames_per_hour=15.0)), VelocitySegment.SLOW)
        self.assertEqual(classify_velocity(AnnotatorStats(annotator_id="u", full_name="U", avg_frames_per_hour=None)), VelocitySegment.SLOW)

    def test_quality_risk_flag(self) -> None:
        # Rejection rate cao (>= 0.20) -> HIGH_RISK
        self.assertEqual(
            classify_quality_risk(AnnotatorStats(annotator_id="u", full_name="U", first_time_pass_rate=0.9, rejection_rate=0.25, mean_f1_score=0.9)),
            QualityRiskFlag.HIGH_RISK,
        )
        # First-time pass rate thấp (< 0.80) -> HIGH_RISK
        self.assertEqual(
            classify_quality_risk(AnnotatorStats(annotator_id="u", full_name="U", first_time_pass_rate=0.75, rejection_rate=0.10, mean_f1_score=0.9)),
            QualityRiskFlag.HIGH_RISK,
        )
        # F1 thấp (< 0.85) -> HIGH_RISK
        self.assertEqual(
            classify_quality_risk(AnnotatorStats(annotator_id="u", full_name="U", first_time_pass_rate=0.85, rejection_rate=0.10, mean_f1_score=0.70)),
            QualityRiskFlag.HIGH_RISK,
        )
        # Đạt chuẩn
        self.assertEqual(
            classify_quality_risk(AnnotatorStats(annotator_id="u", full_name="U", first_time_pass_rate=0.85, rejection_rate=0.10, mean_f1_score=0.90)),
            QualityRiskFlag.ACCEPTABLE,
        )

    def test_final_segments(self) -> None:
        # 1. FAST_AND_FAULTY
        s1 = AnnotatorStats(
            annotator_id="u1", full_name="U1", avg_frames_per_hour=80.0,
            first_time_pass_rate=0.5, rejection_rate=0.3, active_hours_7d=10.0,
        )
        self.assertEqual(classify_annotator(s1).final_segment, FinalSegment.FAST_AND_FAULTY)

        # 2. NEEDS_RETRAINING
        s2 = AnnotatorStats(
            annotator_id="u2", full_name="U2", avg_frames_per_hour=15.0,
            first_time_pass_rate=0.5, rejection_rate=0.3, active_hours_7d=10.0,
        )
        self.assertEqual(classify_annotator(s2).final_segment, FinalSegment.NEEDS_RETRAINING)

        # 3. SLOW_BUT_STEADY
        s3 = AnnotatorStats(
            annotator_id="u3", full_name="U3", avg_frames_per_hour=15.0,
            first_time_pass_rate=0.9, rejection_rate=0.05, active_hours_7d=10.0,
        )
        self.assertEqual(classify_annotator(s3).final_segment, FinalSegment.SLOW_BUT_STEADY)

        # 4. STAR_ANNOTATOR
        s4 = AnnotatorStats(
            annotator_id="u4", full_name="U4", avg_frames_per_hour=55.0,
            first_time_pass_rate=0.95, rejection_rate=0.02, active_hours_7d=10.0,
        )
        self.assertEqual(classify_annotator(s4).final_segment, FinalSegment.STAR_ANNOTATOR)

        # 5. ONBOARDING (tenure <= 14 và jobs <= 10)
        s5 = AnnotatorStats(
            annotator_id="u5", full_name="U5", tenure_days=10, total_jobs_completed=5,
            avg_frames_per_hour=35.0, first_time_pass_rate=0.85, rejection_rate=0.1,
            active_hours_7d=5.0,
        )
        self.assertEqual(classify_annotator(s5).final_segment, FinalSegment.ONBOARDING)

        # 6. INACTIVE (active_hours_7d == 0)
        s6 = AnnotatorStats(
            annotator_id="u6", full_name="U6", tenure_days=50, total_jobs_completed=20,
            avg_frames_per_hour=35.0, first_time_pass_rate=0.85, rejection_rate=0.1,
            active_hours_7d=0.0,
        )
        self.assertEqual(classify_annotator(s6).final_segment, FinalSegment.INACTIVE)

        # 7. CORE_PERFORMER
        s7 = AnnotatorStats(
            annotator_id="u7", full_name="U7", tenure_days=50, total_jobs_completed=20,
            avg_frames_per_hour=35.0, first_time_pass_rate=0.85, rejection_rate=0.1,
            active_hours_7d=10.0,
        )
        self.assertEqual(classify_annotator(s7).final_segment, FinalSegment.CORE_PERFORMER)

    def test_segment_properties(self) -> None:
        self.assertEqual(FinalSegment.FAST_AND_FAULTY.priority, 1)
        self.assertEqual(FinalSegment.CORE_PERFORMER.priority, 7)
        self.assertIn("Nguy cơ gán ẩu", FinalSegment.FAST_AND_FAULTY.short_label)
        self.assertTrue(len(FinalSegment.STAR_ANNOTATOR.action) > 0)


if __name__ == "__main__":
    unittest.main()
