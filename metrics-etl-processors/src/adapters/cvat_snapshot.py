"""Đọc snapshot `cvat.json` (định dạng của Duy: task, jobs, labels, issues, comments, annotations)
và chuyển sang các dataclass của `src/processors`.

Quy ước ánh xạ (có căn cứ từ snapshot thật 20261009T094549598531Z):

* `Job.status`   <- trường `status` của job CVAT (`annotation`/`validation`/`completed`),
                    trùng từ vựng của Data Dictionary. Không dùng `stage`/`state`.
* `Job.total_frames` <- `frame_count`.
* `Job.annotator_id` <- `assignee.id` (None nếu job chưa giao cho ai).
* `Job.date_key` chỉ được điền khi job đã `completed`, lấy từ `updated_date`. `updated_date`
  là lần sửa cuối chứ không phải ngày nộp, nên với job chưa completed để None.
* `Job.active_time_hours` = 0.0: snapshot KHÔNG có log thời gian làm việc.
* Đối tượng "đã vẽ" = shape đơn và keyframe không `outside` của track. Keyframe `outside`
  chỉ là mốc báo đối tượng biến mất, không phải một hộp được vẽ. Track KHÔNG được nội suy.
* Review, lỗi, kết quả Ground Truth: snapshot không có nguồn nên để rỗng.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Iterator, Optional

from ..processors import geometry
from ..processors.geometry import ShapeGeometry
from ..processors.models import Annotator, Defect, GroundTruthEval, Job, Review

logger = logging.getLogger(__name__)

FrameSize = tuple[float, float]


@dataclass
class SnapshotData:
    snapshot_dir: str
    task_id: Optional[int]
    task_name: Optional[str]
    total_frames: Optional[int]
    jobs: list[Job]
    annotators: list[Annotator]
    geometries: list[ShapeGeometry]
    frame_size: Optional[FrameSize]
    counts: dict[str, int]
    failed_annotation_jobs: list[int] = field(default_factory=list)
    malformed_records: int = 0
    # Snapshot hiện không có nguồn cho 3 nhóm dưới đây.
    reviews: list[Review] = field(default_factory=list)
    defects: list[Defect] = field(default_factory=list)
    gt_evals: list[GroundTruthEval] = field(default_factory=list)


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    """Đọc ISO 8601 có hậu tố Z (Python 3.10 chưa hiểu 'Z' trong fromisoformat)."""
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _iter_drawn(data: dict) -> Iterator[tuple[str, dict]]:
    """Mọi hộp thực sự được vẽ: shape đơn và keyframe không `outside` của track."""
    for shape in data.get("shapes", []):
        if not shape.get("outside", False):
            yield "shape", shape
    for track in data.get("tracks", []):
        for keyframe in track.get("shapes", []):
            if not keyframe.get("outside", False):
                yield "keyframe", keyframe


def _count_annotation_payload(data: dict) -> dict[str, int]:
    tracks = data.get("tracks", [])
    keyframe_records = sum(len(t.get("shapes", [])) for t in tracks)
    outside = sum(1 for t in tracks for k in t.get("shapes", []) if k.get("outside", False))
    outside += sum(1 for s in data.get("shapes", []) if s.get("outside", False))
    drawn = sum(1 for _ in _iter_drawn(data))
    return {
        "shapes": len(data.get("shapes", [])),
        "tracks": len(tracks),
        "tags": len(data.get("tags", [])),
        "track_keyframe_records": keyframe_records,   # trùng `track_shape_records` trong report_data.json
        "outside_markers": outside,
        "drawn_objects": drawn,
    }


def _assignee(job: dict) -> Optional[dict]:
    value = job.get("assignee")
    return value if isinstance(value, dict) else None


def load_snapshot(folder: Path | str, frame_size: Optional[FrameSize] = None) -> SnapshotData:
    """Đọc `cvat.json` trong thư mục snapshot.

    `frame_size` là (rộng, cao) pixel của ảnh. Snapshot không chứa thông tin này nên phải được
    truyền vào nếu muốn tính `frame_area_pct`; để None thì chỉ số đó là None.
    """
    folder = Path(folder)
    cvat = json.loads((folder / "cvat.json").read_text(encoding="utf-8"))
    task = cvat.get("task", {})
    width, height = frame_size if frame_size else (0, 0)

    counts = {"shapes": 0, "tracks": 0, "tags": 0, "track_keyframe_records": 0,
              "outside_markers": 0, "drawn_objects": 0}
    drawn_by_job: dict[int, int] = {}
    geometries: list[ShapeGeometry] = []
    failed: list[int] = []
    malformed = 0

    for record in cvat.get("annotations", []):
        job_id = record["job_id"]
        if record.get("status") != "success":
            failed.append(job_id)
            continue
        data = record["data"]
        for key, value in _count_annotation_payload(data).items():
            counts[key] += value
        drawn_by_job[job_id] = sum(1 for _ in _iter_drawn(data))
        for _, shape in _iter_drawn(data):
            try:
                geometries.append(geometry.measure_shape(shape["type"], shape["points"], width, height))
            except (ValueError, KeyError):
                malformed += 1

    if failed:
        logger.warning("Không lấy được annotations của job %s; số đối tượng của các job này bị tính là 0", failed)
    if malformed:
        logger.warning("Bỏ qua %d bản ghi hình học hỏng (sai số tọa độ hoặc thiếu trường)", malformed)

    jobs: list[Job] = []
    people: dict[str, Annotator] = {}
    for raw in cvat.get("jobs", []):
        status = raw.get("status") or raw.get("stage") or ""
        person = _assignee(raw)
        annotator_id = str(person["id"]) if person and "id" in person else None
        if person and annotator_id not in people:
            full_name = f"{person.get('first_name', '')} {person.get('last_name', '')}".strip()
            people[annotator_id] = Annotator(annotator_id, full_name or person.get("username", ""))
        updated = _parse_dt(raw.get("updated_date"))
        jobs.append(
            Job(
                job_id=raw["id"],
                task_id=raw.get("task_id", task.get("id")),
                annotator_id=annotator_id,
                status=status,
                total_frames=raw.get("frame_count") or 0,
                total_objects=drawn_by_job.get(raw["id"], 0),
                active_time_hours=0.0,
                date_key=updated.date() if (status == "completed" and updated) else None,
            )
        )

    return SnapshotData(
        snapshot_dir=str(folder),
        task_id=task.get("id"),
        task_name=task.get("name"),
        total_frames=task.get("size"),
        jobs=jobs,
        annotators=list(people.values()),
        geometries=geometries,
        frame_size=frame_size,
        counts=counts,
        failed_annotation_jobs=failed,
        malformed_records=malformed,
    )
