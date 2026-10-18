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
        if type(task_id) is not int or task_id<=0: raise ValueError('task_id must be a positive integer')
        task=self.client.get(f"api/tasks/{task_id}").json()
        if not isinstance(task,dict) or task.get('id')!=task_id: raise ValueError('CVAT returned an unexpected task')
        return task

    def get_jobs(self, task_id: int) -> List[Dict[str, Any]]:
        """Fetch all jobs belonging to a task."""
        jobs=self.client.listing("api/jobs", {"task_id": task_id, "page_size": 100})
        seen=set()
        for job in jobs:
            jid=job.get('id')
            if type(jid) is not int or jid<=0 or jid in seen or job.get('task_id')!=task_id:
                raise ValueError('CVAT returned duplicate, invalid or out-of-scope jobs')
            seen.add(jid)
        return jobs

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
            not isinstance(data.get(k), list) or any(not isinstance(r,dict) for r in data[k]) for k in ("tags", "shapes", "tracks")
        ):
            raise ValueError(f"Invalid CVAT annotation payload format for job {job_id}")
        if any(not isinstance(t.get('shapes'),list) or any(not isinstance(s,dict) for s in t['shapes']) for t in data['tracks']):
            raise ValueError(f'Invalid track shape records for job {job_id}')
        return data

    def get_quality_reports(self, task_id: int) -> Optional[Dict[str, Any]]:
        """Latest task-level report metadata; job reports are not task aggregates."""
        try:
            reports = self.client.listing('api/quality/reports', {'task_id': task_id, 'target':'task', 'page_size': 100})
            candidates = [r for r in reports if r.get('job_id') is None and r.get('task_id') == task_id and r.get('target','task')=='task']
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
        reports=[]
        sources={}
        for target in ('task','job'):
            try:
                result=self.client.listing('api/quality/reports', {'task_id':task_id,'target':target,'page_size':100})
                reports.extend(result)
                sources[target]={'status':'success','count':len(result)}
            except (requests.RequestException,RuntimeError,ValueError) as error:
                sources[target]=self._failure(error)
        latest = {}
        for report in reports:
            jid = report.get('job_id')
            if report.get('task_id') not in (None,task_id): continue
            if jid is None and (report.get('task_id')!=task_id or report.get('target','task')!='task'): continue
            if jid is not None and jid not in job_ids: continue
            if jid not in latest or self._report_order(report) > self._report_order(latest[jid]): latest[jid] = report
        records = []
        for report in latest.values():
            try:
                data = self.client.get(f'api/quality/reports/{int(report["id"])}/data', {'format': 'json'}).json()
                if not isinstance(data, dict): raise ValueError('Expected quality report JSON object')
                records.append({'status': 'success', 'metadata': report, 'data': data})
            except (requests.RequestException, RuntimeError, ValueError, KeyError, TypeError) as error:
                records.append({**self._failure(error), 'metadata': report})
        list_failed=any(s['status']=='failed' for s in sources.values())
        status=('failed' if all(s['status']=='failed' for s in sources.values()) else
                'partial' if list_failed or any(r['status']!='success' for r in records) else
                'available' if records else 'unavailable')
        return {'status': status, 'reports': records, 'list_sources':sources,'latest_task_report': latest.get(None)}

    @staticmethod
    def _failure(error):
        result={'status':'failed','error_type':type(error).__name__}
        if isinstance(getattr(error,'status_code',None),int): result['http_status']=error.status_code
        return result

    def close(self):
        self.client.close()

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
        try:
            issues = self.get_issues(task_id)
            issue_source={'status':'available'}
        except (requests.RequestException,RuntimeError,ValueError) as error:
            issues=[]
            issue_source=self._failure(error)

        comments: List[Dict[str, Any]] = []
        comment_failures = []
        for issue in issues:
            if "id" in issue:
                try:
                    comments.extend(self.get_comments(issue["id"]))
                except (requests.RequestException, RuntimeError, ValueError) as error:
                    comment_failures.append({'issue_id': issue['id'], **self._failure(error)})

        annotations: List[Dict[str, Any]] = []
        for job in jobs:
            job_id = job["id"]
            try:
                data = self.get_job_annotations(job_id)
                annotations.append({"job_id": job_id, "status": "success", "data": data})
            except (requests.RequestException, RuntimeError, ValueError) as err:
                row: Dict[str, Any] = {'job_id':job_id,**self._failure(err)}
                annotations.append(row)

        annotation_ids = {j['id'] for j in jobs if j.get('type', 'annotation') == 'annotation'}
        quality_bundle = self.get_quality_bundle(task_id, annotation_ids)
        media_metadata = []
        for job_id in sorted(annotation_ids):
            try:
                media_metadata.append({'job_id': job_id, 'status': 'success', 'data': self.get_job_data_meta(job_id)})
            except (requests.RequestException, RuntimeError, ValueError) as error:
                media_metadata.append({'job_id': job_id, **self._failure(error)})

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
            'optional_sources': {
                'issues':issue_source,
                'comments': {'status': 'unavailable' if issue_source['status']=='failed' else 'partial' if comment_failures else 'available', 'failures': comment_failures},
                'media_metadata': {'status':'partial' if any(r['status']=='failed' for r in media_metadata) else 'available'},
            },
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
