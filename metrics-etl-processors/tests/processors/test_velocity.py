"""Unit tests cho module velocity (WBS 2.1)."""
from __future__ import annotations

import unittest
from datetime import date, datetime, timedelta, timezone
from src.processors.models import Job
from src.processors.velocity import (
    active_seconds_from_events,
    avg_time_per_frame_minutes,
    avg_time_per_object_seconds,
    backlog_frames,
    completed_frames_per_day,
    progress_ratio,
    projected_completion_date,
    total_active_hours,
    total_completed_frames,
    total_objects_created,
    velocity_frames_per_hour,
    velocity_objects_per_hour,
)


class TestVelocity(unittest.TestCase):
    def setUp(self) -> None:
        self.jobs = [
            Job(
                job_id=1,
                task_id=10,
                annotator_id="u1",
                status="completed",
                total_frames=100,
                total_objects=250,
                active_time_hours=2.0,
                date_key=date(2026, 10, 5),
            ),
            Job(
                job_id=2,
                task_id=10,
                annotator_id="u1",
                status="in_progress",
                total_frames=100,
                total_objects=50,
                active_time_hours=1.0,
                date_key=date(2026, 10, 6),
            ),
        ]

    def test_aggregates(self) -> None:
        self.assertEqual(total_completed_frames(self.jobs), 100)
        self.assertEqual(total_objects_created(self.jobs), 300)
        self.assertAlmostEqual(total_active_hours(self.jobs), 3.0)

    def test_velocity_frames_per_hour(self) -> None:
        # basis="all": 100 / 3.0 = 33.3333
        self.assertAlmostEqual(velocity_frames_per_hour(self.jobs, hours_basis="all"), 100 / 3.0)
        # basis="completed": 100 / 2.0 = 50.0
        self.assertAlmostEqual(velocity_frames_per_hour(self.jobs, hours_basis="completed"), 50.0)

    def test_velocity_objects_per_hour(self) -> None:
        # 300 objects / 3.0 hours = 100.0
        self.assertAlmostEqual(velocity_objects_per_hour(self.jobs), 100.0)

    def test_avg_time_per_frame_minutes(self) -> None:
        # 3.0 hours * 60 / 100 frames = 1.8 mins/frame
        self.assertAlmostEqual(avg_time_per_frame_minutes(self.jobs), 1.8)

    def test_avg_time_per_object_seconds(self) -> None:
        # 3.0 hours * 3600 / 300 objects = 36.0 secs/object
        self.assertAlmostEqual(avg_time_per_object_seconds(self.jobs), 36.0)

    def test_progress_and_backlog(self) -> None:
        self.assertAlmostEqual(progress_ratio(100, 500), 0.2)
        self.assertEqual(backlog_frames(100, 500), 400)
        self.assertEqual(backlog_frames(600, 500), 0)

    def test_completed_frames_per_day_and_eta(self) -> None:
        as_of = date(2026, 10, 9)
        # window 7 days: job 1 (date 2026-10-05) falls inside (10-03 to 10-09)
        # completed frames = 100 / 7 days
        per_day = completed_frames_per_day(self.jobs, as_of=as_of, window_days=7)
        self.assertAlmostEqual(per_day, 100 / 7)

        # ETA: backlog 400, per_day = 100/7 (~14.28) -> 28 days -> 2026-10-09 + 28 days = 2026-11-06
        eta = projected_completion_date(400, per_day, as_of)
        self.assertEqual(eta, as_of + timedelta(days=28))

    def test_active_seconds_from_events(self) -> None:
        base = datetime(2026, 10, 1, 10, 0, 0, tzinfo=timezone.utc)
        events = [
            base,
            base + timedelta(seconds=60),   # delta 60s <= 300s -> +60s
            base + timedelta(seconds=120),  # delta 60s <= 300s -> +60s
            base + timedelta(seconds=1000), # delta 880s > 300s -> idle, +0s
            base + timedelta(seconds=1030), # delta 30s <= 300s -> +30s
        ]
        self.assertEqual(active_seconds_from_events(events, idle_gap_seconds=300), 150.0)


if __name__ == "__main__":
    unittest.main()
