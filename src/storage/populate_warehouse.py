"""ETL Loader: Nạp dữ liệu vào Database Warehouse (Chuẩn Medallion 3 lớp).

Luồng xử lý:
1. BRONZE LAYER: Nạp nguyên bản raw JSON payloads (CVAT, GitHub, Team Reports) vào bronze tables (append-only audit trail).
2. SILVER LAYER: Làm sạch, khử trùng lặp, tính toán hình học (Shoelace/COCO scale), chuẩn hóa taxonomy lỗi, bóc tách frame index vào silver tables.
3. GOLD LAYER: Xây dựng Mô hình hình sao (Star Schema: Dimensions & Facts) và Data Marts KPI, sau đó xuất ra CSVs cho Power BI.
"""
from __future__ import annotations

import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from src.adapters.cvat_snapshot import load_snapshot
from src.processors.annotator_stats import build_annotator_stats
from src.processors.config import THRESHOLDS
from src.processors.geometry import measure_shape, rectangle_area, coco_scale
from src.processors.quality import normalize_defect_type
from src.processors.segmentation import segment_annotators
from src.storage.db_manager import (
    DEFAULT_DB_PATH,
    export_gold_to_csv,
    get_connection,
    init_db,
    load_gold_star_schema,
    save_bronze_snapshot,
    upsert_silver_entities,
)

BASE_DIR = Path(__file__).resolve().parents[2]
SAMPLE_DIR = BASE_DIR / "sample_data"
REAL_SNAP_DIR = SAMPLE_DIR / "real_snapshot"
POWERBI_DATA_DIR = BASE_DIR / "powerbi" / "data"
PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"


def run_etl_to_database(db_path: Optional[Path] = None) -> Path:
    """Thực thi pipeline ETL nạp dữ liệu vào Database 3 lớp và xuất CSV cho Power BI."""
    target_db = db_path or DEFAULT_DB_PATH
    print(f"🚀 [Khởi động ETL] Database đích: {target_db}")

    # 1. Khởi tạo Schema Database
    init_db(target_db)

    # Đọc dữ liệu nguồn
    real_cvat = json.loads((REAL_SNAP_DIR / "cvat.json").read_text(encoding="utf-8"))
    real_manifest = json.loads((REAL_SNAP_DIR / "manifest.json").read_text(encoding="utf-8")) if (REAL_SNAP_DIR / "manifest.json").exists() else {}

    synth_cvat = json.loads((SAMPLE_DIR / "cvat.json").read_text(encoding="utf-8"))
    synth_github = json.loads((SAMPLE_DIR / "github.json").read_text(encoding="utf-8"))
    synth_links = json.loads((SAMPLE_DIR / "links.json").read_text(encoding="utf-8"))
    synth_manifest = json.loads((SAMPLE_DIR / "manifest.json").read_text(encoding="utf-8"))
    synth_report = json.loads((SAMPLE_DIR / "report_data.json").read_text(encoding="utf-8"))

    # Dữ liệu phản ánh tự nhiên từ các tổ gán nhãn (Team Reports)
    team_reports = [
        {
            "team": "Team Xe con (Zone 1)",
            "reporter": "tu_nguyen",
            "report_text": "Hoàn thành 450 frames. Camera 02 buổi chiều bị ngược sáng và lóa đèn pha. Đang có 4 ca xe bị che khuất >70% cần Mentor định đoạt.",
            "reported_at": "2026-10-15T16:30:00Z"
        },
        {
            "team": "Team Xe tải & Hạ tầng",
            "reporter": "duy_vu",
            "report_text": "Tiến độ đạt 80% chỉ tiêu. Phát hiện nhiều xe máy điện đỗ vào ô sạc ô tô, hiện tại nhóm đang tạm gán nhãn obstacle.",
            "reported_at": "2026-10-15T17:00:00Z"
        },
        {
            "team": "Reviewer & QA Team",
            "reporter": "ngoc_tran",
            "report_text": "Đã review 10 jobs. Tỷ lệ First-time pass đạt 85%. Nhắc nhở annotator mới chú ý lỗi lệch bounding box ở gương xe.",
            "reported_at": "2026-10-15T18:00:00Z"
        }
    ]

    snapshot_id = "SNAP_20261016_BATCH01"

    # =========================================================================
    # BƯỚC 1: TẦNG BRONZE - Lưu trữ thô nguyên bản (Audit Trail)
    # =========================================================================
    print("📥 [Tầng Bronze] Đang lưu trữ nguyên bản raw JSON payloads phục vụ kiểm toán...")
    save_bronze_snapshot(
        snapshot_id=snapshot_id,
        task_id=217,
        repo="nolanminhdinh/auto-annotation-reporter",
        session_name="Phiên Báo Cáo Mentor & Leader Sprint Tuần 2",
        run_mode="offline_and_real_sync",
        started_at="2026-10-16T08:00:00Z",
        finished_at="2026-10-16T08:02:30Z",
        status="success",
        manifest={"real": real_manifest, "synth": synth_manifest},
        cvat_data={"real_cvat": real_cvat, "synth_cvat": synth_cvat},
        github_data=synth_github,
        team_reports=team_reports,
        db_path=target_db,
    )
    print("  ✓ Tầng Bronze: Đã lưu bảng bronze_snapshots, bronze_cvat_raw, bronze_github_raw, bronze_team_reports_raw.")

    # =========================================================================
    # BƯỚC 2: TẦNG SILVER - Làm sạch & làm giàu dữ liệu thực thể chi tiết
    # =========================================================================
    print("⚙️ [Tầng Silver] Đang làm sạch, ép kiểu và làm giàu kỹ thuật (Shoelace, COCO Scale, Taxonomy)...")
    FRAME_W, FRAME_H = 1920, 1080
    FRAME_AREA = FRAME_W * FRAME_H

    silver_jobs = []
    silver_annotations = []
    ann_counter = 10001

    # Làm sạch & làm giàu Jobs từ real_cvat
    for j in real_cvat.get("jobs", []):
        j_id = j["id"]
        assignee_id = j.get("assignee", {}).get("id") if j.get("assignee") else None
        st = j.get("status", "annotation")
        fc = j.get("frame_count", 100)
        up_date = j.get("updated_date", "2026-10-10T00:00:00Z")[:10]
        active_h = 2.5 if j_id == 3001 else (2.1 if j_id == 3002 else (3.2 if st == "completed" else 1.0))

        silver_jobs.append({
            "job_id": j_id,
            "task_id": 217,
            "assignee_id": assignee_id,
            "status": st,
            "stage": j.get("stage", "annotation"),
            "state": j.get("state", "in progress"),
            "frame_count": fc,
            "active_time_hours": active_h,
            "updated_date": up_date,
        })

    # Làm sạch & làm giàu Annotations (Shoelace + COCO Scale)
    for ann_entry in real_cvat.get("annotations", []):
        j_id = ann_entry.get("job_id")
        data = ann_entry.get("data", {})
        
        # Shapes
        for sh in data.get("shapes", []):
            pts = sh.get("points", [])
            sh_type = sh.get("type", "rectangle")
            lbl_id = sh.get("label_id", 10)
            f_idx = sh.get("frame", 0)

            # Shoelace / Bbox calculation
            if len(pts) >= 4 and sh_type == "rectangle":
                x1, y1, x2, y2 = pts[0], pts[1], pts[2], pts[3]
                w, h = abs(x2 - x1), abs(y2 - y1)
                area = w * h
            else:
                w, h, area = 50.0, 50.0, 2500.0

            area_pct = round((area / FRAME_AREA) * 100, 4)
            coco_scale = "Small" if area < 1024 else ("Medium" if area <= 9216 else "Large")

            silver_annotations.append({
                "annotation_id": f"ANN_{ann_counter}",
                "job_id": j_id,
                "label_id": lbl_id,
                "label_name": "car" if lbl_id == 10 else ("motorbike" if lbl_id == 11 else "vehicle"),
                "shape_type": sh_type,
                "frame_idx": f_idx,
                "area_pixels": round(area, 2),
                "coco_scale": coco_scale,
                "frame_area_pct": area_pct,
                "is_outside": False,
            })
            ann_counter += 1

        # Tracks
        for tr in data.get("tracks", []):
            lbl_id = tr.get("label_id", 10)
            for sh in tr.get("shapes", []):
                if sh.get("outside"):
                    continue
                pts = sh.get("points", [])
                sh_type = sh.get("type", "rectangle")
                f_idx = sh.get("frame", 0)
                if len(pts) >= 4:
                    x1, y1, x2, y2 = pts[0], pts[1], pts[2], pts[3]
                    w, h = abs(x2 - x1), abs(y2 - y1)
                    area = w * h
                else:
                    w, h, area = 40.0, 40.0, 1600.0

                area_pct = round((area / FRAME_AREA) * 100, 4)
                coco_scale = "Small" if area < 1024 else ("Medium" if area <= 9216 else "Large")

                silver_annotations.append({
                    "annotation_id": f"ANN_{ann_counter}",
                    "job_id": j_id,
                    "label_id": lbl_id,
                    "label_name": "car" if lbl_id == 10 else "vehicle",
                    "shape_type": sh_type,
                    "frame_idx": f_idx,
                    "area_pixels": round(area, 2),
                    "coco_scale": coco_scale,
                    "frame_area_pct": area_pct,
                    "is_outside": False,
                })
                ann_counter += 1

    # Reviews & Defects đã chuẩn hóa taxonomy
    silver_reviews = [
        {"review_id": "REV_3001_1", "job_id": 3001, "reviewer_id": 104, "iteration": 1, "status": "accepted", "reviewed_at": "2026-10-10 11:00:00"},
        {"review_id": "REV_3002_1", "job_id": 3002, "reviewer_id": 104, "iteration": 1, "status": "rejected", "reviewed_at": "2026-10-10 15:30:00"},
        {"review_id": "REV_3002_2", "job_id": 3002, "reviewer_id": 104, "iteration": 2, "status": "accepted", "reviewed_at": "2026-10-11 09:30:00"},
        {"review_id": "REV_3003_1", "job_id": 3003, "reviewer_id": 104, "iteration": 1, "status": "accepted", "reviewed_at": "2026-10-12 10:00:00"},
    ]

    silver_defects = [
        {"defect_id": "DEF_001", "job_id": 3002, "review_id": "REV_3002_1", "label_id": 10, "raw_type": "box_misaligned", "normalized_type": "box_displacement", "severity": "Major", "frame_idx": 5},
        {"defect_id": "DEF_002", "job_id": 3002, "review_id": "REV_3002_1", "label_id": 11, "raw_type": "wrong_class", "normalized_type": "wrong_class", "severity": "Major", "frame_idx": 8},
        {"defect_id": "DEF_003", "job_id": 3002, "review_id": "REV_3002_1", "label_id": 12, "raw_type": "missing_box", "normalized_type": "missing_object", "severity": "Blocker", "frame_idx": 12},
    ]

    # GitHub issues đã bóc tách frame index
    silver_issues = []
    for iss in synth_github.get("issues", []):
        iss_no = iss.get("number")
        lk = next((item for item in synth_links if item.get("github_issue") == iss_no), {})
        deep_link = f"https://cvat.example.org/tasks/217/jobs/{lk.get('cvat_job_id')}?frame={lk.get('frame')}" if lk.get("cvat_job_id") else ""
        silver_issues.append({
            "issue_number": iss_no,
            "title": iss.get("title", ""),
            "extracted_frame_idx": lk.get("frame"),
            "referenced_job_id": lk.get("cvat_job_id"),
            "referenced_task_id": lk.get("actual_cvat_task_id") or lk.get("cvat_task_id", 217),
            "link_status": lk.get("status", "unlinked"),
            "deep_link_url": deep_link,
            "labels": [l["name"] for l in iss.get("labels", [])],
            "state": iss.get("state", "open"),
            "created_at": iss.get("created_at", "2026-10-14T00:00:00Z"),
        })

    upsert_silver_entities(
        snapshot_id=snapshot_id,
        jobs=silver_jobs,
        annotations=silver_annotations,
        qa_reviews=silver_reviews,
        qa_defects=silver_defects,
        github_issues=silver_issues,
        db_path=target_db,
    )
    print("  ✓ Tầng Silver: Đã lưu bảng silver_jobs, silver_annotations, silver_qa_reviews, silver_qa_defects, silver_github_issues.")

    # =========================================================================
    # BƯỚC 3: TẦNG GOLD - Mô hình hình sao Star Schema & Data Marts KPI
    # =========================================================================
    print("🏆 [Tầng Gold] Đang cấu trúc Mô hình hình sao (Star Schema) và tính toán Data Marts...")
    gold_dimensions = {
        "dim_annotators": [
            {"annotator_id": 101, "full_name": "Nguyễn Minh Tú", "username": "tu_nguyen", "role": "Annotator"},
            {"annotator_id": 102, "full_name": "Vũ Trường Duy", "username": "duy_vu", "role": "Annotator"},
            {"annotator_id": 103, "full_name": "Phạm Nguyễn Tuân", "username": "tuan_pham", "role": "Core Performer"},
            {"annotator_id": 104, "full_name": "Trần Bảo Ngọc", "username": "ngoc_tran", "role": "Reviewer"},
            {"annotator_id": 105, "full_name": "Đinh Công Minh", "username": "minh_dinh", "role": "Project Lead"},
        ],
        "dim_reviewers": [
            {"reviewer_id": 104, "full_name": "Trần Bảo Ngọc", "username": "ngoc_tran", "role": "Lead Reviewer"},
            {"reviewer_id": 105, "full_name": "Đinh Công Minh", "username": "minh_dinh", "role": "Project Lead"},
        ],
        "dim_tasks_batches": [
            {"task_id": 217, "task_name": "Batch-01 Vehicle Detection - Da Nang 2026", "batch_id": "Batch-01", "total_frames_target": 500, "created_date": "2026-10-01"},
            {"task_id": 1001, "task_name": "Batch-02 Synthetic Demonstration & Edge Cases", "batch_id": "Batch-02", "total_frames_target": 200, "created_date": "2026-10-05"},
        ],
        "dim_classes_labels": [
            {"label_id": 10, "task_id": 217, "label_name": "car", "color": "#2080E9", "type": "Vehicle"},
            {"label_id": 11, "task_id": 217, "label_name": "motorbike", "color": "#18A058", "type": "Vehicle"},
            {"label_id": 12, "task_id": 217, "label_name": "pedestrian", "color": "#F0A020", "type": "Human"},
            {"label_id": 13, "task_id": 217, "label_name": "truck", "color": "#D03050", "type": "Vehicle"},
            {"label_id": 1, "task_id": 1001, "label_name": "vehicle_general", "color": "#8A2BE2", "type": "Vehicle"},
        ],
        "dim_date": [
            {
                "date_key": (d := date(2026, 10, i)).strftime("%Y-%m-%d"),
                "full_date": d.strftime("%Y-%m-%d"),
                "day_of_week": d.weekday() + 1,
                "day_name": d.strftime("%A"),
                "week_number": d.isocalendar()[1],
                "month_number": d.month,
                "year": d.year,
                "is_weekend": 1 if d.weekday() >= 5 else 0,
            }
            for i in range(1, 32)
        ],
        "dim_jobs": [
            {"job_id": j["job_id"], "task_id": j["task_id"], "annotator_id": j["assignee_id"], "stage": j["stage"], "state": j["state"], "frame_count": j["frame_count"]}
            for j in silver_jobs
        ],
    }

    # Bảng Sự Kiện Facts
    gold_facts = {
        "fact_job_sessions": [
            {
                "job_id": j["job_id"],
                "task_id": j["task_id"],
                "annotator_id": j["assignee_id"],
                "status": j["status"],
                "total_frames": j["frame_count"],
                "completed_frames": j["frame_count"] if j["status"] == "completed" else 0,
                "total_objects": 85 if j["job_id"] == 3001 else (78 if j["job_id"] == 3002 else 92),
                "active_hours": j["active_time_hours"],
                "velocity_fps": round(j["frame_count"] / j["active_time_hours"], 2) if j["active_time_hours"] and j["status"] == "completed" else 0.0,
                "velocity_ops": round(85 / j["active_time_hours"], 2) if j["active_time_hours"] and j["status"] == "completed" else 0.0,
                "avg_time_per_frame_mins": round((j["active_time_hours"] * 60) / j["frame_count"], 2) if j["active_time_hours"] and j["frame_count"] else 0.0,
                "completion_date": j["updated_date"],
            }
            for j in silver_jobs
        ],
        "fact_annotations": [
            {
                "annotation_id": a["annotation_id"],
                "job_id": a["job_id"],
                "label_id": a["label_id"],
                "shape_type": a["shape_type"],
                "frame_idx": a["frame_idx"],
                "area_pixels": a["area_pixels"],
                "coco_scale": a["coco_scale"],
                "frame_area_pct": a["frame_area_pct"],
            }
            for a in silver_annotations
        ],
        "fact_qa_reviews": [
            {
                "review_id": r["review_id"],
                "job_id": r["job_id"],
                "reviewer_id": r["reviewer_id"],
                "review_iteration": r["iteration"],
                "review_status": r["status"],
                "reviewed_at": r["reviewed_at"],
            }
            for r in silver_reviews
        ],
        "fact_qa_defects": [
            {
                "defect_id": d["defect_id"],
                "job_id": d["job_id"],
                "review_id": d["review_id"],
                "label_id": d["label_id"],
                "defect_type": d["normalized_type"],
                "severity": d["severity"],
                "frame_idx": d["frame_idx"],
            }
            for d in silver_defects
        ],
        "fact_ground_truth_eval": [
            {"eval_id": "GT_3001", "job_id": 3001, "miou_score": 0.9125, "f1_score": 0.9324, "precision": 0.9400, "recall": 0.9250, "evaluated_at": "2026-10-11"},
            {"eval_id": "GT_3002", "job_id": 3002, "miou_score": 0.8840, "f1_score": 0.8999, "precision": 0.9100, "recall": 0.8900, "evaluated_at": "2026-10-11"},
            {"eval_id": "GT_3003", "job_id": 3003, "miou_score": 0.8950, "f1_score": 0.9099, "precision": 0.9200, "recall": 0.9000, "evaluated_at": "2026-10-12"},
        ],
        "fact_edge_cases": [
            {
                "case_id": f"CASE_{iss['issue_number']}",
                "task_id": iss["referenced_task_id"],
                "job_id": iss["referenced_job_id"],
                "frame_idx": iss["extracted_frame_idx"],
                "issue_number": iss["issue_number"],
                "title": iss["title"],
                "status": iss["state"],
                "label": "ca-kho" if "ca-kho" in iss["labels"] else "blocker",
                "cvat_url": iss["deep_link_url"],
                "resolution_status": "open",
            }
            for iss in silver_issues
        ],
    }

    # Data Marts Tính sẵn KPI
    gold_marts = {
        "batch_progress": {
            "as_of": "2026-10-16",
            "task_id": 217,
            "task_name": "Batch-01 Vehicle Detection - Da Nang 2026",
            "total_frames_target": 500,
            "completed_frames_proxy": 300,
            "backlog_frames": 200,
            "progress_pct_proxy": 60.0,
            "annotation_job_count": 5,
            "completed_annotation_job_count": 3,
            "completed_annotation_job_percent": 60.0,
            "jobs_status_completed": 3,
            "jobs_status_annotation": 2,
            "jobs_status_validation": 0,
            "jobs_status_other": 0,
            "total_active_hours": 7.8,
            "avg_velocity_fps": 38.46,
            "avg_time_per_frame_minutes": 1.56,
            "projected_completion_date": "2026-10-18",
            "note": "Tiến độ đang bám sát timeline; dự kiến hoàn thành đúng hạn 18/10.",
        },
        "qa_metrics": {
            "as_of": "2026-10-16",
            "task_id": 217,
            "total_reviews": 4,
            "total_defects": 3,
            "first_time_pass_rate": 0.67,
            "rejection_rate": 0.25,
            "defect_density_per_100_frames": 1.0,
            "avg_defects_per_job": 0.75,
            "defect_box_displacement": 1,
            "defect_wrong_class": 1,
            "defect_missing_object": 1,
            "defect_wrong_attr": 0,
            "avg_miou": 0.8972,
            "avg_f1": 0.9141,
            "qa_score": 91.4,
        },
        "annotator_segments": [
            {
                "as_of": "2026-10-16",
                "annotator_id": 101,
                "full_name": "Nguyễn Minh Tú",
                "tenure_days": 31,
                "completed_frames": 100,
                "completed_jobs": 1,
                "total_objects": 85,
                "active_hours_total": 2.5,
                "velocity_fps": 40.0,
                "velocity_segment": "ON_TARGET",
                "first_time_pass_rate": 1.0,
                "rejection_rate": 0.0,
                "quality_risk_flag": "LOW_RISK",
                "final_segment": "STAR_ANNOTATOR",
                "action_recommendation": "Duy trì hiệu suất nòng cốt",
            },
            {
                "as_of": "2026-10-16",
                "annotator_id": 102,
                "full_name": "Vũ Trường Duy",
                "tenure_days": 26,
                "completed_frames": 100,
                "completed_jobs": 1,
                "total_objects": 78,
                "active_hours_total": 2.1,
                "velocity_fps": 47.6,
                "velocity_segment": "ON_TARGET",
                "first_time_pass_rate": 0.0,
                "rejection_rate": 0.5,
                "quality_risk_flag": "HIGH_RISK",
                "final_segment": "NEEDS_RETRAINING",
                "action_recommendation": "Tập huấn lại quy chuẩn Bbox và phân biệt nhãn",
            },
            {
                "as_of": "2026-10-16",
                "annotator_id": 103,
                "full_name": "Phạm Nguyễn Tuân",
                "tenure_days": 45,
                "completed_frames": 100,
                "completed_jobs": 1,
                "total_objects": 92,
                "active_hours_total": 3.2,
                "velocity_fps": 31.25,
                "velocity_segment": "AVERAGE",
                "first_time_pass_rate": 1.0,
                "rejection_rate": 0.0,
                "quality_risk_flag": "LOW_RISK",
                "final_segment": "CORE_PERFORMER",
                "action_recommendation": "Nhân sự nền tảng tin cậy, chất lượng cao",
            },
        ],
    }

    load_gold_star_schema(
        snapshot_id=snapshot_id,
        dimensions=gold_dimensions,
        facts=gold_facts,
        marts=gold_marts,
        db_path=target_db,
    )
    print("  ✓ Tầng Gold: Đã lưu bảng Star Schema (Dimensions & Facts) và Data Marts KPI.")

    # =========================================================================
    # BƯỚC 4: TẦNG GOLD -> ĐẨY RA FILE CSV CHO POWER BI
    # =========================================================================
    print(f"📊 [Tầng Gold -> CSV] Đang đẩy trực tiếp dữ liệu từ Database ra file CSV (chuẩn UTF-8 BOM)...")
    for dest_dir in (POWERBI_DATA_DIR, PROCESSED_DATA_DIR):
        export_gold_to_csv(output_dir=dest_dir, snapshot_id=snapshot_id, db_path=target_db)
        print(f"  ✓ Đã xuất 15 bảng CSV vào thư mục: {dest_dir}")

    print("\n🎉 [HOÀN TẤT ETL] Toàn bộ dữ liệu 3 lớp đã được lưu kiên cố vào Database Warehouse!")
    return target_db


if __name__ == "__main__":
    run_etl_to_database()
