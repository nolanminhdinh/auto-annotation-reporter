"""Data Warehouse Manager (Chuẩn Medallion Architecture: Bronze -> Silver -> Gold).

Storage engine: SQLite (data/annotation_warehouse.db) - ACID, zero-ops, full audit trail.

1. TẦNG BRONZE (Raw Layer):
   - Tiếp nhận dữ liệu nguyên bản (raw JSON payloads) từ CVAT REST API, GitHub API, Team text.
   - Thao tác: Chỉ append, tuyệt đối không chỉnh sửa, lưu trữ toàn bộ lịch sử các đợt chạy.
   - Phục vụ: Bằng chứng kiểm toán (Audit Trail), khôi phục và đối soát khi có nghi ngờ sai lệch số liệu.

2. TẦNG SILVER (Cleansed & Enriched Layer):
   - Xử lý dữ liệu từ Bronze: làm sạch, ép kiểu, khử trùng lặp, xử lý null vs 0.
   - Làm giàu dữ liệu kỹ thuật: tính diện tích Shoelace, phân loại COCO scale (Small/Medium/Large),
     trích xuất Regex frame index, chuẩn hóa taxonomy 4 nhóm lỗi, đối soát liên kết task/job.
   - Dữ liệu ở mức thực thể chi tiết (Granular Entities), phục vụ Data Analyst / Data Scientist.

3. TẦNG GOLD (Curated / Business-Ready Layer):
   - Mô hình hóa theo chuẩn Star Schema (Bảng Chiều Dim và Bảng Sự Kiện Fact) và Data Marts.
   - Tối ưu hóa sẵn sàng kết nối trực tiếp với Power BI hoặc đẩy ra các file CSV chuẩn UTF-8 BOM.
   - Phục vụ: Ban lãnh đạo, Mentor, Dashboard Power BI.
"""
from __future__ import annotations

import csv
import json
import logging
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / "data" / "annotation_warehouse.db"
CSV_ENCODING = "utf-8-sig"  # UTF-8 BOM cho Power BI & Excel trên Windows


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Khởi tạo kết nối SQLite với cấu hình WAL mode và Foreign Keys."""
    target_path = db_path or DEFAULT_DB_PATH
    target_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(db_path: Optional[Path] = None) -> None:
    """Khởi tạo toàn bộ cấu trúc Schema 3 tầng Bronze -> Silver -> Gold."""
    conn = get_connection(db_path)
    cur = conn.cursor()

    # =========================================================================
    # 1. TẦNG BRONZE (RAW LAYER - Dữ liệu thô nguyên bản, append-only)
    # =========================================================================
    cur.execute("""
    CREATE TABLE IF NOT EXISTS bronze_snapshots (
        snapshot_id TEXT PRIMARY KEY,
        task_id INTEGER,
        repo TEXT,
        session_name TEXT,
        run_mode TEXT,
        started_at TEXT,
        finished_at TEXT,
        status TEXT,
        manifest_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS bronze_cvat_raw (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        snapshot_id TEXT NOT NULL,
        task_id INTEGER,
        raw_payload TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (snapshot_id) REFERENCES bronze_snapshots(snapshot_id) ON DELETE CASCADE
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS bronze_github_raw (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        snapshot_id TEXT NOT NULL,
        repo TEXT,
        raw_payload TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (snapshot_id) REFERENCES bronze_snapshots(snapshot_id) ON DELETE CASCADE
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS bronze_team_reports_raw (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        snapshot_id TEXT NOT NULL,
        raw_payload TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (snapshot_id) REFERENCES bronze_snapshots(snapshot_id) ON DELETE CASCADE
    );
    """)

    # =========================================================================
    # 2. TẦNG SILVER (CLEANSED & ENRICHED LAYER - Làm sạch, làm giàu thực thể)
    # =========================================================================
    cur.execute("""
    CREATE TABLE IF NOT EXISTS silver_jobs (
        snapshot_id TEXT NOT NULL,
        job_id INTEGER NOT NULL,
        task_id INTEGER,
        assignee_id INTEGER,
        status TEXT,
        stage TEXT,
        state TEXT,
        frame_count INTEGER,
        active_time_hours REAL,
        updated_date TEXT,
        is_completed INTEGER,
        PRIMARY KEY (snapshot_id, job_id)
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS silver_annotations (
        snapshot_id TEXT NOT NULL,
        annotation_id TEXT NOT NULL,
        job_id INTEGER,
        label_id INTEGER,
        label_name TEXT,
        shape_type TEXT,
        frame_idx INTEGER,
        area_pixels REAL,
        coco_scale TEXT,
        frame_area_pct REAL,
        is_outside INTEGER,
        PRIMARY KEY (snapshot_id, annotation_id)
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS silver_qa_reviews (
        snapshot_id TEXT NOT NULL,
        review_id TEXT NOT NULL,
        job_id INTEGER,
        reviewer_id INTEGER,
        iteration INTEGER,
        status TEXT,
        reviewed_at TEXT,
        PRIMARY KEY (snapshot_id, review_id)
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS silver_qa_defects (
        snapshot_id TEXT NOT NULL,
        defect_id TEXT NOT NULL,
        job_id INTEGER,
        review_id TEXT,
        label_id INTEGER,
        raw_type TEXT,
        normalized_type TEXT,
        severity TEXT,
        frame_idx INTEGER,
        PRIMARY KEY (snapshot_id, defect_id)
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS silver_github_issues (
        snapshot_id TEXT NOT NULL,
        issue_number INTEGER NOT NULL,
        title TEXT,
        extracted_frame_idx INTEGER,
        referenced_job_id INTEGER,
        referenced_task_id INTEGER,
        link_status TEXT,
        deep_link_url TEXT,
        labels_json TEXT,
        state TEXT,
        created_at TEXT,
        PRIMARY KEY (snapshot_id, issue_number)
    );
    """)

    # =========================================================================
    # 3. TẦNG GOLD (CURATED / BUSINESS-READY - Star Schema & Data Marts)
    # =========================================================================
    # 3.1. BẢNG CHIỀU (DIMENSIONS)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS gold_dim_annotators (
        annotator_id INTEGER PRIMARY KEY,
        username TEXT,
        full_name TEXT,
        role TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS gold_dim_reviewers (
        reviewer_id INTEGER PRIMARY KEY,
        username TEXT,
        full_name TEXT,
        role TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS gold_dim_tasks_batches (
        task_id INTEGER PRIMARY KEY,
        task_name TEXT,
        batch_id TEXT,
        total_frames_target INTEGER,
        created_date TEXT
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS gold_dim_classes_labels (
        label_id INTEGER,
        task_id INTEGER,
        label_name TEXT,
        color TEXT,
        type TEXT,
        PRIMARY KEY (label_id, task_id)
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS gold_dim_date (
        date_key TEXT PRIMARY KEY,
        full_date TEXT,
        day_of_week INTEGER,
        day_name TEXT,
        week_number INTEGER,
        month_number INTEGER,
        year INTEGER,
        is_weekend INTEGER
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS gold_dim_jobs (
        job_id INTEGER PRIMARY KEY,
        task_id INTEGER,
        annotator_id INTEGER,
        stage TEXT,
        state TEXT,
        frame_count INTEGER,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 3.2. BẢNG SỰ KIỆN (FACTS)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS gold_fact_job_sessions (
        snapshot_id TEXT NOT NULL,
        job_id INTEGER NOT NULL,
        task_id INTEGER,
        annotator_id INTEGER,
        status TEXT,
        total_frames INTEGER,
        completed_frames INTEGER,
        total_objects INTEGER,
        active_hours REAL,
        velocity_fps REAL,
        velocity_ops REAL,
        avg_time_per_frame_mins REAL,
        completion_date TEXT,
        PRIMARY KEY (snapshot_id, job_id)
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS gold_fact_annotations (
        snapshot_id TEXT NOT NULL,
        annotation_id TEXT NOT NULL,
        job_id INTEGER,
        label_id INTEGER,
        shape_type TEXT,
        frame_idx INTEGER,
        area_pixels REAL,
        coco_scale TEXT,
        frame_area_pct REAL,
        PRIMARY KEY (snapshot_id, annotation_id)
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS gold_fact_qa_reviews (
        snapshot_id TEXT NOT NULL,
        review_id TEXT NOT NULL,
        job_id INTEGER,
        reviewer_id INTEGER,
        review_iteration INTEGER,
        review_status TEXT,
        reviewed_at TEXT,
        PRIMARY KEY (snapshot_id, review_id)
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS gold_fact_qa_defects (
        snapshot_id TEXT NOT NULL,
        defect_id TEXT NOT NULL,
        job_id INTEGER,
        review_id TEXT,
        label_id INTEGER,
        defect_type TEXT,
        severity TEXT,
        frame_idx INTEGER,
        PRIMARY KEY (snapshot_id, defect_id)
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS gold_fact_ground_truth_eval (
        snapshot_id TEXT NOT NULL,
        eval_id TEXT NOT NULL,
        job_id INTEGER,
        miou_score REAL,
        f1_score REAL,
        precision REAL,
        recall REAL,
        evaluated_at TEXT,
        PRIMARY KEY (snapshot_id, eval_id)
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS gold_fact_edge_cases (
        snapshot_id TEXT NOT NULL,
        case_id TEXT NOT NULL,
        task_id INTEGER,
        job_id INTEGER,
        frame_idx INTEGER,
        issue_number INTEGER,
        title TEXT,
        status TEXT,
        label TEXT,
        cvat_url TEXT,
        resolution_status TEXT,
        PRIMARY KEY (snapshot_id, case_id)
    );
    """)

    # 3.3. DATA MARTS TỔNG HỢP (Aggregated KPIs)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS gold_mart_batch_progress (
        snapshot_id TEXT NOT NULL,
        as_of TEXT,
        task_id INTEGER,
        task_name TEXT,
        total_frames_target INTEGER,
        completed_frames_proxy INTEGER,
        backlog_frames INTEGER,
        progress_pct_proxy REAL,
        annotation_job_count INTEGER,
        completed_annotation_job_count INTEGER,
        completed_annotation_job_percent REAL,
        jobs_status_completed INTEGER,
        jobs_status_annotation INTEGER,
        jobs_status_validation INTEGER,
        jobs_status_other INTEGER,
        total_active_hours REAL,
        avg_velocity_fps REAL,
        avg_time_per_frame_minutes REAL,
        projected_completion_date TEXT,
        note TEXT,
        PRIMARY KEY (snapshot_id, task_id)
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS gold_mart_qa_metrics (
        snapshot_id TEXT NOT NULL,
        as_of TEXT,
        task_id INTEGER,
        total_reviews INTEGER,
        total_defects INTEGER,
        first_time_pass_rate REAL,
        rejection_rate REAL,
        defect_density_per_100_frames REAL,
        avg_defects_per_job REAL,
        defect_box_displacement INTEGER,
        defect_wrong_class INTEGER,
        defect_missing_object INTEGER,
        defect_wrong_attr INTEGER,
        avg_miou REAL,
        avg_f1 REAL,
        qa_score REAL,
        PRIMARY KEY (snapshot_id, task_id)
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS gold_mart_annotator_segments (
        snapshot_id TEXT NOT NULL,
        as_of TEXT,
        annotator_id INTEGER NOT NULL,
        full_name TEXT,
        tenure_days INTEGER,
        completed_frames INTEGER,
        completed_jobs INTEGER,
        total_objects INTEGER,
        active_hours_total REAL,
        velocity_fps REAL,
        velocity_segment TEXT,
        first_time_pass_rate REAL,
        rejection_rate REAL,
        quality_risk_flag TEXT,
        final_segment TEXT,
        action_recommendation TEXT,
        PRIMARY KEY (snapshot_id, annotator_id)
    );
    """)

    conn.commit()
    conn.close()
    logger.info(f"Initialized Medallion Warehouse database schema at {db_path or DEFAULT_DB_PATH}")


# =============================================================================
# HÀM XỬ LÝ CHO TỪNG TẦNG
# =============================================================================

def save_bronze_snapshot(
    snapshot_id: str,
    task_id: int,
    repo: str,
    session_name: str,
    run_mode: str,
    started_at: str,
    finished_at: str,
    status: str,
    manifest: Dict[str, Any],
    cvat_data: Optional[Dict[str, Any]] = None,
    github_data: Optional[Dict[str, Any]] = None,
    team_reports: Optional[Any] = None,
    db_path: Optional[Path] = None,
) -> None:
    """TẦNG BRONZE: Lưu trữ nguyên bản raw JSON payloads (append-only) phục vụ kiểm toán."""
    conn = get_connection(db_path)
    cur = conn.cursor()

    cur.execute("""
    INSERT OR REPLACE INTO bronze_snapshots (
        snapshot_id, task_id, repo, session_name, run_mode, started_at, finished_at, status, manifest_json
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        snapshot_id,
        task_id,
        repo,
        session_name,
        run_mode,
        started_at,
        finished_at,
        status,
        json.dumps(manifest, ensure_ascii=False) if manifest else None,
    ))

    if cvat_data:
        cur.execute("""
        INSERT INTO bronze_cvat_raw (snapshot_id, task_id, raw_payload)
        VALUES (?, ?, ?)
        """, (snapshot_id, task_id, json.dumps(cvat_data, ensure_ascii=False)))

    if github_data:
        cur.execute("""
        INSERT INTO bronze_github_raw (snapshot_id, repo, raw_payload)
        VALUES (?, ?, ?)
        """, (snapshot_id, repo, json.dumps(github_data, ensure_ascii=False)))

    if team_reports:
        cur.execute("""
        INSERT INTO bronze_team_reports_raw (snapshot_id, raw_payload)
        VALUES (?, ?)
        """, (snapshot_id, json.dumps(team_reports, ensure_ascii=False)))

    conn.commit()
    conn.close()
    logger.info(f"[Bronze] Snapshot '{snapshot_id}' stored with complete raw audit trail.")


def upsert_silver_entities(
    snapshot_id: str,
    jobs: List[Dict[str, Any]],
    annotations: List[Dict[str, Any]],
    qa_reviews: List[Dict[str, Any]],
    qa_defects: List[Dict[str, Any]],
    github_issues: List[Dict[str, Any]],
    db_path: Optional[Path] = None,
) -> None:
    """TẦNG SILVER: Lưu trữ dữ liệu thực thể đã làm sạch và làm giàu kỹ thuật."""
    conn = get_connection(db_path)
    cur = conn.cursor()

    for j in jobs:
        cur.execute("""
        INSERT OR REPLACE INTO silver_jobs (
            snapshot_id, job_id, task_id, assignee_id, status, stage, state, frame_count, active_time_hours, updated_date, is_completed
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            snapshot_id, j.get("job_id"), j.get("task_id"), j.get("assignee_id"),
            j.get("status"), j.get("stage"), j.get("state"), j.get("frame_count"),
            j.get("active_time_hours"), j.get("updated_date"),
            1 if j.get("status") == "completed" else 0
        ))

    for a in annotations:
        cur.execute("""
        INSERT OR REPLACE INTO silver_annotations (
            snapshot_id, annotation_id, job_id, label_id, label_name, shape_type, frame_idx, area_pixels, coco_scale, frame_area_pct, is_outside
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            snapshot_id, str(a.get("annotation_id")), a.get("job_id"), a.get("label_id"),
            a.get("label_name"), a.get("shape_type"), a.get("frame_idx"),
            a.get("area_pixels"), a.get("coco_scale"), a.get("frame_area_pct"),
            1 if a.get("is_outside") else 0
        ))

    for r in qa_reviews:
        cur.execute("""
        INSERT OR REPLACE INTO silver_qa_reviews (
            snapshot_id, review_id, job_id, reviewer_id, iteration, status, reviewed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            snapshot_id, str(r.get("review_id")), r.get("job_id"), r.get("reviewer_id"),
            r.get("iteration"), r.get("status"), r.get("reviewed_at")
        ))

    for d in qa_defects:
        cur.execute("""
        INSERT OR REPLACE INTO silver_qa_defects (
            snapshot_id, defect_id, job_id, review_id, label_id, raw_type, normalized_type, severity, frame_idx
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            snapshot_id, str(d.get("defect_id")), d.get("job_id"), str(d.get("review_id")),
            d.get("label_id"), d.get("raw_type"), d.get("normalized_type"),
            d.get("severity"), d.get("frame_idx")
        ))

    for i in github_issues:
        cur.execute("""
        INSERT OR REPLACE INTO silver_github_issues (
            snapshot_id, issue_number, title, extracted_frame_idx, referenced_job_id, referenced_task_id, link_status, deep_link_url, labels_json, state, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            snapshot_id, i.get("issue_number"), i.get("title"), i.get("extracted_frame_idx"),
            i.get("referenced_job_id"), i.get("referenced_task_id"), i.get("link_status"),
            i.get("deep_link_url"), json.dumps(i.get("labels", [])), i.get("state"), i.get("created_at")
        ))

    conn.commit()
    conn.close()
    logger.info(f"[Silver] Cleaned & enriched entities stored for snapshot '{snapshot_id}'.")


def load_gold_star_schema(
    snapshot_id: str,
    dimensions: Dict[str, List[Dict[str, Any]]],
    facts: Dict[str, List[Dict[str, Any]]],
    marts: Optional[Dict[str, Any]] = None,
    db_path: Optional[Path] = None,
) -> None:
    """TẦNG GOLD: Nạp Mô hình hình sao (Star Schema) và Data Marts sẵn sàng cho Power BI."""
    conn = get_connection(db_path)
    cur = conn.cursor()

    # 1. Dimensions
    if "dim_annotators" in dimensions:
        for r in dimensions["dim_annotators"]:
            cur.execute("""
            INSERT OR REPLACE INTO gold_dim_annotators (annotator_id, username, full_name, role)
            VALUES (?, ?, ?, ?)
            """, (r.get("annotator_id"), r.get("username"), r.get("full_name"), r.get("role")))

    if "dim_reviewers" in dimensions:
        for r in dimensions["dim_reviewers"]:
            cur.execute("""
            INSERT OR REPLACE INTO gold_dim_reviewers (reviewer_id, username, full_name, role)
            VALUES (?, ?, ?, ?)
            """, (r.get("reviewer_id"), r.get("username"), r.get("full_name"), r.get("role")))

    if "dim_tasks_batches" in dimensions:
        for r in dimensions["dim_tasks_batches"]:
            cur.execute("""
            INSERT OR REPLACE INTO gold_dim_tasks_batches (task_id, task_name, batch_id, total_frames_target, created_date)
            VALUES (?, ?, ?, ?, ?)
            """, (r.get("task_id"), r.get("task_name"), r.get("batch_id"), r.get("total_frames_target"), r.get("created_date")))

    if "dim_classes_labels" in dimensions:
        for r in dimensions["dim_classes_labels"]:
            cur.execute("""
            INSERT OR REPLACE INTO gold_dim_classes_labels (label_id, task_id, label_name, color, type)
            VALUES (?, ?, ?, ?, ?)
            """, (r.get("label_id"), r.get("task_id"), r.get("label_name"), r.get("color"), r.get("type")))

    if "dim_date" in dimensions:
        for r in dimensions["dim_date"]:
            cur.execute("""
            INSERT OR REPLACE INTO gold_dim_date (date_key, full_date, day_of_week, day_name, week_number, month_number, year, is_weekend)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                r.get("date_key"), r.get("full_date"), r.get("day_of_week"), r.get("day_name"),
                r.get("week_number"), r.get("month_number"), r.get("year"), r.get("is_weekend")
            ))

    if "dim_jobs" in dimensions:
        for r in dimensions["dim_jobs"]:
            cur.execute("""
            INSERT OR REPLACE INTO gold_dim_jobs (job_id, task_id, annotator_id, stage, state, frame_count)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (r.get("job_id"), r.get("task_id"), r.get("annotator_id"), r.get("stage"), r.get("state"), r.get("frame_count")))

    # 2. Facts
    if "fact_job_sessions" in facts:
        for r in facts["fact_job_sessions"]:
            cur.execute("""
            INSERT OR REPLACE INTO gold_fact_job_sessions (
                snapshot_id, job_id, task_id, annotator_id, status, total_frames, completed_frames,
                total_objects, active_hours, velocity_fps, velocity_ops, avg_time_per_frame_mins, completion_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                snapshot_id, r.get("job_id"), r.get("task_id"), r.get("annotator_id"), r.get("status"),
                r.get("total_frames"), r.get("completed_frames"), r.get("total_objects"), r.get("active_hours"),
                r.get("velocity_fps"), r.get("velocity_ops"), r.get("avg_time_per_frame_mins"), r.get("completion_date")
            ))

    if "fact_annotations" in facts:
        for r in facts["fact_annotations"]:
            cur.execute("""
            INSERT OR REPLACE INTO gold_fact_annotations (
                snapshot_id, annotation_id, job_id, label_id, shape_type, frame_idx, area_pixels, coco_scale, frame_area_pct
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                snapshot_id, str(a_id := r.get("annotation_id")), r.get("job_id"), r.get("label_id"),
                r.get("shape_type"), r.get("frame_idx"), r.get("area_pixels"), r.get("coco_scale"), r.get("frame_area_pct")
            ))

    if "fact_qa_reviews" in facts:
        for r in facts["fact_qa_reviews"]:
            cur.execute("""
            INSERT OR REPLACE INTO gold_fact_qa_reviews (
                snapshot_id, review_id, job_id, reviewer_id, review_iteration, review_status, reviewed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                snapshot_id, str(r.get("review_id")), r.get("job_id"), r.get("reviewer_id"),
                r.get("review_iteration"), r.get("review_status"), r.get("reviewed_at")
            ))

    if "fact_qa_defects" in facts:
        for r in facts["fact_qa_defects"]:
            cur.execute("""
            INSERT OR REPLACE INTO gold_fact_qa_defects (
                snapshot_id, defect_id, job_id, review_id, label_id, defect_type, severity, frame_idx
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                snapshot_id, str(r.get("defect_id")), r.get("job_id"), str(r.get("review_id")),
                r.get("label_id"), r.get("defect_type"), r.get("severity"), r.get("frame_idx")
            ))

    if "fact_ground_truth_eval" in facts:
        for r in facts["fact_ground_truth_eval"]:
            cur.execute("""
            INSERT OR REPLACE INTO gold_fact_ground_truth_eval (
                snapshot_id, eval_id, job_id, miou_score, f1_score, precision, recall, evaluated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                snapshot_id, str(r.get("eval_id")), r.get("job_id"), r.get("miou_score"),
                r.get("f1_score"), r.get("precision"), r.get("recall"), r.get("evaluated_at")
            ))

    if "fact_edge_cases" in facts:
        for r in facts["fact_edge_cases"]:
            cur.execute("""
            INSERT OR REPLACE INTO gold_fact_edge_cases (
                snapshot_id, case_id, task_id, job_id, frame_idx, issue_number, title, status, label, cvat_url, resolution_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                snapshot_id, str(r.get("case_id")), r.get("task_id"), r.get("job_id"),
                r.get("frame_idx"), r.get("issue_number"), r.get("title"), r.get("status"),
                r.get("label"), r.get("cvat_url"), r.get("resolution_status")
            ))

    # 3. Data Marts (Pre-aggregated)
    if marts:
        bp = marts.get("batch_progress")
        if bp:
            cur.execute("""
            INSERT OR REPLACE INTO gold_mart_batch_progress (
                snapshot_id, as_of, task_id, task_name, total_frames_target, completed_frames_proxy,
                backlog_frames, progress_pct_proxy, annotation_job_count, completed_annotation_job_count,
                completed_annotation_job_percent, jobs_status_completed, jobs_status_annotation,
                jobs_status_validation, jobs_status_other, total_active_hours, avg_velocity_fps,
                avg_time_per_frame_minutes, projected_completion_date, note
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                snapshot_id, bp.get("as_of"), bp.get("task_id"), bp.get("task_name"),
                bp.get("total_frames_target"), bp.get("completed_frames_proxy"),
                bp.get("backlog_frames"), bp.get("progress_pct_proxy"),
                bp.get("annotation_job_count"), bp.get("completed_annotation_job_count"),
                bp.get("completed_annotation_job_percent"), bp.get("jobs_status_completed"),
                bp.get("jobs_status_annotation"), bp.get("jobs_status_validation"),
                bp.get("jobs_status_other"), bp.get("total_active_hours"),
                bp.get("avg_velocity_fps"), bp.get("avg_time_per_frame_minutes"),
                bp.get("projected_completion_date"), bp.get("note")
            ))

        qm = marts.get("qa_metrics")
        if qm:
            cur.execute("""
            INSERT OR REPLACE INTO gold_mart_qa_metrics (
                snapshot_id, as_of, task_id, total_reviews, total_defects, first_time_pass_rate,
                rejection_rate, defect_density_per_100_frames, avg_defects_per_job,
                defect_box_displacement, defect_wrong_class, defect_missing_object,
                defect_wrong_attr, avg_miou, avg_f1, qa_score
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                snapshot_id, qm.get("as_of"), qm.get("task_id"), qm.get("total_reviews"),
                qm.get("total_defects"), qm.get("first_time_pass_rate"),
                qm.get("rejection_rate"), qm.get("defect_density_per_100_frames"),
                qm.get("avg_defects_per_job"), qm.get("defect_box_displacement"),
                qm.get("defect_wrong_class"), qm.get("defect_missing_object"),
                qm.get("defect_wrong_attr"), qm.get("avg_miou"),
                qm.get("avg_f1"), qm.get("qa_score")
            ))

        segs = marts.get("annotator_segments", [])
        for s in segs:
            cur.execute("""
            INSERT OR REPLACE INTO gold_mart_annotator_segments (
                snapshot_id, as_of, annotator_id, full_name, tenure_days, completed_frames,
                completed_jobs, total_objects, active_hours_total, velocity_fps,
                velocity_segment, first_time_pass_rate, rejection_rate, quality_risk_flag,
                final_segment, action_recommendation
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                snapshot_id, s.get("as_of"), s.get("annotator_id"), s.get("full_name"),
                s.get("tenure_days"), s.get("completed_frames"), s.get("completed_jobs"),
                s.get("total_objects"), s.get("active_hours_total"), s.get("velocity_fps"),
                s.get("velocity_segment"), s.get("first_time_pass_rate"), s.get("rejection_rate"),
                s.get("quality_risk_flag"), s.get("final_segment"), s.get("action_recommendation")
            ))

    conn.commit()
    conn.close()
    logger.info(f"[Gold] Star Schema & Data Marts loaded for snapshot '{snapshot_id}'.")


def export_gold_to_csv(
    output_dir: Path,
    snapshot_id: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> Dict[str, Path]:
    """TẦNG GOLD -> CSV: Đẩy thẳng toàn bộ Mô hình hình sao và Data Marts ra file CSV chuẩn UTF-8 BOM."""
    output_dir.mkdir(parents=True, exist_ok=True)
    conn = get_connection(db_path)
    cur = conn.cursor()

    exported_files = {}

    target_snapshot = snapshot_id
    if not target_snapshot:
        res = cur.execute("SELECT snapshot_id FROM bronze_snapshots ORDER BY created_at DESC LIMIT 1").fetchone()
        if res:
            target_snapshot = res["snapshot_id"]

    # Danh mục bảng cần export ra CSV phục vụ Power BI (tên bảng trong DB, tên file CSV ra ngoài, có filter theo snapshot không)
    export_catalog = [
        # Dimensions
        ("gold_dim_annotators", "dim_annotators.csv", False),
        ("gold_dim_reviewers", "dim_reviewers.csv", False),
        ("gold_dim_tasks_batches", "dim_tasks_batches.csv", False),
        ("gold_dim_classes_labels", "dim_classes_labels.csv", False),
        ("gold_dim_date", "dim_date.csv", False),
        ("gold_dim_jobs", "dim_jobs.csv", False),
        # Facts
        ("gold_fact_job_sessions", "fact_job_sessions.csv", True),
        ("gold_fact_annotations", "fact_annotations.csv", True),
        ("gold_fact_qa_reviews", "fact_qa_reviews.csv", True),
        ("gold_fact_qa_defects", "fact_qa_defects.csv", True),
        ("gold_fact_ground_truth_eval", "fact_ground_truth_eval.csv", True),
        ("gold_fact_edge_cases", "fact_edge_cases.csv", True),
        # Data Marts
        ("gold_mart_batch_progress", "batch_progress.csv", True),
        ("gold_mart_qa_metrics", "qa_metrics.csv", True),
        ("gold_mart_annotator_segments", "annotator_segments.csv", True),
    ]

    for table_name, file_name, is_filtered in export_catalog:
        query = f"SELECT * FROM {table_name}"
        params = ()
        if is_filtered and target_snapshot:
            query += " WHERE snapshot_id = ?"
            params = (target_snapshot,)

        cur.execute(query, params)
        rows = cur.fetchall()
        col_names = [d[0] for d in cur.description] if cur.description else []

        file_path = output_dir / file_name
        with open(file_path, "w", encoding=CSV_ENCODING, newline="") as f:
            writer = csv.writer(f)
            writer.writerow(col_names)
            for row in rows:
                writer.writerow([("" if v is None else v) for v in row])

        exported_files[file_name] = file_path

    conn.close()
    logger.info(f"Đã xuất thành công {len(exported_files)} file CSV từ Tầng Gold sang {output_dir}")
    return exported_files


def get_audit_trail(snapshot_id: str, db_path: Optional[Path] = None) -> Dict[str, Any]:
    """TRUY VẾT LỊCH SỬ (AUDIT TRAIL): Trích xuất nguyên vẹn dữ liệu thô và chỉ số tại thời điểm quá khứ."""
    conn = get_connection(db_path)
    cur = conn.cursor()

    snapshot = cur.execute("SELECT * FROM bronze_snapshots WHERE snapshot_id = ?", (snapshot_id,)).fetchone()
    if not snapshot:
        conn.close()
        return {}

    cvat_raw = cur.execute("SELECT raw_payload FROM bronze_cvat_raw WHERE snapshot_id = ?", (snapshot_id,)).fetchone()
    github_raw = cur.execute("SELECT raw_payload FROM bronze_github_raw WHERE snapshot_id = ?", (snapshot_id,)).fetchone()
    team_raw = cur.execute("SELECT raw_payload FROM bronze_team_reports_raw WHERE snapshot_id = ?", (snapshot_id,)).fetchone()
    batch_progress = cur.execute("SELECT * FROM gold_mart_batch_progress WHERE snapshot_id = ?", (snapshot_id,)).fetchone()
    qa_metrics = cur.execute("SELECT * FROM gold_mart_qa_metrics WHERE snapshot_id = ?", (snapshot_id,)).fetchone()

    conn.close()
    return {
        "metadata": dict(snapshot),
        "cvat_raw_present": bool(cvat_raw),
        "github_raw_present": bool(github_raw),
        "team_raw_present": bool(team_raw),
        "gold_batch_progress": dict(batch_progress) if batch_progress else None,
        "gold_qa_metrics": dict(qa_metrics) if qa_metrics else None,
    }
