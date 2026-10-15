"""Unit tests cho module annotator_stats (WBS 2.4)."""
from __future__ import annotations

import unittest
from datetime import date
from src.processors.annotator_stats import build_annotator_stats
from src.processors.models import Annotator, GroundTruthEval, Job, Review


class TestAnnotatorStats(unittest.TestCase):
    def test_build_annotator_stats(self) -> None:
        annotators = [
            Annotator(annotator_id="u1", full_name="User One", joined_date=date(2026, 9, 1)),
            Annotator(annotator_id="u2", full_name="User Two", joined_date=date(2026, 10, 1)),
        ]
        jobs = [
            Job(
                job_id=1,
                task_id=10,
                annotator_id="u1",
                status="completed",
                total_frames=100,
                total_objects=200,
                active_time_hours=2.0,
                date_key=date(2026, 10, 8),
            ),
            Job(
                job_id=2,
                task_id=10,
                annotator_id="u1",
                status="in_progress",
                total_frames=50,
                total_objects=50,
                active_time_hours=1.0,
                date_key=date(2026, 10, 9),
            ),
            Job(
                job_id=3,
                task_id=10,
                annotator_id="u2",
                status="completed",
                total_frames=80,
                total_objects=120,
                active_time_hours=4.0,
                date_key=date(2026, 10, 5),
            ),
        ]
        reviews = [
            Review(review_id="r1", job_id=1, reviewer_id="rev1", review_iteration=1, review_decision="Accepted"),
            Review(review_id="r2", job_id=3, reviewer_id="rev1", review_iteration=1, review_decision="Rejected"),
            Review(review_id="r3", job_id=3, reviewer_id="rev1", review_iteration=2, review_decision="Accepted"),
        ]
        gt_evals = [
            GroundTruthEval(eval_id="e1", job_id=1, f1_score=0.95),
            GroundTruthEval(eval_id="e2", job_id=3, f1_score=0.75),
        ]

        as_of = date(2026, 10, 9)
        stats = build_annotator_stats(annotators, jobs, reviews, gt_evals, as_of=as_of)

        self.assertEqual(len(stats), 2)

        # Kiểm tra u1
        s1 = next(s for s in stats if s.annotator_id == "u1")
        self.assertEqual(s1.total_jobs_completed, 1)
        self.assertEqual(s1.total_frames_completed, 100)
        self.assertEqual(s1.total_objects, 250)
        self.assertAlmostEqual(s1.total_active_hours, 3.0)
        # avg_frames_per_hour = 100 / 3.0
        self.assertAlmostEqual(s1.avg_frames_per_hour, 100 / 3.0)
        # tenure: 2026-09-01 -> 2026-10-09 = 38 days
        self.assertEqual(s1.tenure_days, 38)
        # active_hours_7d (cutoff: 10-03 to 10-09): cả job 1 (10-08, 2h) và job 2 (10-09, 1h) -> 3.0
        self.assertAlmostEqual(s1.active_hours_7d, 3.0)
        self.assertAlmostEqual(s1.first_time_pass_rate, 1.0)
        self.assertAlmostEqual(s1.rejection_rate, 0.0)
        self.assertAlmostEqual(s1.mean_f1_score, 0.95)

        # Kiểm tra u2
        s2 = next(s for s in stats if s.annotator_id == "u2")
        self.assertEqual(s2.total_jobs_completed, 1)
        self.assertEqual(s2.total_frames_completed, 80)
        self.assertAlmostEqual(s2.total_active_hours, 4.0)
        self.assertAlmostEqual(s2.avg_frames_per_hour, 20.0)
        self.assertEqual(s2.tenure_days, 8)
        self.assertAlmostEqual(s2.first_time_pass_rate, 0.0)
        self.assertAlmostEqual(s2.rejection_rate, 0.5)
        self.assertAlmostEqual(s2.mean_f1_score, 0.75)


if __name__ == "__main__":
    unittest.main()
