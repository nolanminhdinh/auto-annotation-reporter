"""Test adapter bằng snapshot giả lập (cấu trúc theo snapshot thật, số liệu bịa)."""

import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from src.adapters.cvat_snapshot import load_snapshot
from src.adapters.snapshot_metrics import main as cli_main
from src.adapters.snapshot_metrics import summarize

AS_OF = date(2026, 10, 9)


def rect(frame, x1, y1, x2, y2, outside=False):
    return {"id": frame, "type": "rectangle", "frame": frame, "outside": outside,
            "points": [x1, y1, x2, y2], "occluded": False, "rotation": 0.0}


def make_cvat(jobs, annotations, size=100):
    return {"task": {"id": 7, "name": "demo", "size": size}, "jobs": jobs, "labels": [],
            "issues": [], "comments": [], "annotations": annotations}


def job(job_id, status, frames, assignee=None, updated="2026-10-08T10:00:00Z"):
    return {"id": job_id, "task_id": 7, "type": "annotation", "status": status, "stage": "annotation",
            "state": "in progress", "frame_count": frames, "assignee": assignee, "updated_date": updated}


class SnapshotCase(unittest.TestCase):
    def write(self, cvat, manifest=None):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        folder = Path(tmp.name)
        (folder / "cvat.json").write_text(json.dumps(cvat), encoding="utf-8")
        if manifest:
            (folder / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        return folder


class LoadSnapshotTests(SnapshotCase):
    def test_tracks_only_outside_markers_are_not_drawn_objects(self):
        track = {"id": 1, "label_id": 1, "shapes": [
            rect(0, 0, 0, 10, 10),
            rect(5, 0, 0, 20, 20),
            rect(9, 0, 0, 20, 20, outside=True),      # mốc biến mất, không phải hộp được vẽ
        ]}
        cvat = make_cvat([job(1, "annotation", 10)],
                         [{"job_id": 1, "status": "success",
                           "data": {"shapes": [], "tracks": [track], "tags": []}}])
        snap = load_snapshot(self.write(cvat))
        self.assertEqual(snap.counts["track_keyframe_records"], 3)
        self.assertEqual(snap.counts["outside_markers"], 1)
        self.assertEqual(snap.counts["drawn_objects"], 2)
        self.assertEqual(len(snap.geometries), 2)
        self.assertEqual(snap.jobs[0].total_objects, 2)
        self.assertEqual([g.area_pixels for g in snap.geometries], [100.0, 400.0])

    def test_single_shapes_and_tracks_are_both_counted(self):
        data = {"shapes": [rect(1, 0, 0, 5, 5)],
                "tracks": [{"id": 1, "shapes": [rect(0, 0, 0, 2, 2)]}], "tags": [{"id": 9}]}
        cvat = make_cvat([job(1, "annotation", 10)], [{"job_id": 1, "status": "success", "data": data}])
        snap = load_snapshot(self.write(cvat))
        self.assertEqual(snap.counts["drawn_objects"], 2)
        self.assertEqual(snap.counts["tags"], 1)

    def test_job_mapping_uses_cvat_status_and_assignee(self):
        person = {"id": 42, "username": "u", "first_name": "An", "last_name": "Nguyen"}
        cvat = make_cvat([job(1, "completed", 50, assignee=person)], [])
        snap = load_snapshot(self.write(cvat))
        j = snap.jobs[0]
        self.assertEqual((j.status, j.total_frames, j.annotator_id), ("completed", 50, "42"))
        self.assertEqual(j.date_key, date(2026, 10, 8))
        self.assertEqual(snap.annotators[0].full_name, "An Nguyen")
        self.assertEqual(j.active_time_hours, 0.0)

    def test_date_key_only_for_completed_jobs(self):
        snap = load_snapshot(self.write(make_cvat([job(1, "annotation", 5)], [])))
        self.assertIsNone(snap.jobs[0].date_key)

    def test_unassigned_job_has_no_annotator(self):
        snap = load_snapshot(self.write(make_cvat([job(1, "annotation", 5)], [])))
        self.assertIsNone(snap.jobs[0].annotator_id)
        self.assertEqual(snap.annotators, [])

    def test_failed_annotation_job_is_reported_not_hidden(self):
        cvat = make_cvat([job(1, "annotation", 5)], [{"job_id": 1, "status": "failed", "error_type": "X"}])
        with self.assertLogs("src.adapters.cvat_snapshot", level="WARNING"):
            snap = load_snapshot(self.write(cvat))
        self.assertEqual(snap.failed_annotation_jobs, [1])

    def test_malformed_geometry_is_counted_and_logged(self):
        bad = {"id": 1, "type": "rectangle", "frame": 0, "outside": False, "points": [1, 2, 3]}
        cvat = make_cvat([job(1, "annotation", 5)],
                         [{"job_id": 1, "status": "success",
                           "data": {"shapes": [bad, rect(1, 0, 0, 4, 4)], "tracks": [], "tags": []}}])
        with self.assertLogs("src.adapters.cvat_snapshot", level="WARNING"):
            snap = load_snapshot(self.write(cvat))
        self.assertEqual(snap.malformed_records, 1)
        self.assertEqual(len(snap.geometries), 1)

    def test_frame_size_enables_frame_area_pct(self):
        cvat = make_cvat([job(1, "annotation", 5)],
                         [{"job_id": 1, "status": "success",
                           "data": {"shapes": [rect(0, 0, 0, 10, 10)], "tracks": [], "tags": []}}])
        folder = self.write(cvat)
        self.assertIsNone(load_snapshot(folder).geometries[0].frame_area_pct)
        self.assertAlmostEqual(load_snapshot(folder, (100, 100)).geometries[0].frame_area_pct, 1.0)


class SummarizeTests(SnapshotCase):
    def test_missing_sources_are_none_with_reason_never_zero(self):
        cvat = make_cvat([job(1, "annotation", 10)], [])
        result = summarize(load_snapshot(self.write(cvat)), AS_OF)
        for key in ("velocity_frames_per_hour", "first_time_pass_rate", "total_defects",
                    "defect_density_per_100_frames", "avg_f1", "segmentation", "projected_completion_date"):
            self.assertIn(key, result["not_computable"], key)
        self.assertIsNone(result["quality"]["total_defects"])
        self.assertIsNone(result["quality"]["defect_density_per_100_frames"])
        self.assertEqual(result["segmentation"], [])

    def test_progress_from_completed_jobs(self):
        cvat = make_cvat([job(1, "completed", 40), job(2, "annotation", 60)], [], size=100)
        progress = summarize(load_snapshot(self.write(cvat)), AS_OF)["progress"]
        self.assertEqual(progress["completed_frames"], 40)
        self.assertAlmostEqual(progress["progress_ratio"], 0.4)
        self.assertEqual(progress["backlog_frames"], 60)
        self.assertEqual(progress["jobs_by_status"], {"annotation": 1, "completed": 1})

    def test_eta_uses_recent_completed_frames(self):
        # 70 frame completed ngày 08/10 trong cửa sổ 7 ngày -> 10 frame/ngày; backlog 30 -> 3 ngày
        cvat = make_cvat([job(1, "completed", 70)], [], size=100)
        eta = summarize(load_snapshot(self.write(cvat)), AS_OF)["velocity"]["projected_completion_date"]
        self.assertEqual(eta, "2026-10-12")

    def test_geometry_summary(self):
        data = {"shapes": [rect(0, 0, 0, 10, 10), rect(1, 0, 0, 50, 50)], "tracks": [], "tags": []}
        cvat = make_cvat([job(1, "annotation", 5)], [{"job_id": 1, "status": "success", "data": data}])
        geo = summarize(load_snapshot(self.write(cvat)), AS_OF)["geometry"]
        self.assertEqual(geo["boxes_measured"], 2)
        self.assertAlmostEqual(geo["avg_object_area_pixels"], 1300.0)
        self.assertAlmostEqual(geo["pct_small_objects"], 0.5)
        self.assertEqual(geo["size_scale_counts"], {"Small": 1, "Medium": 1, "Large": 0, "Unmeasured": 0})

    def test_segmentation_runs_when_job_is_assigned(self):
        person = {"id": 1, "username": "u", "first_name": "A", "last_name": "B"}
        cvat = make_cvat([job(1, "completed", 40, assignee=person)], [])
        result = summarize(load_snapshot(self.write(cvat)), AS_OF)
        self.assertEqual(len(result["segmentation"]), 1)
        self.assertNotIn("segmentation", result["not_computable"])

    def test_cli_prints_json_and_defaults_as_of_from_manifest(self):
        folder = self.write(make_cvat([job(1, "annotation", 10)], []),
                            manifest={"started_at": "2026-10-09T09:45:49.598531+00:00"})
        import contextlib
        import io
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = cli_main([str(folder)])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(buffer.getvalue())["as_of"], "2026-10-09")


if __name__ == "__main__":
    unittest.main()
