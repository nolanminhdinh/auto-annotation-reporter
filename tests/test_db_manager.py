"""Unit tests for SQLite Medallion Data Warehouse (Bronze -> Silver -> Gold)."""
import csv
import tempfile
import unittest
from pathlib import Path
from src.storage.db_manager import (
    init_db,
    save_bronze_snapshot,
    upsert_silver_entities,
    load_gold_star_schema,
    export_gold_to_csv,
    get_audit_trail,
    get_connection,
)


class TestDbManager(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_warehouse.db"
        self.csv_out_dir = Path(self.temp_dir.name) / "csv_out"
        init_db(self.db_path)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_init_db_creates_medallion_tables(self) -> None:
        conn = get_connection(self.db_path)
        cur = conn.cursor()
        tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        conn.close()

        # 1. Check Bronze (Raw)
        self.assertIn("bronze_snapshots", tables)
        self.assertIn("bronze_cvat_raw", tables)
        self.assertIn("bronze_github_raw", tables)
        self.assertIn("bronze_team_reports_raw", tables)

        # 2. Check Silver (Cleansed Granular Entities)
        self.assertIn("silver_jobs", tables)
        self.assertIn("silver_annotations", tables)
        self.assertIn("silver_qa_reviews", tables)
        self.assertIn("silver_qa_defects", tables)
        self.assertIn("silver_github_issues", tables)

        # 3. Check Gold (Star Schema & Data Marts)
        self.assertIn("gold_dim_annotators", tables)
        self.assertIn("gold_dim_tasks_batches", tables)
        self.assertIn("gold_fact_job_sessions", tables)
        self.assertIn("gold_fact_annotations", tables)
        self.assertIn("gold_mart_batch_progress", tables)
        self.assertIn("gold_mart_qa_metrics", tables)
        self.assertIn("gold_mart_annotator_segments", tables)

    def test_medallion_full_flow_and_audit_trail(self) -> None:
        snapshot_id = "20261016_test_snap_001"

        # 1. BRONZE LAYER: Raw Ingestion (Append-only audit)
        save_bronze_snapshot(
            snapshot_id=snapshot_id,
            task_id=217,
            repo="org/repo",
            session_name="Sprint 2 Demo",
            run_mode="offline",
            started_at="2026-10-16T09:00:00Z",
            finished_at="2026-10-16T09:00:10Z",
            status="success",
            manifest={"version": 1, "task": 217},
            cvat_data={"task": {"id": 217, "name": "Task 217"}},
            github_data={"issues": [{"id": 1, "title": "Ca khó 1"}]},
            team_reports=[{"team": "Xe con", "text": "Khó khăn ở cam 02"}],
            db_path=self.db_path,
        )

        # 2. SILVER LAYER: Cleansed Granular Entities
        jobs = [{
            "job_id": 101, "task_id": 217, "assignee_id": 1, "status": "completed",
            "stage": "annotation", "state": "completed", "frame_count": 100,
            "active_time_hours": 2.5, "updated_date": "2026-10-15T10:00:00Z"
        }]
        annotations = [{
            "annotation_id": "ann_1", "job_id": 101, "label_id": 5, "label_name": "car",
            "shape_type": "rectangle", "frame_idx": 142, "area_pixels": 4500.0,
            "coco_scale": "Medium", "frame_area_pct": 2.5, "is_outside": False
        }]
        reviews = [{"review_id": "rev_1", "job_id": 101, "reviewer_id": 2, "iteration": 1, "status": "accepted", "reviewed_at": "2026-10-15"}]
        defects = [{"defect_id": "def_1", "job_id": 101, "review_id": "rev_1", "label_id": 5, "raw_type": "box_misaligned", "normalized_type": "box_displacement", "severity": "medium", "frame_idx": 142}]
        issues = [{"issue_number": 1, "title": "Ca khó cam 02", "extracted_frame_idx": 142, "referenced_job_id": 101, "referenced_task_id": 217, "link_status": "verified", "deep_link_url": "https://cvat.ai/jobs/101?frame=142", "labels": ["ca-kho"], "state": "open", "created_at": "2026-10-15"}]

        upsert_silver_entities(snapshot_id, jobs, annotations, reviews, defects, issues, db_path=self.db_path)

        # 3. GOLD LAYER: Star Schema (Dimensions & Facts) + Data Marts
        dimensions = {
            "dim_annotators": [{"annotator_id": 1, "username": "tuan", "full_name": "Tuan Pham", "role": "Annotator"}],
            "dim_tasks_batches": [{"task_id": 217, "task_name": "Batch 01", "batch_id": "B1", "total_frames_target": 1000}],
            "dim_jobs": [{"job_id": 101, "task_id": 217, "annotator_id": 1, "stage": "annotation", "state": "completed", "frame_count": 100}],
        }
        facts = {
            "fact_job_sessions": [{
                "job_id": 101, "task_id": 217, "annotator_id": 1, "status": "completed",
                "total_frames": 100, "completed_frames": 100, "total_objects": 250, "active_hours": 2.5,
                "velocity_fps": 40.0, "velocity_ops": 100.0, "avg_time_per_frame_mins": 1.5,
                "completion_date": "2026-10-15"
            }],
            "fact_edge_cases": [{
                "case_id": "case_1", "task_id": 217, "job_id": 101, "frame_idx": 142,
                "issue_number": 1, "title": "Ca khó cam 02", "status": "open",
                "label": "ca-kho", "cvat_url": "https://cvat.ai/jobs/101?frame=142", "resolution_status": "open"
            }]
        }
        marts = {
            "batch_progress": {"task_id": 217, "as_of": "2026-10-16", "total_frames_target": 1000, "avg_velocity_fps": 40.0},
            "qa_metrics": {"task_id": 217, "as_of": "2026-10-16", "first_time_pass_rate": 0.85, "qa_score": 92.5},
            "annotator_segments": [{"as_of": "2026-10-16", "annotator_id": 1, "full_name": "Tuan Pham", "final_segment": "STAR_ANNOTATOR"}]
        }

        load_gold_star_schema(snapshot_id, dimensions, facts, marts, db_path=self.db_path)

        # 4. TRUY VẾT LỊCH SỬ (AUDIT TRAIL): Truy vấn snapshot quá khứ
        audit = get_audit_trail(snapshot_id, db_path=self.db_path)
        self.assertEqual(audit["metadata"]["snapshot_id"], snapshot_id)
        self.assertTrue(audit["cvat_raw_present"])
        self.assertTrue(audit["github_raw_present"])
        self.assertTrue(audit["team_raw_present"])
        self.assertEqual(audit["gold_batch_progress"]["avg_velocity_fps"], 40.0)

        # 5. ĐẨY THẲNG RA CSV PHỤC VỤ POWER BI
        exported = export_gold_to_csv(self.csv_out_dir, snapshot_id=snapshot_id, db_path=self.db_path)
        self.assertIn("dim_annotators.csv", exported)
        self.assertIn("fact_job_sessions.csv", exported)
        self.assertIn("batch_progress.csv", exported)
        self.assertIn("annotator_segments.csv", exported)
        self.assertTrue(exported["batch_progress.csv"].exists())

        # Kiểm tra mã hóa chuẩn UTF-8 BOM cho Power BI / Windows Excel
        with open(exported["dim_annotators.csv"], "rb") as f:
            header_bytes = f.read(3)
            self.assertEqual(header_bytes, b"\xef\xbb\xbf")


if __name__ == "__main__":
    unittest.main()
