"""Chạy bộ tính toán chỉ số trên một snapshot và trả về kết quả kèm lý do chỉ số nào chưa tính được.

Dùng từ dòng lệnh (chạy ở thư mục gốc repo):

    python -m src.adapters.snapshot_metrics <thư-mục-snapshot> [--frame-size 960x540] [--as-of 2026-10-09]

Nguyên tắc: chỉ số thiếu nguồn dữ liệu được để None kèm lý do trong `not_computable`,
không bao giờ thay bằng 0 để tránh tạo ra số liệu giả.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

from ..processors import geometry, quality, segmentation, velocity
from ..processors.annotator_stats import build_annotator_stats
from .cvat_snapshot import FrameSize, SnapshotData, load_snapshot


def summarize(snap: SnapshotData, as_of: date) -> dict[str, Any]:
    jobs = snap.jobs
    completed_frames = velocity.total_completed_frames(jobs)
    hours = velocity.total_active_hours(jobs)
    not_computable: dict[str, str] = {}

    def need(condition: bool, metrics: list[str], reason: str) -> bool:
        """Đánh dấu các chỉ số không tính được khi thiếu nguồn; trả True nếu đủ nguồn."""
        if not condition:
            for m in metrics:
                not_computable[m] = reason
        return condition

    # --- Tiến độ ---
    target = snap.total_frames
    progress = {
        "completed_frames": completed_frames,
        "target_frames": target,
        "progress_ratio": velocity.progress_ratio(completed_frames, target) if target else None,
        "backlog_frames": velocity.backlog_frames(completed_frames, target) if target else None,
        "jobs_total": len(jobs),
        "jobs_by_status": {s: sum(1 for j in jobs if j.status == s) for s in sorted({j.status for j in jobs})},
    }

    # --- Vận tốc ---
    has_hours = need(
        hours > 0,
        ["velocity_frames_per_hour", "velocity_objects_per_hour",
         "avg_time_per_frame_minutes", "avg_time_per_object_seconds"],
        "Snapshot không có log thời gian làm việc (active_time_hours), cần CVAT analytics/events",
    )
    per_day = velocity.completed_frames_per_day(jobs, as_of)
    vel = {
        "total_active_hours": hours if has_hours else None,
        "velocity_frames_per_hour": velocity.velocity_frames_per_hour(jobs) if has_hours else None,
        "velocity_objects_per_hour": velocity.velocity_objects_per_hour(jobs) if has_hours else None,
        "avg_time_per_frame_minutes": velocity.avg_time_per_frame_minutes(jobs) if has_hours else None,
        "avg_time_per_object_seconds": velocity.avg_time_per_object_seconds(jobs) if has_hours else None,
        "completed_frames_per_day": per_day,
        "projected_completion_date": None,
    }
    if target and per_day > 0:
        eta = velocity.projected_completion_date(progress["backlog_frames"], per_day, as_of)
        vel["projected_completion_date"] = eta.isoformat() if eta else None
    else:
        not_computable["projected_completion_date"] = (
            "Chưa có frame completed trong cửa sổ ngày gần nhất nên không ước tính được vận tốc ngày"
            if target else "Không biết tổng số frame của task"
        )

    # --- Chất lượng ---
    has_reviews = need(
        bool(snap.reviews),
        ["first_time_pass_rate", "rejection_rate", "total_defects", "defect_density_per_100_frames",
         "avg_defects_per_job", "defect_type_counts"],
        "Snapshot không có lịch sử review/lỗi; không kết luận được (không phải bằng 0)",
    )
    has_gt = need(bool(snap.gt_evals), ["avg_miou", "avg_f1"],
                  "Snapshot không có kết quả Ground Truth (quality reports)")
    n_defects = quality.total_defects(snap.defects)
    qual = {
        "first_time_pass_rate": quality.first_time_pass_rate(snap.reviews) if has_reviews else None,
        "rejection_rate": quality.rejection_rate(snap.reviews) if has_reviews else None,
        "total_defects": n_defects if has_reviews else None,
        "defect_density_per_100_frames": quality.defect_density_per_100_frames(n_defects, completed_frames) if has_reviews else None,
        "avg_defects_per_job": quality.avg_defects_per_job(n_defects, snap.reviews) if has_reviews else None,
        "defect_type_counts": quality.defect_type_counts(snap.defects) if has_reviews else None,
        "avg_miou": quality.avg_miou(snap.gt_evals) if has_gt else None,
        "avg_f1": quality.avg_f1(snap.gt_evals) if has_gt else None,
    }

    # --- Hình học (trên các hộp được vẽ: shape đơn + keyframe không outside) ---
    need(snap.frame_size is not None, ["avg_area_frame_pct"],
         "Snapshot không có kích thước ảnh; truyền --frame-size RỘNGxCAO nếu biết")
    geo = {
        "boxes_measured": len(snap.geometries),
        "avg_object_area_pixels": geometry.avg_object_area(snap.geometries),
        "avg_area_frame_pct": geometry.avg_area_frame_pct(snap.geometries),
        "pct_small_objects": geometry.pct_small_objects(snap.geometries),
        "size_scale_counts": geometry.size_scale_counts(snap.geometries),
    }

    # --- Phân khúc nhân sự ---
    seg: list[dict[str, Any]] = []
    if need(bool(snap.annotators), ["segmentation"], "Không có job nào được giao cho annotator (assignee = null)"):
        stats = build_annotator_stats(snap.annotators, jobs, snap.reviews, snap.gt_evals, as_of=as_of)
        for r in segmentation.segment_annotators(stats):
            seg.append({
                "annotator_id": r.annotator_id,
                "velocity_segment": r.velocity_segment.value,
                "quality_risk_flag": r.quality_risk_flag.value,
                "final_segment": r.final_segment.value,
            })

    return {
        "snapshot": snap.snapshot_dir,
        "as_of": as_of.isoformat(),
        "task": {"id": snap.task_id, "name": snap.task_name},
        "input_counts": snap.counts,
        "data_issues": {
            "failed_annotation_jobs": snap.failed_annotation_jobs,
            "malformed_geometry_records": snap.malformed_records,
        },
        "progress": progress,
        "velocity": vel,
        "quality": qual,
        "geometry": geo,
        "segmentation": seg,
        "not_computable": not_computable,
    }


def _parse_frame_size(text: str) -> FrameSize:
    width, _, height = text.lower().partition("x")
    return float(width), float(height)


def _default_as_of(folder: Path) -> date:
    """Mặc định lấy ngày thu thập trong manifest để chỉ số gắn với thời điểm snapshot."""
    manifest = folder / "manifest.json"
    if manifest.exists():
        started = json.loads(manifest.read_text(encoding="utf-8")).get("started_at")
        if started:
            return datetime.fromisoformat(started.replace("Z", "+00:00")).date()
    return date.today()


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("snapshot", type=Path, help="Thư mục snapshot chứa cvat.json")
    parser.add_argument("--frame-size", type=_parse_frame_size, default=None, metavar="RxC",
                        help="Kích thước ảnh, ví dụ 960x540 (không có trong snapshot)")
    parser.add_argument("--as-of", type=date.fromisoformat, default=None, help="Ngày tính (YYYY-MM-DD)")
    args = parser.parse_args(argv)

    snap = load_snapshot(args.snapshot, args.frame_size)
    result = summarize(snap, args.as_of or _default_as_of(args.snapshot))
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
