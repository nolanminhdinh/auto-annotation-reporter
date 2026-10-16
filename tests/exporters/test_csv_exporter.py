"""Unit tests cho csv_exporter (WBS 2.5)."""
from __future__ import annotations

import csv
import tempfile
import unittest
from datetime import date
from pathlib import Path

from src.exporters.csv_exporter import (
    ANNOTATOR_SEGMENTS_FIELDS,
    BATCH_PROGRESS_FIELDS,
    EDGE_CASES_FIELDS,
    QA_METRICS_FIELDS,
    export_all,
    export_annotator_segments,
    export_batch_progress,
    export_edge_cases,
    export_qa_metrics,
)


class TestCsvExporter(unittest.TestCase):
    def setUp(self) -> None:
        sample_dir = Path(__file__).resolve().parents[2] / "sample_data"
        if not sample_dir.exists():
            sample_dir = Path(__file__).resolve().parents[3] / "sample_data"
        self.sample_data_dir = sample_dir
        self.real_snapshot_dir = self.sample_data_dir / "real_snapshot"
        self.temp_dir = tempfile.TemporaryDirectory()
        self.out_dir = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _read_csv(self, path: Path):
        with open(path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            return reader.fieldnames, rows

    def test_export_all_sample_data(self) -> None:
        as_of = date(2026, 10, 9)
        results = export_all(self.sample_data_dir, self.out_dir, as_of)

        self.assertIn("batch_progress", results)
        self.assertIn("qa_metrics", results)
        self.assertIn("annotator_segments", results)
        self.assertIn("edge_cases", results)

        for name, path in results.items():
            self.assertTrue(path.exists())
            # Kiểm tra BOM UTF-8-sig
            raw_bytes = path.read_bytes()
            self.assertTrue(raw_bytes.startswith(b"\xef\xbb\xbf"), f"{name} thiếu BOM")

    def test_batch_progress_schema(self) -> None:
        as_of = date(2026, 10, 9)
        path = export_batch_progress(self.sample_data_dir, self.out_dir, as_of)
        fields, rows = self._read_csv(path)
        self.assertEqual(fields, BATCH_PROGRESS_FIELDS)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["as_of"], "2026-10-09")

    def test_qa_metrics_schema(self) -> None:
        as_of = date(2026, 10, 9)
        path = export_qa_metrics(self.sample_data_dir, self.out_dir, as_of)
        fields, rows = self._read_csv(path)
        self.assertEqual(fields, QA_METRICS_FIELDS)
        self.assertEqual(len(rows), 1)

    def test_annotator_segments_empty_header(self) -> None:
        # sample_data không có annotator -> bảng rỗng nhưng phải có đủ header
        as_of = date(2026, 10, 9)
        path = export_annotator_segments(self.sample_data_dir, self.out_dir, as_of)
        fields, rows = self._read_csv(path)
        self.assertEqual(fields, ANNOTATOR_SEGMENTS_FIELDS)
        self.assertEqual(len(rows), 0)

    def test_annotator_segments_real_snapshot(self) -> None:
        if not self.real_snapshot_dir.exists():
            self.skipTest("real_snapshot directory does not exist")
        as_of = date(2026, 10, 9)
        path = export_annotator_segments(self.real_snapshot_dir, self.out_dir, as_of)
        fields, rows = self._read_csv(path)
        self.assertEqual(fields, ANNOTATOR_SEGMENTS_FIELDS)
        self.assertGreater(len(rows), 0)

    def test_edge_cases_from_report_data(self) -> None:
        as_of = date(2026, 10, 9)
        path = export_edge_cases(self.sample_data_dir, self.out_dir, as_of)
        fields, rows = self._read_csv(path)
        self.assertEqual(fields, EDGE_CASES_FIELDS)
        self.assertGreater(len(rows), 0)
        self.assertEqual(rows[0]["number"], "2")
        self.assertEqual(rows[0]["link_status"], "verified")


if __name__ == "__main__":
    unittest.main()
