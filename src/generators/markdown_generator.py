"""Markdown Report Generator rendering the standard 4-section Mentor Draft."""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional


def escape_cell(value: Any) -> str:
    """Escape pipe and linebreaks for markdown table cells."""
    if value is None:
        return "Chưa có"
    return str(value).replace("|", "\\|").replace("\n", " ").replace("\r", "").strip()


def format_vn_time(iso_str: Optional[str]) -> str:
    """Format UTC ISO timestamp to Vietnam Time (UTC+7)."""
    if not iso_str:
        return "Chưa có"
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        vn_dt = dt.astimezone(timezone(timedelta(hours=7)))
        return vn_dt.strftime("%d/%m/%Y %H:%M:%S (UTC+7)")
    except Exception:
        return str(iso_str)


def render_mentor_report(data: Dict[str, Any]) -> str:
    """Render standardized Markdown mentor report draft."""
    meta = data.get("metadata", {})
    progress = data.get("batch_progress", {})
    scores = data.get("scores", {})
    annotations = data.get("annotations", {})

    lines: List[str] = [
        "# 📋 Bản Nháp Báo Cáo Trước Phiên Họp Mentor",
        "",
        f"**Phiên họp**: {escape_cell(meta.get('mentor_session') or 'Định kỳ hàng tuần')}",
        f"**Thời điểm trích xuất dữ liệu**: {format_vn_time(meta.get('snapshot_started_at'))}",
        f"**Thời điểm khởi tạo bản nháp**: {format_vn_time(meta.get('generated_at'))}",
        f"**Snapshot nguồn**: `{escape_cell(meta.get('snapshot'))}`",
        "",
        "> 💡 *Bản nháp tự động từ hệ thống CVAT & GitHub Sync. Nhóm trưởng vui lòng rà soát và bổ sung ngữ cảnh (5 phút) trước phiên họp.*",
        "",
    ]

    warnings = meta.get("warnings", [])
    if warnings:
        lines += [
            "### ⚠️ Thông tin cần lưu ý & Cảnh báo dữ liệu:",
            "",
        ]
        for w in warnings:
            lines.append(f"- {w}")
        lines.append("")

    # --- Section 1: Tiến độ Batch & KPI ---
    lines += [
        "---",
        "",
        "## 1. 📊 Tiến độ Batch & Vận Tốc Gán Nhãn",
        "",
        f"- **CVAT Task**: **{escape_cell(progress.get('task_name'))}** (ID: `{escape_cell(progress.get('task_id'))}`)",
        f"- **Tổng số Frame**: **{escape_cell(progress.get('total_frames'))}**",
    ]

    if progress.get("status") == "available":
        pct = progress.get("completed_annotation_job_percent")
        pct_str = f"{pct}%" if pct is not None else "Chưa xác định"
        lines += [
            f"- **Tỷ lệ Job hoàn thành**: **{progress.get('completed_annotation_job_count')}/{progress.get('annotation_job_count')}** ({pct_str})",
            "",
            "> ℹ️ *Ghi chú: Tỷ lệ theo Job phản ánh trạng thái hoàn thành quy trình trên CVAT, chưa đại diện cho % frame đã qua nghiệm thu QA cuối cùng.*",
            "",
            "| Mã Job | Loại Job | Giai đoạn (Stage) | Trạng thái (State) | Người phụ trách | Số Frame |",
            "| :---: | :---: | :---: | :---: | :---: | :---: |",
        ]
        for job in progress.get("jobs", []):
            job_link = f"[{job['job_id']}]({job['source_url']})"
            lines.append(
                f"| {job_link} | {escape_cell(job.get('type'))} | {escape_cell(job.get('stage'))} | {escape_cell(job.get('state'))} | {escape_cell(job.get('assignee'))} | {escape_cell(job.get('frame_count'))} |"
            )
        lines.append("")
    else:
        lines += ["\n*Chưa kết nối được dữ liệu CVAT; không có số liệu tiến độ đáng tin cậy.*\n"]

    # Annotations sub-section
    if annotations.get("status") in ("available", "partial"):
        totals = annotations.get("totals", {})
        lines += [
            "### 📐 Thống kê đối tượng gán nhãn (Annotations):",
            "",
            f"- Tổng số: **{totals.get('shapes', 0)} shapes**, **{totals.get('tracks', 0)} tracks**, **{totals.get('tags', 0)} tags** "
            f"({totals.get('track_shape_records', 0)} bản ghi shape trong tracks).",
            "",
            "| Tên Nhãn (Class) | Mã Label ID | Shapes | Tracks | Tags |",
            "| :--- | :---: | :---: | :---: | :---: |",
        ]
        for item in annotations.get("by_label", []):
            lines.append(
                f"| **{escape_cell(item.get('label_name'))}** | `{escape_cell(item.get('label_id'))}` | {item.get('shapes', 0)} | {item.get('tracks', 0)} | {item.get('tags', 0)} |"
            )
        lines.append("")
    else:
        lines += ["*Chưa có thống kê annotations trong snapshot này.*\n"]

    # LLM Multi-Team Synthesis sub-section (nếu có)
    llm_summary = data.get("llm_summary")
    if llm_summary:
        from .llm_summarizer import format_summary_markdown
        lines += [
            "",
            format_summary_markdown(llm_summary),
        ]

    # --- Section 2: Điểm chất lượng & QA/QC ---
    lines += [
        "---",
        "",
        "## 2. 🎯 Chất lượng & Điểm QA/QC",
        "",
    ]
    if scores.get("status") == "available":
        lines += [
            f"- **Điểm đánh giá (mIoU / Quality Score)**: **{scores.get('value')}**",
            f"- **Phương pháp**: {scores.get('method')}",
            f"- **Báo cáo nguồn**: [Xem chi tiết trên CVAT]({scores.get('source_url')})",
            "",
        ]
    else:
        lines += [
            f"> ⚠️ **Trạng thái**: {scores.get('reason', 'Chưa có điểm.')}",
            "> *Lưu ý: Hệ thống không coi việc thiếu dữ liệu kiểm thử là điểm 0.*",
            "",
        ]

    # --- Section 3: Ca khó (Edge Cases) kèm Deep Link ---
    lines += [
        "---",
        "",
        "## 3. 🔍 Danh Sách Ca Khó & Trường Hợp Biên (Edge Cases)",
        "",
    ]
    edges = data.get("edge_cases", {})
    if edges.get("status") == "unavailable":
        lines += ["*Chưa kết nối được nguồn GitHub Issues cho mục này.*\n"]
    elif not edges.get("items"):
        lines += ["*Không có issue mở gắn nhãn `ca-kho` trong kỳ báo cáo này.*\n"]
    else:
        for it in edges.get("items", []):
            frame_label = f"Frame #{it['frame']}" if it.get("frame") is not None else "Toàn Job"
            lines += [
                f"### 📍 Issue #{it['number']}: {escape_cell(it.get('title'))}",
                "",
                f"- **Người tạo**: `{it.get('author')}` | **Vị trí**: **{frame_label}**",
                f"- [🔗 Xem Issue trên GitHub]({it.get('source_url')})",
            ]
            if it.get("cvat_job_url"):
                if it.get("frame") is not None:
                    lines.append(
                        f"- 🎯 **[🔗 Mở trực tiếp Frame {it['frame']} trên CVAT]({it['cvat_job_url']})** *(Đã xác minh liên kết task/job)*"
                    )
                else:
                    lines.append(
                        f"- 🔗 **[Mở Job CVAT]({it['cvat_job_url']})** *(Đã xác minh quan hệ task/job; chưa có chỉ số frame cụ thể)*"
                    )
            else:
                lines.append(
                    f"- ⚠️ *Liên kết CVAT chưa xác minh ({it.get('link_status')})*"
                )
            lines.append("")
            lines.append("**Mô tả vấn đề & Đề xuất:**")
            desc_lines = (it.get("description") or "Chưa có mô tả.").splitlines()
            lines += [f"> {line}" for line in desc_lines]
            lines.append("")

    # --- Section 4: Câu hỏi mở & Mentor Consultation ---
    lines += [
        "---",
        "",
        "## 4. 💬 Câu Hỏi Mở Cần Mentor Định Đoạt (Open Questions)",
        "",
    ]
    questions = data.get("open_questions", {})
    if questions.get("status") == "unavailable":
        lines += ["*Chưa kết nối được nguồn GitHub Issues cho mục này.*\n"]
    elif not questions.get("items"):
        lines += ["*Không có câu hỏi mở gắn nhãn `mentor-question` trong kỳ báo cáo này.*\n"]
    else:
        for it in questions.get("items", []):
            lines += [
                f"### ❓ Question #{it['number']}: {escape_cell(it.get('title'))}",
                "",
                f"- **Người đặt câu hỏi**: `{it.get('author')}`",
                f"- [🔗 Xem thảo luận trên GitHub]({it.get('source_url')})",
            ]
            if it.get("cvat_job_url"):
                lines.append(f"- [Mở Job liên quan trên CVAT]({it['cvat_job_url']})")
            lines.append("")
            desc_lines = (it.get("description") or "Chưa có mô tả.").splitlines()
            lines.append("")

    # Gợi ý chủ đề thảo luận từ LLM
    if llm_summary and llm_summary.get("suggested_agenda"):
        lines += [
            "### 💡 Gợi Ý Chủ Đề Họp Trọng Tâm Với Mentor (AI Synthesis):",
            "",
        ]
        for idx, agenda_item in enumerate(llm_summary["suggested_agenda"], start=1):
            lines.append(f"{idx}. {agenda_item}")
        lines.append("")

    # --- Phụ lục Blocker nếu có ---
    blockers = data.get("blockers", {}).get("items", [])
    if blockers:
        lines += [
            "---",
            "",
            "## 🚨 Sự Cố Hạ Tầng & Quy Trình Ngưng Trệ (Blockers)",
            "",
        ]
        for it in blockers:
            lines += [
                f"- **[#{it['number']}]({it['source_url']})**: {escape_cell(it.get('title'))} (Báo bởi `{it.get('author')}`)",
            ]
        lines.append("")

    return "\n".join(lines) + "\n"
