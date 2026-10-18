"""Script sinh toàn bộ dữ liệu chuẩn hóa cho Power BI Dashboard (Star Schema + Aggregated Tables).

Tuân thủ:
- Data Contract v1 (PROJECT_ANALYTICS_SPEC.md & BUILD_PLAN_MINH.md)
- UTF-8 BOM (utf-8-sig) để Power BI trên Windows đọc tiếng Việt không lỗi font
- Làm tròn 4 chữ số thập phân
- Sinh đầy đủ các bảng Dimension & Fact cho cả 5 trang báo cáo
"""
from __future__ import annotations

import csv
import json
import math
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

ENCODING = "utf-8-sig"
BASE_DIR = Path(__file__).resolve().parent.parent
REAL_SNAP = BASE_DIR / "sample_data" / "real_snapshot"
SYNTH_SNAP = BASE_DIR / "sample_data"
OUT_DIR = BASE_DIR / "data" / "processed"
POWERBI_DATA_DIR = BASE_DIR / "powerbi" / "data"

for d in (OUT_DIR, POWERBI_DATA_DIR):
    d.mkdir(parents=True, exist_ok=True)


def _write_csv(filepath: Path, fieldnames: List[str], rows: List[Dict[str, Any]]) -> None:
    with open(filepath, "w", encoding=ENCODING, newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            # Clean None values to empty string
            clean_r = {k: ("" if r.get(k) is None else r.get(k)) for k in fieldnames}
            writer.writerow(clean_r)
    print(f"  [OK] Exported {len(rows)} rows to {filepath.name}")


def generate_all():
    print("=== Đang sinh dữ liệu chuẩn hóa cho Power BI ===")

    # 1. Đọc dữ liệu từ real_snapshot và sample_data
    real_cvat = json.loads((REAL_SNAP / "cvat.json").read_text(encoding="utf-8"))
    synth_cvat = json.loads((SYNTH_SNAP / "cvat.json").read_text(encoding="utf-8"))
    synth_report = json.loads((SYNTH_SNAP / "report_data.json").read_text(encoding="utf-8"))
    github_data = json.loads((SYNTH_SNAP / "github.json").read_text(encoding="utf-8"))
    links_data = json.loads((SYNTH_SNAP / "links.json").read_text(encoding="utf-8"))

    # -------------------------------------------------------------
    # BẢNG 1: dim_annotators
    # -------------------------------------------------------------
    annotators = [
        {"annotator_id": 101, "full_name": "Nguyễn Minh Tú", "username": "tu_nguyen", "role": "Annotator", "joined_date": "2026-09-15"},
        {"annotator_id": 102, "full_name": "Vũ Trường Duy", "username": "duy_vu", "role": "Annotator", "joined_date": "2026-09-20"},
        {"annotator_id": 103, "full_name": "Phạm Nguyễn Tuân", "username": "tuan_pham", "role": "Core Performer", "joined_date": "2026-09-01"},
        {"annotator_id": 104, "full_name": "Trần Bảo Ngọc", "username": "ngoc_tran", "role": "Reviewer", "joined_date": "2026-09-01"},
        {"annotator_id": 105, "full_name": "Đinh Công Minh", "username": "minh_dinh", "role": "Project Lead", "joined_date": "2026-08-15"},
    ]

    # -------------------------------------------------------------
    # BẢNG 2: dim_reviewers
    # -------------------------------------------------------------
    reviewers = [
        {"reviewer_id": 104, "full_name": "Trần Bảo Ngọc", "role": "Lead Reviewer", "team": "QA Core"},
        {"reviewer_id": 105, "full_name": "Đinh Công Minh", "role": "Mentor / Tech Lead", "team": "Management"},
        {"reviewer_id": 999, "full_name": "Auto GT Evaluator", "role": "System Benchmark", "team": "AI System"},
    ]

    # -------------------------------------------------------------
    # BẢNG 3: dim_tasks_batches
    # -------------------------------------------------------------
    tasks_batches = [
        {
            "task_id": 217,
            "task_name": "Batch-01 Vehicle Detection - Da Nang 2026",
            "batch_id": "Batch-01",
            "total_frames_target": 500,
            "target_deadline": "2026-10-18",
            "status": "In Progress",
            "description": "Gán nhãn phát hiện phương tiện giao thông tại nút giao Đà Nẵng",
        },
        {
            "task_id": 1001,
            "task_name": "Batch-02 Synthetic Demonstration & Edge Cases",
            "batch_id": "Batch-02",
            "total_frames_target": 200,
            "target_deadline": "2026-10-25",
            "status": "Planned",
            "description": "Tập dữ liệu giả lập tình huống khó và đánh giá mô hình",
        },
    ]

    # -------------------------------------------------------------
    # BẢNG 4: dim_classes_labels
    # -------------------------------------------------------------
    classes_labels = [
        {"label_id": 10, "label_name": "car", "label_category": "Vehicle", "color_hex": "#2080E9"},
        {"label_id": 11, "label_name": "motorbike", "label_category": "Vehicle", "color_hex": "#18A058"},
        {"label_id": 12, "label_name": "pedestrian", "label_category": "Human", "color_hex": "#F0A020"},
        {"label_id": 13, "label_name": "truck", "label_category": "Vehicle", "color_hex": "#D03050"},
        {"label_id": 1, "label_name": "vehicle_general", "label_category": "Vehicle", "color_hex": "#8A2BE2"},
    ]

    # -------------------------------------------------------------
    # BẢNG 5: dim_date (Lịch 2026-10-01 đến 2026-10-31)
    # -------------------------------------------------------------
    dates = []
    start_d = date(2026, 10, 1)
    for i in range(31):
        cur_d = start_d + timedelta(days=i)
        dates.append({
            "date_key": cur_d.strftime("%Y-%m-%d"),
            "day": cur_d.day,
            "day_name": cur_d.strftime("%A"),
            "week_num": cur_d.isocalendar()[1],
            "month_num": cur_d.month,
            "month_name": cur_d.strftime("%B"),
            "quarter": f"Q{(cur_d.month - 1) // 3 + 1}",
            "year": cur_d.year,
            "is_weekend": 1 if cur_d.weekday() >= 5 else 0,
        })

    # -------------------------------------------------------------
    # BẢNG 6: dim_jobs & FACT 7: fact_job_sessions
    # -------------------------------------------------------------
    jobs = []
    job_sessions = []

    # Map jobs từ real_snapshot
    for j in real_cvat.get("jobs", []):
        j_id = j["id"]
        assignee_id = j.get("assignee", {}).get("id") if j.get("assignee") else None
        st = j.get("status", "annotation")
        state = j.get("state", "annotation")
        fc = j.get("frame_count", 100)
        up_date = j.get("updated_date", "2026-10-10T00:00:00Z")[:10]

        # Đếm objects thực tế trong annotations
        obj_count = 0
        for ann in real_cvat.get("annotations", []):
            if ann.get("job_id") == j_id:
                shapes = ann.get("data", {}).get("shapes", [])
                obj_count += len(shapes)
                for tr in ann.get("data", {}).get("tracks", []):
                    obj_count += len([s for s in tr.get("shapes", []) if not s.get("outside")])

        # Active time estimate (hoặc null nếu chưa có log)
        # Giả lập active hours phù hợp với completed jobs: 100 frame completed ~ 2.2 - 2.8 giờ
        if st == "completed":
            active_h = 2.5 if j_id == 3001 else (2.1 if j_id == 3002 else 3.2)
        else:
            active_h = 1.0 if st == "annotation" and assignee_id else 0.0

        jobs.append({
            "job_id": j_id,
            "task_id": 217,
            "annotator_id": assignee_id,
            "stage": j.get("stage", "annotation"),
            "state": state,
            "status": st,
            "type": j.get("type", "annotation"),
            "frame_count": fc,
            "updated_date": up_date,
        })

        job_sessions.append({
            "job_id": j_id,
            "task_id": 217,
            "annotator_id": assignee_id,
            "date_key": up_date,
            "total_frames": fc,
            "total_objects": obj_count,
            "active_time_hours": active_h if active_h > 0 else None,
            "status": st,
        })

    # Thêm jobs từ synthetic
    for j in synth_cvat.get("jobs", []):
        j_id = j["id"]
        st = j.get("state", "in progress")
        jobs.append({
            "job_id": j_id,
            "task_id": 1001,
            "annotator_id": 103 if j_id == 2001 else 102,
            "stage": j.get("stage", "annotation"),
            "state": st,
            "status": "completed" if st == "completed" else "annotation",
            "type": j.get("type", "annotation"),
            "frame_count": 10,
            "updated_date": "2026-10-12",
        })
        job_sessions.append({
            "job_id": j_id,
            "task_id": 1001,
            "annotator_id": 103 if j_id == 2001 else 102,
            "date_key": "2026-10-12",
            "total_frames": 10,
            "total_objects": 4,
            "active_time_hours": 0.4 if st == "completed" else 0.2,
            "status": "completed" if st == "completed" else "annotation",
        })

    # -------------------------------------------------------------
    # BẢNG 8: fact_annotations (Bbox, Shoelace, COCO scale)
    # -------------------------------------------------------------
    annotations_rows = []
    ann_pk = 10001
    FRAME_W, FRAME_H = 1920, 1080
    FRAME_AREA = FRAME_W * FRAME_H

    for ann_entry in real_cvat.get("annotations", []):
        j_id = ann_entry.get("job_id")
        data = ann_entry.get("data", {})
        
        # Shapes
        for sh in data.get("shapes", []):
            pts = sh.get("points", [])
            lbl_id = sh.get("label_id", 10)
            f_idx = sh.get("frame", 0)
            sh_type = sh.get("type", "rectangle")

            if len(pts) >= 4 and sh_type == "rectangle":
                x1, y1, x2, y2 = pts[0], pts[1], pts[2], pts[3]
                w = abs(x2 - x1)
                h = abs(y2 - y1)
                area = w * h
            else:
                w, h = 50.0, 50.0
                area = 2500.0

            area_pct = round((area / FRAME_AREA) * 100, 4)
            scale = "Small" if area < 1024 else ("Medium" if area <= 9216 else "Large")

            annotations_rows.append({
                "annotation_id": f"ANN_{ann_pk}",
                "job_id": j_id,
                "frame_idx": f_idx,
                "label_id": lbl_id,
                "shape_type": sh_type,
                "bbox_width": round(w, 2),
                "bbox_height": round(h, 2),
                "area_pixels": round(area, 2),
                "frame_area_pct": area_pct,
                "size_scale": scale,
            })
            ann_pk += 1

        # Tracks
        for tr in data.get("tracks", []):
            lbl_id = tr.get("label_id", 10)
            for sh in tr.get("shapes", []):
                if sh.get("outside"):
                    continue
                pts = sh.get("points", [])
                f_idx = sh.get("frame", 0)
                sh_type = sh.get("type", "rectangle")
                if len(pts) >= 4:
                    x1, y1, x2, y2 = pts[0], pts[1], pts[2], pts[3]
                    w = abs(x2 - x1)
                    h = abs(y2 - y1)
                    area = w * h
                else:
                    w, h, area = 40.0, 40.0, 1600.0

                area_pct = round((area / FRAME_AREA) * 100, 4)
                scale = "Small" if area < 1024 else ("Medium" if area <= 9216 else "Large")
                annotations_rows.append({
                    "annotation_id": f"ANN_{ann_pk}",
                    "job_id": j_id,
                    "frame_idx": f_idx,
                    "label_id": lbl_id,
                    "shape_type": sh_type,
                    "bbox_width": round(w, 2),
                    "bbox_height": round(h, 2),
                    "area_pixels": round(area, 2),
                    "frame_area_pct": area_pct,
                    "size_scale": scale,
                })
                ann_pk += 1

    # -------------------------------------------------------------
    # BẢNG 9: fact_qa_reviews
    # -------------------------------------------------------------
    qa_reviews = [
        {"review_id": "REV_3001_1", "job_id": 3001, "reviewer_id": 104, "review_iteration": 1, "review_decision": "Accepted", "reviewed_at": "2026-10-10 11:00:00"},
        {"review_id": "REV_3002_1", "job_id": 3002, "reviewer_id": 104, "review_iteration": 1, "review_decision": "Rejected", "reviewed_at": "2026-10-10 15:30:00"},
        {"review_id": "REV_3002_2", "job_id": 3002, "reviewer_id": 104, "review_iteration": 2, "review_decision": "Accepted", "reviewed_at": "2026-10-11 09:30:00"},
        {"review_id": "REV_3003_1", "job_id": 3003, "reviewer_id": 104, "review_iteration": 1, "review_decision": "Accepted", "reviewed_at": "2026-10-12 10:00:00"},
        {"review_id": "REV_2001_1", "job_id": 2001, "reviewer_id": 105, "review_iteration": 1, "review_decision": "Accepted", "reviewed_at": "2026-10-13 14:00:00"},
    ]

    # -------------------------------------------------------------
    # BẢNG 10: fact_qa_defects
    # -------------------------------------------------------------
    qa_defects = [
        {
            "defect_id": "DEF_001",
            "review_id": "REV_3002_1",
            "job_id": 3002,
            "frame_idx": 5,
            "label_id": 10,
            "defect_type": "box_displacement",
            "severity": "Major",
            "description": "Bounding box xe hơi bị lệch 8px so với đuôi xe",
            "cvat_deep_link": "https://cvat.example.org/tasks/217/jobs/3002?frame=5",
        },
        {
            "defect_id": "DEF_002",
            "review_id": "REV_3002_1",
            "job_id": 3002,
            "frame_idx": 8,
            "label_id": 11,
            "defect_type": "wrong_class",
            "severity": "Major",
            "description": "Gán nhầm xe máy thành xe tải nhỏ",
            "cvat_deep_link": "https://cvat.example.org/tasks/217/jobs/3002?frame=8",
        },
        {
            "defect_id": "DEF_003",
            "review_id": "REV_3002_1",
            "job_id": 3002,
            "frame_idx": 12,
            "label_id": 12,
            "defect_type": "missing_object",
            "severity": "Blocker",
            "description": "Bỏ sót người đi bộ tại góc khuất",
            "cvat_deep_link": "https://cvat.example.org/tasks/217/jobs/3002?frame=12",
        },
    ]

    # -------------------------------------------------------------
    # BẢNG 11: fact_ground_truth_eval
    # -------------------------------------------------------------
    gt_evals = [
        {"eval_id": "GT_3001", "job_id": 3001, "mean_iou": 0.9125, "precision": 0.9400, "recall": 0.9250, "f1_score": 0.9324},
        {"eval_id": "GT_3002", "job_id": 3002, "mean_iou": 0.8840, "precision": 0.9100, "recall": 0.8900, "f1_score": 0.8999},
        {"eval_id": "GT_3003", "job_id": 3003, "mean_iou": 0.8950, "precision": 0.9200, "recall": 0.9000, "f1_score": 0.9099},
    ]

    # -------------------------------------------------------------
    # BẢNG 12: fact_edge_cases
    # -------------------------------------------------------------
    edge_cases = []
    for iss in github_data.get("issues", []):
        iss_no = iss.get("number")
        lbls = [l["name"] for l in iss.get("labels", [])]
        # find link status
        lk = next((item for item in links_data if item.get("github_issue") == iss_no), {})
        status = lk.get("status", "unlinked")
        tid = lk.get("actual_cvat_task_id") or lk.get("cvat_task_id")
        jid = lk.get("cvat_job_id")
        frame = lk.get("frame")
        deep_link = f"https://cvat.example.org/tasks/{tid}/jobs/{jid}?frame={frame}" if (tid and jid) else ""

        edge_cases.append({
            "case_id": f"ISSUE_{iss_no}",
            "number": iss_no,
            "title": iss.get("title", ""),
            "description": iss.get("body", ""),
            "labels": ", ".join(lbls),
            "state": iss.get("state", "open"),
            "author": iss.get("user", {}).get("login", "unknown"),
            "severity": "Blocker" if "blocker" in lbls else ("Major" if "ca-kho" in lbls else "Minor"),
            "task_id": tid,
            "job_id": jid,
            "frame": frame,
            "link_status": status,
            "cvat_deep_link": deep_link,
            "source_url": iss.get("html_url", f"https://github.com/issues/{iss_no}"),
        })

    # XUẤT RA CẢ data/processed VÀ powerbi/data
    tables = [
        ("dim_annotators.csv", ["annotator_id", "full_name", "username", "role", "joined_date"], annotators),
        ("dim_reviewers.csv", ["reviewer_id", "full_name", "role", "team"], reviewers),
        ("dim_tasks_batches.csv", ["task_id", "task_name", "batch_id", "total_frames_target", "target_deadline", "status", "description"], tasks_batches),
        ("dim_classes_labels.csv", ["label_id", "label_name", "label_category", "color_hex"], classes_labels),
        ("dim_date.csv", ["date_key", "day", "day_name", "week_num", "month_num", "month_name", "quarter", "year", "is_weekend"], dates),
        ("dim_jobs.csv", ["job_id", "task_id", "annotator_id", "stage", "state", "status", "type", "frame_count", "updated_date"], jobs),
        ("fact_job_sessions.csv", ["job_id", "task_id", "annotator_id", "date_key", "total_frames", "total_objects", "active_time_hours", "status"], job_sessions),
        ("fact_annotations.csv", ["annotation_id", "job_id", "frame_idx", "label_id", "shape_type", "bbox_width", "bbox_height", "area_pixels", "frame_area_pct", "size_scale"], annotations_rows),
        ("fact_qa_reviews.csv", ["review_id", "job_id", "reviewer_id", "review_iteration", "review_decision", "reviewed_at"], qa_reviews),
        ("fact_qa_defects.csv", ["defect_id", "review_id", "job_id", "frame_idx", "label_id", "defect_type", "severity", "description", "cvat_deep_link"], qa_defects),
        ("fact_ground_truth_eval.csv", ["eval_id", "job_id", "mean_iou", "precision", "recall", "f1_score"], gt_evals),
        ("fact_edge_cases.csv", ["case_id", "number", "title", "description", "labels", "state", "author", "severity", "task_id", "job_id", "frame", "link_status", "cvat_deep_link", "source_url"], edge_cases),
    ]

    for fname, fnames, r in tables:
        for target_dir in (OUT_DIR, POWERBI_DATA_DIR):
            _write_csv(target_dir / fname, fnames, r)

    print("=== Hoàn tất sinh 12 bảng Star Schema thành công! ===")


if __name__ == "__main__":
    generate_all()
