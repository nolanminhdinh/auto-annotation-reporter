"""Unit tests cho module quality (WBS 2.2)."""
from __future__ import annotations

import unittest
from src.processors.models import Defect, GroundTruthEval, Review
from src.processors.quality import (
    avg_defects_per_job,
    avg_f1,
    avg_miou,
    defect_density_per_100_frames,
    defect_type_counts,
    f1_from_precision_recall,
    first_time_pass_rate,
    normalize_defect_type,
    rejection_rate,
    total_defects,
)


class TestQuality(unittest.TestCase):
    def test_first_time_pass_rate(self) -> None:
        reviews = [
            Review(review_id="r1", job_id=101, reviewer_id="rev1", review_iteration=1, review_decision="Accepted"),
            Review(review_id="r2", job_id=102, reviewer_id="rev1", review_iteration=1, review_decision="Rejected"),
            Review(review_id="r3", job_id=102, reviewer_id="rev1", review_iteration=2, review_decision="Accepted"),
        ]
        # Vòng 1 có 2 lượt: 1 Accepted, 1 Rejected -> 1/2 = 0.5
        self.assertAlmostEqual(first_time_pass_rate(reviews), 0.5)

    def test_rejection_rate(self) -> None:
        reviews = [
            Review(review_id="r1", job_id=101, reviewer_id="rev1", review_iteration=1, review_decision="Accepted"),
            Review(review_id="r2", job_id=102, reviewer_id="rev1", review_iteration=1, review_decision="Rejected"),
            Review(review_id="r3", job_id=102, reviewer_id="rev1", review_iteration=2, review_decision="Rejected"),
        ]
        # Tổng 3 review, 2 Rejected -> 2/3
        self.assertAlmostEqual(rejection_rate(reviews), 2 / 3)

    def test_normalize_defect_type(self) -> None:
        self.assertEqual(normalize_defect_type("BOX_LOOSE"), "box_displacement")
        self.assertEqual(normalize_defect_type("BOX_TIGHT_CLIPPED"), "box_displacement")
        self.assertEqual(normalize_defect_type("MISLABELED"), "wrong_class")
        self.assertEqual(normalize_defect_type("MISSED_OBJECT"), "missing_object")
        self.assertEqual(normalize_defect_type("ATTRIBUTE_ERROR"), "wrong_attr")
        self.assertEqual(normalize_defect_type("UNKNOWN_DEFECT"), "unclassified")

    def test_defect_type_counts(self) -> None:
        defects = [
            Defect(defect_id="d1", review_id="r1", frame_idx=0, label_id=1, defect_type="BOX_LOOSE"),
            Defect(defect_id="d2", review_id="r1", frame_idx=1, label_id=1, defect_type="MISLABELED"),
            Defect(defect_id="d3", review_id="r2", frame_idx=0, label_id=2, defect_type="RANDOM_ERR"),
        ]
        self.assertEqual(total_defects(defects), 3)
        counts = defect_type_counts(defects)
        self.assertEqual(counts["box_displacement"], 1)
        self.assertEqual(counts["wrong_class"], 1)
        self.assertEqual(counts["missing_object"], 0)
        self.assertEqual(counts["wrong_attr"], 0)
        self.assertEqual(counts["unclassified"], 1)

    def test_defect_density(self) -> None:
        self.assertAlmostEqual(defect_density_per_100_frames(5, 500), 1.0)
        self.assertIsNone(defect_density_per_100_frames(5, 0))

    def test_avg_defects_per_job(self) -> None:
        reviews = [
            Review(review_id="r1", job_id=101, reviewer_id="rev1", review_iteration=1, review_decision="Accepted"),
            Review(review_id="r2", job_id=101, reviewer_id="rev1", review_iteration=2, review_decision="Accepted"),
            Review(review_id="r3", job_id=102, reviewer_id="rev1", review_iteration=1, review_decision="Accepted"),
        ]
        # 2 jobs khác nhau (101, 102), 4 defects -> 4 / 2 = 2.0
        self.assertAlmostEqual(avg_defects_per_job(4, reviews), 2.0)

    def test_ground_truth_metrics(self) -> None:
        gt = [
            GroundTruthEval(eval_id="e1", job_id=101, mean_iou=0.85, f1_score=0.9),
            GroundTruthEval(eval_id="e2", job_id=102, mean_iou=0.75, precision=0.8, recall=0.8),
        ]
        self.assertAlmostEqual(avg_miou(gt), 0.8)
        self.assertAlmostEqual(avg_f1(gt), 0.85)

        self.assertAlmostEqual(f1_from_precision_recall(0.8, 0.8), 0.8)
        self.assertIsNone(f1_from_precision_recall(None, 0.8))


if __name__ == "__main__":
    unittest.main()
