"""Unit tests for LLM Summarizer module."""
from __future__ import annotations

import unittest
from pathlib import Path
from src.generators.llm_summarizer import (
    format_summary_markdown,
    heuristic_summarize,
    summarize_from_warehouse,
)
from src.generators.markdown_generator import render_mentor_report


class TestLLMSummarizer(unittest.TestCase):
    def setUp(self) -> None:
        self.team_reports = [
            {
                "team": "Team Xe con",
                "reporter": "tu_nguyen",
                "report_text": "Camera 02 buổi chiều bị ngược sáng và lóa đèn pha. Đang có 4 ca xe bị che khuất >70% cần Mentor định đoạt.",
            },
            {
                "team": "Team Xe tải",
                "reporter": "duy_vu",
                "report_text": "Mạng chập chờn lúc 14h làm gián đoạn 45 phút. Nhiều xe máy điện đỗ vào ô sạc ô tô, tạm gán nhãn obstacle.",
            },
            {
                "team": "Reviewer QA",
                "reporter": "ngoc_tran",
                "report_text": "Tỷ lệ First-time pass đạt 85%. Chú ý lỗi lệch bounding box ở gương chiếu hậu.",
            },
        ]
        self.kpi_context = {
            "progress_pct_proxy": 60.0,
            "avg_velocity_fps": 38.5,
            "projected_completion_date": "2026-10-18",
        }

    def test_heuristic_summarize_extraction(self) -> None:
        res = heuristic_summarize(self.team_reports, self.kpi_context)
        self.assertIn("executive_summary", res)
        self.assertIn("blockers", res)
        self.assertIn("guideline_disputes", res)
        self.assertIn("quality_warnings", res)
        self.assertIn("suggested_agenda", res)

        # Check blocker detection (lóa, ngược sáng, gián đoạn)
        self.assertTrue(any("ngược sáng" in b or "gián đoạn" in b for b in res["blockers"]))
        # Check guideline dispute (che khuất, tạm gán)
        self.assertTrue(any("che khuất" in g or "tạm gán" in g for g in res["guideline_disputes"]))
        # Check QA warning (lệch bounding box)
        self.assertTrue(any("lệch" in q or "pass" in q for q in res["quality_warnings"]))

    def test_format_summary_markdown(self) -> None:
        summary = heuristic_summarize(self.team_reports, self.kpi_context)
        md = format_summary_markdown(summary)
        self.assertIn("### 💬 Tóm lược Phản ánh từ Đội ngũ Gán nhãn", md)
        self.assertIn("Sự cố hạ tầng", md)
        self.assertIn("Guideline cần định đoạt", md)
        self.assertIn("Cảnh báo chất lượng", md)

    def test_summarize_from_warehouse(self) -> None:
        db_path = Path(__file__).resolve().parents[1] / "data" / "annotation_warehouse.db"
        if not db_path.exists():
            self.skipTest("Database file not found")
        res = summarize_from_warehouse(db_path=db_path)
        self.assertIn("executive_summary", res)
        self.assertTrue(len(res["blockers"]) > 0)

    def test_render_mentor_report_with_llm(self) -> None:
        summary = heuristic_summarize(self.team_reports, self.kpi_context)
        data = {
            "metadata": {"snapshot": "SNAP_01"},
            "batch_progress": {"status": "available", "task_name": "Task 217", "total_frames": 500},
            "scores": {"status": "available", "value": 91.4, "method": "CVAT GT"},
            "edge_cases": {"status": "available", "items": []},
            "open_questions": {"status": "available", "items": []},
            "llm_summary": summary,
        }
        rendered = render_mentor_report(data)
        self.assertIn("### 💬 Tóm lược Phản ánh từ Đội ngũ Gán nhãn", rendered)
        self.assertIn("### 💡 Gợi Ý Chủ Đề Họp Trọng Tâm Với Mentor", rendered)


if __name__ == "__main__":
    unittest.main()
