"""Exporter CSV (WBS 2.5) – xuất 4 file chuẩn hóa vào data/processed/.

Output files:
    batch_progress.csv       – tiến độ batch và vận tốc tổng hợp
    qa_metrics.csv           – chỉ số chất lượng QA/QC toàn task
    annotator_segments.csv   – phân khúc từng annotator
    edge_cases.csv           – danh sách ca khó kèm deep link

Encoding: utf-8-sig (BOM) để Power BI đọc đúng tiếng Việt.
Làm tròn: 4 chữ số thập phân ở tầng export (không làm tròn trong processors).
Tên cột bám Data Contract v1 – KHÔNG thay đổi mà không có sự chấp thuận của Lead.

Chạy từ thư mục gốc repo (metrics-etl-processors/):
    python -m src.exporters.csv_exporter <snapshot_dir> [--output-dir data/processed]
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..adapters.cvat_snapshot import load_snapshot
from ..adapters.snapshot_metrics import _default_as_of
from ..processors import geometry, quality, velocity
from ..processors.annotator_stats import build_annotator_stats
from ..processors.config import THRESHOLDS
from ..processors.segmentation import (
    QualityRiskFlag,
    classify_annotator,
    classify_quality_risk,
)

logger = logging.getLogger(__name__)

ENCODING = "utf-8-sig"   # BOM cho Power BI
ROUND_DP = 4             # chữ số thập phân khi export

BATCH_PROGRESS_FIELDS = [
    "snapshot_dir", "as_of", "task_id", "task_name", "total_frames_target",
    "completed_frames_proxy", "backlog_frames", "progress_pct_proxy",
    "annotation_job_count", "completed_annotation_job_count", "completed_annotation_job_percent",
    "jobs_status_completed", "jobs_status_annotation", "jobs_status_validation", "jobs_status_other",
    "total_active_hours", "avg_velocity_fps", "avg_time_per_frame_minutes",
    "projected_completion_date", "note",
]

QA_METRICS_FIELDS = [
    "snapshot_dir", "as_of", "task_id", "total_reviews", "total_defects",
    "first_time_pass_rate", "rejection_rate", "defect_density_per_100_frames",
    "avg_defects_per_job", "defect_box_displacement", "defect_wrong_class",
    "defect_missing_object", "defect_wrong_attr", "avg_miou", "avg_f1", "qa_score",
]

ANNOTATOR_SEGMENTS_FIELDS = [
    "snapshot_dir", "as_of", "annotator_id", "full_name",
    "total_jobs_completed", "total_frames_completed", "total_objects",
    "total_active_hours", "avg_frames_per_hour", "avg_velocity_fps",
    "tenure_days", "active_hours_7d", "first_time_pass_rate", "rejection_rate",
    "mean_f1_score", "velocity_segment", "quality_risk_flag", "final_segment",
    "final_segment_short", "priority", "at_risk", "action",
]

EDGE_CASES_FIELDS = [
    "snapshot_dir", "as_of", "number", "title", "description", "labels",
    "source_url", "state", "author", "updated_at",
    "task_id", "job_id", "frame", "link_status", "cvat_deep_link",
]


def _r(value: Optional[float], dp: int = ROUND_DP) -> Optional[float]:
    """Làm tròn giá trị float; giữ None."""
    if value is None:
        return None
    return round(value, dp)


def _pct(ratio: Optional[float]) -> Optional[float]:
    """Chuyển tỷ số 0–1 sang % 0–100."""
    if ratio is None:
        return None
    return _r(ratio * 100, 2)


# ---------------------------------------------------------------------------
# 1. batch_progress.csv
# ---------------------------------------------------------------------------

def export_batch_progress(snap_dir: Path, output_dir: Path, as_of: date) -> Path:
    """Xuất tiến độ batch và vận tốc tổng hợp.

    Cột xuất (bám schema report_data.json của Duy):
        snapshot_dir, as_of, task_id, task_name, total_frames_target,
        completed_frames (proxy: tổng frames của job status=completed – xem note),
        backlog_frames, progress_pct,
        annotation_job_count, completed_annotation_job_count, completed_annotation_job_percent,
        jobs_by_stage_annotation, jobs_by_stage_validation, jobs_by_stage_acceptance,
        jobs_by_state_completed, jobs_by_state_in_progress, jobs_by_state_new, jobs_by_state_rejected,
        total_active_hours (null khi snapshot không có log analytics – xem mục 6.1 notes Duy),
        avg_velocity_fps, avg_time_per_frame_minutes, projected_completion_date

    Lưu ý (theo notes Duy mục 5.1 + 8):
    - completed_frames ở đây là proxy (tổng frame_count của job status=completed);
      KHÔNG phải % frame QA pass. Duy xác nhận giá trị thực = null vì chưa suy ra được.
    - total_active_hours = null khi snapshot thiếu CVAT Analytics (không trả 0 để tránh nhầm).
    - updated_date KHÔNG được dùng mặc định là ngày nộp job.
    """
    snap = load_snapshot(snap_dir)
    jobs = snap.jobs

    completed_f = velocity.total_completed_frames(jobs)
    target_f    = snap.total_frames
    backlog     = velocity.backlog_frames(completed_f, target_f)
    progress    = velocity.progress_ratio(completed_f, target_f)
    hours       = velocity.total_active_hours(jobs)
    # null khi không có dữ liệu analytics (hours == 0 do snapshot không có log)
    hours_out   = _r(hours) if hours > 0 else None
    v_fps_h     = velocity.velocity_frames_per_hour(jobs)
    v_fps       = _r(v_fps_h * THRESHOLDS.frames_per_hour_to_per_minute) if v_fps_h is not None else None
    atpf        = _r(velocity.avg_time_per_frame_minutes(jobs))
    per_day     = velocity.completed_frames_per_day(jobs, as_of)
    eta         = velocity.projected_completion_date(backlog, per_day, as_of) if backlog is not None else None

    # Phân biệt stage và state theo schema thực tế của Duy (mục 3.2)
    # Job.status trong adapter được ánh xạ từ trường status CVAT
    # (cùng từ vựng annotation/validation/completed – giả định #7)
    # stage và state CVAT là hai chiều độc lập; adapter hiện chỉ giữ status
    by_status: Dict[str, int] = {}
    for j in jobs:
        by_status[j.status] = by_status.get(j.status, 0) + 1

    annotation_jobs = [j for j in jobs if j.status in ("annotation", "validation", "completed")]
    completed_ann   = [j for j in jobs if j.status == "completed"]

    row = {
        "snapshot_dir":                       str(snap_dir),
        "as_of":                              as_of.isoformat(),
        "task_id":                            snap.task_id,
        "task_name":                          snap.task_name,
        "total_frames_target":                target_f,
        # proxy — xem docstring; giá trị null trong report_data.json thực tế
        "completed_frames_proxy":             completed_f,
        "backlog_frames":                     backlog,
        "progress_pct_proxy":                 _pct(progress),
        # Theo report_data.json schema của Duy
        "annotation_job_count":               len(annotation_jobs),
        "completed_annotation_job_count":     len(completed_ann),
        "completed_annotation_job_percent":   _r(
            len(completed_ann) * 100.0 / len(annotation_jobs)
            if annotation_jobs else None, 2
        ),
        # jobs theo status (adapter ánh xạ từ CVAT status field)
        "jobs_status_completed":              by_status.get("completed", 0),
        "jobs_status_annotation":             by_status.get("annotation", 0),
        "jobs_status_validation":             by_status.get("validation", 0),
        "jobs_status_other":                  sum(
            v for k, v in by_status.items()
            if k not in ("completed", "annotation", "validation")
        ),
        # Velocity — null khi thiếu log analytics (KHÔNG xuất 0)
        "total_active_hours":                 hours_out,
        "avg_velocity_fps":                   v_fps,
        "avg_time_per_frame_minutes":         atpf,
        "projected_completion_date":          eta.isoformat() if eta else None,
        "note":                               (
            "completed_frames_proxy: tổng frame_count của job status=completed, "
            "không phải frame QA pass. total_active_hours=null: snapshot thiếu CVAT Analytics log."
        ),
    }

    output_path = output_dir / "batch_progress.csv"
    _write_csv(output_path, [row], fieldnames=BATCH_PROGRESS_FIELDS)
    logger.info("Đã ghi %s", output_path)
    return output_path


# ---------------------------------------------------------------------------
# 2. qa_metrics.csv
# ---------------------------------------------------------------------------

def export_qa_metrics(snap_dir: Path, output_dir: Path, as_of: date) -> Path:
    """Xuất chỉ số chất lượng QA/QC tổng hợp toàn task.

    qa_score chưa định nghĩa trong tài liệu → để None (ghi rõ trong README).
    """
    snap = load_snapshot(snap_dir)
    jobs = snap.jobs

    completed_f  = velocity.total_completed_frames(jobs)
    n_defects    = quality.total_defects(snap.defects)
    ftpr         = quality.first_time_pass_rate(snap.reviews) if snap.reviews else None
    rr           = quality.rejection_rate(snap.reviews) if snap.reviews else None
    dd           = quality.defect_density_per_100_frames(n_defects, completed_f) if snap.reviews else None
    adpj         = quality.avg_defects_per_job(n_defects, snap.reviews) if snap.reviews else None
    miou         = quality.avg_miou(snap.gt_evals) if snap.gt_evals else None
    f1           = quality.avg_f1(snap.gt_evals) if snap.gt_evals else None
    dtc          = quality.defect_type_counts(snap.defects) if snap.reviews else None

    row: Dict[str, Any] = {
        "snapshot_dir":                  str(snap_dir),
        "as_of":                         as_of.isoformat(),
        "task_id":                       snap.task_id,
        "total_reviews":                 len(snap.reviews),
        "total_defects":                 n_defects if snap.reviews else None,
        "first_time_pass_rate":          _r(ftpr),
        "rejection_rate":                _r(rr),
        "defect_density_per_100_frames": _r(dd),
        "avg_defects_per_job":           _r(adpj),
        "defect_box_displacement":       dtc.get("box_displacement") if dtc else None,
        "defect_wrong_class":            dtc.get("wrong_class") if dtc else None,
        "defect_missing_object":         dtc.get("missing_object") if dtc else None,
        "defect_wrong_attr":             dtc.get("wrong_attr") if dtc else None,
        "avg_miou":                      _r(miou),
        "avg_f1":                        _r(f1),
        "qa_score":                      None,   # chưa có định nghĩa trong tài liệu
    }

    output_path = output_dir / "qa_metrics.csv"
    _write_csv(output_path, [row], fieldnames=QA_METRICS_FIELDS)
    logger.info("Đã ghi %s", output_path)
    return output_path


# ---------------------------------------------------------------------------
# 3. annotator_segments.csv
# ---------------------------------------------------------------------------

def export_annotator_segments(snap_dir: Path, output_dir: Path, as_of: date) -> Path:
    """Xuất phân khúc và chỉ số từng annotator."""
    snap = load_snapshot(snap_dir)
    output_path = output_dir / "annotator_segments.csv"

    if not snap.annotators:
        logger.warning("Snapshot không có annotator nào (assignee = null); annotator_segments.csv sẽ rỗng")
        _write_csv(output_path, [], fieldnames=ANNOTATOR_SEGMENTS_FIELDS)
        return output_path

    stats_list = build_annotator_stats(
        snap.annotators, snap.jobs, snap.reviews, snap.gt_evals, as_of=as_of
    )
    rows: List[Dict[str, Any]] = []
    for stats in stats_list:
        clf = classify_annotator(stats)
        at_risk = (clf.quality_risk_flag == QualityRiskFlag.HIGH_RISK)
        rows.append({
            "snapshot_dir":           str(snap_dir),
            "as_of":                  as_of.isoformat(),
            "annotator_id":           stats.annotator_id,
            "full_name":              stats.full_name,
            "total_jobs_completed":   stats.total_jobs_completed,
            "total_frames_completed": stats.total_frames_completed,
            "total_objects":          stats.total_objects,
            "total_active_hours":     _r(stats.total_active_hours),
            "avg_frames_per_hour":    _r(stats.avg_frames_per_hour),
            # frames/phút (giả định #6)
            "avg_velocity_fps":       _r(
                stats.avg_frames_per_hour * THRESHOLDS.frames_per_hour_to_per_minute
                if stats.avg_frames_per_hour is not None else None
            ),
            "tenure_days":            stats.tenure_days,
            "active_hours_7d":        _r(stats.active_hours_7d),
            "first_time_pass_rate":   _r(stats.first_time_pass_rate),
            "rejection_rate":         _r(stats.rejection_rate),
            "mean_f1_score":          _r(stats.mean_f1_score),
            "velocity_segment":       clf.velocity_segment.value,
            "quality_risk_flag":      clf.quality_risk_flag.value,
            "final_segment":          clf.final_segment.value,
            "final_segment_short":    clf.final_segment.short_label,
            "priority":               clf.final_segment.priority,
            "at_risk":                int(at_risk),
            "action":                 clf.final_segment.action,
        })

    _write_csv(output_path, rows, fieldnames=ANNOTATOR_SEGMENTS_FIELDS)
    logger.info("Đã ghi %s (%d dòng)", output_path, len(rows))
    return output_path


# ---------------------------------------------------------------------------
# 4. edge_cases.csv
# ---------------------------------------------------------------------------

def export_edge_cases(snap_dir: Path, output_dir: Path, as_of: date) -> Path:
    """Xuất danh sách ca khó từ report_data.json (GitHub issues label ca-kho).

    Theo notes của Duy (mục 5.3 + 5.5):
    - Ca khó đến từ GitHub issues (label 'ca-kho') đã được xác minh liên kết CVAT.
    - Nguồn là report_data.json → edge_cases.items[] (KHÔNG phải CVAT defects).
    - frame hiện luôn null; cvat_job_url chỉ có khi link_status = 'verified'.
    - Snapshot không chứa CVAT issues/defects nội bộ ở dạng có thể dùng.

    Cột xuất bám schema report_data.json:
        snapshot_dir, as_of, number, title, description, labels, source_url (GitHub),
        state, author, updated_at,
        task_id, job_id, frame, link_status, cvat_deep_link (deep link CVAT)
    """
    import json as _json

    rows: List[Dict[str, Any]] = []

    # Đọc report_data.json nếu tồn tại (tại snap_dir hoặc thư mục cha của snapshot)
    snap_p = Path(snap_dir)
    report_data_path = snap_p / "report_data.json"
    if not report_data_path.exists() and (snap_p.parent / "report_data.json").exists():
        report_data_path = snap_p.parent / "report_data.json"

    if report_data_path.exists():
        report_data = _json.loads(report_data_path.read_text(encoding="utf-8"))
        items = report_data.get("edge_cases", {}).get("items", [])
        for item in items:
            rows.append({
                "snapshot_dir":   str(snap_dir),
                "as_of":          as_of.isoformat(),
                # Schema theo report_data.json của Duy (mục 5.3)
                "number":         item.get("number"),
                "title":          item.get("title"),
                "description":    (item.get("description") or "").replace("\n", " "),
                "labels":         "|".join(item.get("labels", [])),
                "source_url":     item.get("source_url"),      # URL GitHub issue
                "state":          item.get("state"),
                "author":         item.get("author"),
                "updated_at":     item.get("updated_at"),
                "task_id":        item.get("task_id"),
                "job_id":         item.get("job_id"),
                # frame hiện luôn null (chưa đọc/xác minh tự động – mục 5.3 notes)
                "frame":          item.get("frame"),
                "link_status":    item.get("link_status"),
                # Deep link CVAT — chỉ có khi link_status = 'verified'
                "cvat_deep_link": item.get("cvat_job_url"),
            })
        logger.info("Đọc %d ca khó từ report_data.json (%s)", len(rows), report_data_path)
    else:
        logger.warning(
            "Không tìm thấy report_data.json tại %s; edge_cases.csv sẽ rỗng. "
            "Ca khó đến từ GitHub issues (label 'ca-kho'), không phải CVAT defects nội bộ.",
            snap_dir,
        )

    output_path = output_dir / "edge_cases.csv"
    _write_csv(output_path, rows, fieldnames=EDGE_CASES_FIELDS)
    logger.info("Đã ghi %s (%d dòng)", output_path, len(rows))
    return output_path


# ---------------------------------------------------------------------------
# CSV writer helper
# ---------------------------------------------------------------------------

def _write_csv(
    path: Path,
    rows: List[Dict[str, Any]],
    fieldnames: Optional[List[str]] = None,
) -> None:
    """Ghi danh sách dict ra CSV utf-8-sig. Nếu rows rỗng và có fieldnames, vẫn ghi header."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        if fieldnames:
            with open(path, "w", newline="", encoding=ENCODING) as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
        else:
            path.write_text("", encoding=ENCODING)
        return
    fields = fieldnames if fieldnames is not None else list(rows[0].keys())
    with open(path, "w", newline="", encoding=ENCODING) as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def export_all(snap_dir: Path, output_dir: Path, as_of: date) -> Dict[str, Path]:
    """Xuất cả 4 file CSV và trả về dict tên → path."""
    results = {}
    results["batch_progress"]     = export_batch_progress(snap_dir, output_dir, as_of)
    results["qa_metrics"]         = export_qa_metrics(snap_dir, output_dir, as_of)
    results["annotator_segments"] = export_annotator_segments(snap_dir, output_dir, as_of)
    results["edge_cases"]         = export_edge_cases(snap_dir, output_dir, as_of)
    return results


def main(argv: Optional[list] = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("snapshot", type=Path, help="Thư mục snapshot chứa cvat.json")
    parser.add_argument("--output-dir", type=Path, default=Path("data/processed"),
                        help="Thư mục đầu ra CSV (mặc định: data/processed)")
    parser.add_argument("--as-of", type=date.fromisoformat, default=None,
                        help="Ngày tính (YYYY-MM-DD)")
    args = parser.parse_args(argv)

    as_of = args.as_of or _default_as_of(args.snapshot)
    results = export_all(args.snapshot, args.output_dir, as_of)
    print(json.dumps({k: str(v) for k, v in results.items()}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
