"""Unit tests for Report Reader and Warehouse Agent."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from src.generators.report_agent import ReportReaderAgent


class TestReportAgent(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.sample_report = Path(self.temp_dir.name) / "SAMPLE_REPORT.md"
        self.sample_report.write_text("""# 📋 Bản Nháp Báo Cáo
## 1. 📊 Tiến độ Batch & Vận Tốc Gán Nhãn
- CVAT Task: Task 217 (ID: `217`)
- Tỷ lệ Job hoàn thành: 3/5 (60%)
## 2. 🎯 Chất lượng & Điểm QA/QC
- Điểm đánh giá (mIoU / Quality Score): 91.4
## 3. 🔍 Danh Sách Ca Khó & Trường Hợp Biên (Edge Cases)
### 📍 Issue #2: DEMO: occluded vehicle
## 4. 💬 Câu Hỏi Mở Cần Mentor Định Đoạt (Open Questions)
### ❓ Question #3: DEMO: guideline question
""", encoding="utf-8")

        self.db_path = Path(__file__).resolve().parents[1] / "data" / "annotation_warehouse.db"
        self.agent = ReportReaderAgent(report_path=self.sample_report, db_path=self.db_path)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_load_report_sections(self) -> None:
        self.agent.load_report(self.sample_report)
        self.assertGreaterEqual(len(self.agent.sections), 4)
        section_titles = list(self.agent.sections.keys())
        self.assertTrue(any("Tiến độ" in t for t in section_titles))
        self.assertTrue(any("Chất lượng" in t for t in section_titles))
        self.assertTrue(any("Ca Khó" in t for t in section_titles))

    def test_get_database_kpis(self) -> None:
        if not self.db_path.exists():
            self.skipTest("Database not found")
        data = self.agent.get_database_kpis()
        self.assertIn("progress", data)
        self.assertIn("qa_metrics", data)
        self.assertIn("edge_cases", data)
        self.assertIn("team_reports", data)

    def test_verify_reconciliation(self) -> None:
        if not self.db_path.exists():
            self.skipTest("Database not found")
        reconciliation = self.agent.verify_reconciliation()
        self.assertIn("checks", reconciliation)
        self.assertTrue(reconciliation["overall_consistent"])

    def test_generate_executive_briefing(self) -> None:
        brief = self.agent.generate_executive_briefing()
        self.assertIn("BẢN TÓM TẮT ĐIỀU HÀNH", brief)
        self.assertIn("Tiến Độ & Vận Tốc Cốt Lõi", brief)
        self.assertIn("Chất Lượng QA/QC", brief)
        self.assertIn("Điểm Nghẽn & Ca Khó", brief)

    def test_answer_questions(self) -> None:
        ans_progress = self.agent.answer_question("Tiến độ hiện tại có kịp hạn hoàn thành không?")
        self.assertIn("Tiến độ", ans_progress)
        self.assertIn("ETA", ans_progress)

        ans_quality = self.agent.answer_question("Chất lượng và tỉ lệ duyệt bài thế nào?")
        self.assertIn("Chất lượng", ans_quality)
        self.assertIn("FTPR", ans_quality)

        ans_edge = self.agent.answer_question("Có ca khó hay tình huống che khuất nào không?")
        self.assertIn("Ca khó", ans_edge)

        ans_annotator = self.agent.answer_question("Nhân sự nào gán nhãn tốt nhất?")
        self.assertIn("Nhân sự", ans_annotator)


if __name__ == "__main__":
    unittest.main()
