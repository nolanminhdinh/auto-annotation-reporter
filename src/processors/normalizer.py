"""Data Normalization Engine aligning with Data Contract v1."""
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.extractors.cvat_extractor import CVATExtractor


def normalize_snapshot(
    manifest: Dict[str, Any],
    cvat_data: Optional[Dict[str, Any]],
    github_data: Optional[Dict[str, Any]],
    links_data: Optional[List[Dict[str, Any]]],
    snapshot_dir: Path,
    session_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Transform raw CVAT and GitHub snapshot payloads into standardized report_data dict.
    Strictly follows Data Contract v1 schema.
    """
    task = (cvat_data or {}).get("task", {})
    jobs = (cvat_data or {}).get("jobs", [])
    labels = (cvat_data or {}).get("labels", [])
    scope = manifest.get("scope", {})
    host = scope.get("cvat_host", "https://app.cvat.ai").rstrip("/")
    warnings: List[str] = []

    # 1. Summarize Annotations
    annotations_summary = CVATExtractor.summarize_annotations(
        (cvat_data or {}).get("annotations"),
        labels,
    )
    if annotations_summary["status"] != "available":
        warnings.append(
            "Annotations chưa đầy đủ; xem annotations.status và từng job trước khi sử dụng thống kê."
        )

    # 2. Source availability warnings
    for source,result in (cvat_data or {}).get('optional_sources',{}).items():
        if result.get('status') in ('failed','partial','unavailable'):
            warnings.append(f'CVAT optional source {source}: {result["status"]}; không coi dữ liệu thiếu là không có bản ghi.')
    if (cvat_data or {}).get('quality_reports_data',{}).get('status') in ('failed','partial'):
        warnings.append('CVAT Quality Reports chưa lấy đầy đủ; xem quality_reports_data và HTTP status trong snapshot.')
    for source in ("cvat", "github"):
        if manifest.get("sources", {}).get(source, {}).get("status") != "success":
            warnings.append(
                f"Nguồn {source} chưa lấy thành công; dữ liệu mục liên quan chưa đầy đủ."
            )

    # 3. Process GitHub Issues & Verified Links
    refs = {row["github_issue"]: row for row in (links_data or []) if "github_issue" in row}
    edge_cases: List[Dict[str, Any]] = []
    open_questions: List[Dict[str, Any]] = []
    blockers: List[Dict[str, Any]] = []
    guideline_updates: List[Dict[str, Any]] = []
    excluded_issues: List[Dict[str, Any]] = []

    for issue in (github_data or {}).get("issues", []):
        if "pull_request" in issue:
            continue

        issue_labels = [lbl.get("name", "") for lbl in issue.get("labels", [])]
        title = issue.get("title", "")
        number = issue.get("number")

        # Exclude test issues
        if title.lower().startswith("[api test]") or "api-test" in issue_labels:
            excluded_issues.append({"number": number, "reason": "api_test"})
            continue

        if issue.get("state") != "open":
            continue

        ref = refs.get(number, {})
        selected_task = scope.get("task_id") or task.get("id")

        # Exclude issues explicitly bound to a different task
        if (
            selected_task is not None
            and ref.get("cvat_task_id") is not None
            and ref["cvat_task_id"] != selected_task
        ):
            excluded_issues.append({
                "number": number,
                "reason": "other_task",
                "task_id": ref["cvat_task_id"],
            })
            continue

        is_verified = (ref.get("status") == "verified")
        task_id = ref.get("cvat_task_id")
        job_id = ref.get("cvat_job_id")
        frame_idx = ref.get("frame")

        # Build Deep Link with Frame support
        cvat_url: Optional[str] = None
        if is_verified and task_id and job_id:
            cvat_url = f"{host}/tasks/{task_id}/jobs/{job_id}"
            if frame_idx is not None:
                cvat_url += f"?frame={frame_idx}"

        item = {
            "number": number,
            "title": title,
            "description": issue.get("body") or "",
            "labels": issue_labels,
            "source_url": issue.get("html_url"),
            "state": issue.get("state"),
            "author": (issue.get("user") or {}).get("login"),
            "updated_at": issue.get("updated_at"),
            "task_id": task_id,
            "job_id": job_id,
            "frame": frame_idx,
            "link_status": ref.get("status", "unlinked"),
            "cvat_job_url": cvat_url,
        }

        if "ca-kho" in issue_labels:
            edge_cases.append(item)
            if not is_verified:
                warnings.append(
                    f"Ca khó #{number} chưa có liên kết CVAT được xác minh."
                )

        if "mentor-question" in issue_labels:
            open_questions.append(item)
            if not is_verified:
                warnings.append(
                    f"Câu hỏi #{number} chưa có tham chiếu task/job được xác minh; có thể là câu hỏi chung của repo."
                )

        if "blocker" in issue_labels:
            blockers.append(item)

        if "guideline-update" in issue_labels:
            guideline_updates.append(item)

    # 4. Normalize Jobs & Batch Progress
    normalized_jobs = [
        {
            "job_id": j["id"],
            "type": j.get("type"),
            "stage": j.get("stage"),
            "state": j.get("state"),
            "assignee": (j.get("assignee") or {}).get("username"),
            "frame_count": j.get("frame_count"),
            "source_url": f"{host}/tasks/{j.get('task_id', task.get('id'))}/jobs/{j['id']}",
        }
        for j in jobs
        if "id" in j
    ]

    annotation_jobs = [j for j in jobs if j.get("type") == "annotation"]
    completed_jobs = sum(j.get("state") == "completed" for j in annotation_jobs)
    job_percent = (
        round(completed_jobs * 100 / len(annotation_jobs), 2)
        if annotation_jobs
        else None
    )

    # 5. Quality Scores Handling
    quality_report = (cvat_data or {}).get("quality_report")
    quality_value=None
    if quality_report:
        quality_value=quality_report.get('mean_iou')
        if quality_value is None: quality_value=quality_report.get('quality_score')
    if quality_report and quality_value is not None:
        scores_data = {
            "status": "available",
            "value": quality_value,
            "method": "CVAT Quality Report (Ground Truth)",
            "source_url": f"{host}/api/quality/reports/{quality_report.get('id', '')}",
            "scored_at": quality_report.get("created_date"),
            "details": quality_report,
        }
    else:
        scores_data = {
            "status": "unavailable",
            "value": None,
            "method": None,
            "source_url": None,
            "scored_at": None,
            "reason": "Chưa thống nhất nguồn điểm và quy tắc chấm QA/QC (hoặc task chưa có Ground Truth).",
        }

    return {
        "schema_version": 1,
        "metadata": {
            "snapshot": str(snapshot_dir),
            "snapshot_started_at": manifest.get("started_at"),
            "snapshot_finished_at": manifest.get("finished_at"),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "mentor_session": session_name,
            "scope": scope,
            "warnings": warnings,
            "excluded_issues": excluded_issues,
        },
        "batch_progress": {
            "status": "available" if cvat_data is not None else "unavailable",
            "task_id": task.get("id"),
            "task_name": task.get("name"),
            "total_frames": task.get("size"),
            "jobs": normalized_jobs,
            "jobs_by_stage": dict(Counter(j.get("stage") or "unknown" for j in jobs)),
            "jobs_by_state": dict(Counter(j.get("state") or "unknown" for j in jobs)),
            "annotation_job_count": len(annotation_jobs),
            "completed_annotation_job_count": completed_jobs,
            "completed_annotation_job_percent": job_percent,
            "completed_frames": None,
            "completion_percent": None,
            "note": "Chưa suy ra tiến độ frame hoặc nghiệm thu từ trạng thái job.",
        },
        "scores": scores_data,
        "annotations": annotations_summary,
        "edge_cases": {
            "status": "available" if github_data is not None else "unavailable",
            "items": edge_cases,
        },
        "open_questions": {
            "status": "available" if github_data is not None else "unavailable",
            "items": open_questions,
        },
        "blockers": {
            "status": "available" if github_data is not None else "unavailable",
            "items": blockers,
        },
        "guideline_updates": {
            "status": "available" if github_data is not None else "unavailable",
            "items": guideline_updates,
        },
    }
