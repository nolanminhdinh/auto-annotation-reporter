"""CVAT REST API Extractor for Tasks, Jobs, Annotations, and Quality Reports."""
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import requests

from .base_client import BaseClient


class CVATExtractor:
    """Extractor for CVAT REST API v2."""

    def __init__(self, host: str, token: str, org: Optional[str] = None):
        self.host = host.rstrip("/")
        # Personal access token authentication.
        self.client = BaseClient(
            base_url=self.host,
            token=token,
            auth_prefix="Bearer",
            org=org,
        )

    def build_deep_link(
        self,
        task_id: int,
        job_id: int,
        frame: Optional[int] = None,
    ) -> str:
        """Construct standard CVAT Deep Link directly pointing to job and optional frame."""
        url = f"{self.host}/tasks/{task_id}/jobs/{job_id}"
        if frame is not None:
            url += f"?frame={frame}"
        return url

    def get_task(self, task_id: int) -> Dict[str, Any]:
        """Fetch general task details."""
        return self.client.get(f"api/tasks/{task_id}").json()

    def get_jobs(self, task_id: int) -> List[Dict[str, Any]]:
        """Fetch all jobs belonging to a task."""
        return self.client.listing("api/jobs", {"task_id": task_id, "page_size": 100})

    def get_labels(self, task_id: int) -> List[Dict[str, Any]]:
        """Fetch class taxonomy / labels for a task."""
        return self.client.listing("api/labels", {"task_id": task_id, "page_size": 100})

    def get_issues(self, task_id: int) -> List[Dict[str, Any]]:
        """Fetch all annotation issues/disputes logged in CVAT for this task."""
        return self.client.listing("api/issues", {"task_id": task_id, "page_size": 100})

    def get_comments(self, issue_id: int) -> List[Dict[str, Any]]:
        """Fetch discussion comments for an issue."""
        return self.client.listing("api/comments", {"issue_id": issue_id, "page_size": 100})

    def get_job_annotations(self, job_id: int) -> Dict[str, Any]:
        """Fetch shapes, tracks, and tags for a specific job."""
        data = self.client.get(f"api/jobs/{job_id}/annotations/").json()
        if not isinstance(data, dict) or any(
            not isinstance(data.get(k, []), list) for k in ("tags", "shapes", "tracks")
        ):
            raise ValueError(f"Invalid CVAT annotation payload format for job {job_id}")
        return data

    def get_quality_reports(self, task_id: int) -> Optional[Dict[str, Any]]:
        """Latest task-level report metadata; job reports are not task aggregates."""
        try:
            reports = self.client.listing('api/quality/reports', {'task_id': task_id, 'page_size': 100})
            candidates = [r for r in reports if r.get('job_id') is None and r.get('task_id', task_id) == task_id]
            return max(candidates, key=self._report_order) if candidates else None
        except (requests.RequestException, RuntimeError, ValueError, TypeError, KeyError):
            return None

    @staticmethod
    def _report_order(report):
        value = report.get('created_date')
        try:
            stamp = datetime.fromisoformat(value.replace('Z', '+00:00')) if value else datetime.min.replace(tzinfo=timezone.utc)
            if stamp.tzinfo is None: stamp = stamp.replace(tzinfo=timezone.utc)
        except (ValueError, AttributeError):
            stamp = datetime.min.replace(tzinfo=timezone.utc)
        try:
            report_id = int(report.get('id', 0))
        except (ValueError, TypeError):
            report_id = 0
        return stamp, report_id

    def get_quality_bundle(self, task_id, job_ids):
        """Read report/data with explicit availability; preserve payloads for mapping.

        Raw report contents are not relabelled as reviewer history or synthetic GT.
        """
        try:
            reports = self.client.listing('api/quality/reports', {'task_id': task_id, 'page_size': 100})
        except (requests.RequestException, RuntimeError, ValueError) as error:
            return {'status': 'failed', 'error_type': type(error).__name__, 'reports': []}
        latest = {}
        for report in reports:
            if report.get('task_id', task_id) != task_id: continue
            jid = report.get('job_id')
            if jid is not None and jid not in job_ids: continue
            if jid not in latest or self._report_order(report) > self._report_order(latest[jid]): latest[jid] = report
        records = []
        for report in latest.values():
            try:
                data = self.client.get(f'api/quality/reports/{int(report["id"])}/data', {'format': 'json'}).json()
                if not isinstance(data, dict): raise ValueError('Expected quality report JSON object')
                records.append({'status': 'success', 'metadata': report, 'data': data})
            except (requests.RequestException, RuntimeError, ValueError, KeyError, TypeError) as error:
                records.append({'status': 'failed', 'metadata': report, 'error_type': type(error).__name__})
        status = 'unavailable' if not records else ('partial' if any(r['status'] != 'success' for r in records) else 'available')
        return {'status': status, 'reports': records, 'latest_task_report': latest.get(None)}

    def get_job_data_meta(self, job_id):
        data = self.client.get(f'api/jobs/{job_id}/data/meta').json()
        if not isinstance(data, dict) or not isinstance(data.get('frames'), list):
            raise ValueError('Invalid media metadata')
        return data

    def extract_snapshot(self, task_id: int) -> Dict[str, Any]:
        """Extract a complete snapshot from CVAT including tasks, jobs, annotations, and issues."""
        task = self.get_task(task_id)
        jobs = self.get_jobs(task_id)
        labels = self.get_labels(task_id)
        issues = self.get_issues(task_id)

        comments: List[Dict[str, Any]] = []
        comment_failures = []
        for issue in issues:
            if "id" in issue:
                try:
                    comments.extend(self.get_comments(issue["id"]))
                except (requests.RequestException, RuntimeError, ValueError) as error:
                    comment_failures.append({'issue_id': issue['id'], 'error_type': type(error).__name__})

        annotations: List[Dict[str, Any]] = []
        for job in jobs:
            job_id = job["id"]
            try:
                data = self.get_job_annotations(job_id)
                annotations.append({"job_id": job_id, "status": "success", "data": data})
            except (requests.RequestException, RuntimeError, ValueError) as err:
                row: Dict[str, Any] = {
                    "job_id": job_id,
                    "status": "failed",
                    "error_type": type(err).__name__,
                }
                if isinstance(err, RuntimeError):
                    row["error"] = str(err)
                annotations.append(row)

        annotation_ids = {j['id'] for j in jobs if j.get('type', 'annotation') == 'annotation'}
        quality_bundle = self.get_quality_bundle(task_id, annotation_ids)
        media_metadata = []
        for job_id in sorted(annotation_ids):
            try:
                media_metadata.append({'job_id': job_id, 'status': 'success', 'data': self.get_job_data_meta(job_id)})
            except (requests.RequestException, RuntimeError, ValueError) as error:
                media_metadata.append({'job_id': job_id, 'status': 'failed', 'error_type': type(error).__name__})

        return {
            "task": task,
            "jobs": jobs,
            "labels": labels,
            "issues": issues,
            "comments": comments,
            "annotations": annotations,
            "quality_report": quality_bundle.get('latest_task_report'),
            'quality_reports_data': quality_bundle,
            'media_metadata': media_metadata,
            'optional_sources': {'comments': {'status': 'partial' if comment_failures else 'available', 'failures': comment_failures}},
        }

    @staticmethod
    def summarize_annotations(
        annotations_records: Optional[List[Dict[str, Any]]],
        labels_records: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Summarize raw annotations records without inferring ungrounded metrics."""
        if annotations_records is None:
            return {
                "status": "unavailable",
                "reason": "Snapshot chưa thu thập annotations.",
                "jobs": [],
                "totals": None,
                "by_label": [],
            }

        labels_map = {
            label["id"]: label.get("name", f"ID {label['id']}")
            for label in (labels_records or [])
            if "id" in label
        }

        totals = {"shapes": 0, "tracks": 0, "tags": 0, "track_shape_records": 0}
        by_label: Dict[int, Dict[str, Any]] = {}
        jobs_summary: List[Dict[str, Any]] = []
        has_failed = False

        for record in annotations_records:
            job_id = record.get("job_id")
            if record.get("status") != "success" or "data" not in record:
                has_failed = True
                jobs_summary.append({"job_id": job_id, "status": "failed", "counts": None})
                continue

            data = record["data"]
            counts = {key: len(data.get(key, [])) for key in ("shapes", "tracks", "tags")}
            counts["track_shape_records"] = sum(
                len(track.get("shapes", [])) for track in data.get("tracks", [])
            )

            for key in totals:
                totals[key] += counts[key]

            for kind in ("shapes", "tracks", "tags"):
                for obj in data.get(kind, []):
                    label_id = obj.get("label_id")
                    if label_id is not None:
                        if label_id not in by_label:
                            by_label[label_id] = {
                                "label_id": label_id,
                                "label_name": labels_map.get(label_id, f"ID {label_id}"),
                                "shapes": 0,
                                "tracks": 0,
                                "tags": 0,
                            }
                        by_label[label_id][kind] += 1

            jobs_summary.append({"job_id": job_id, "status": "success", "counts": counts})

        return {
            "status": "partial" if has_failed else "available",
            "jobs": jobs_summary,
            "totals": totals,
            "by_label": list(by_label.values()),
            "note": (
                "Đếm bản ghi API theo job, không nội suy track. "
                "Không phải số frame hoàn thành hoặc số đối tượng duy nhất toàn task."
            ),
        }
