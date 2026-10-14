import unittest
from src.extractors.cvat_extractor import CVATExtractor


class CVATExtractorTests(unittest.TestCase):
    def test_cloud_pat_uses_bearer_authentication(self):
        ext = CVATExtractor(host="https://app.cvat.ai", token="fake-pat")
        self.assertEqual(ext.client.session.headers["Authorization"], "Bearer fake-pat")

    def test_build_deep_link_with_and_without_frame(self):
        ext = CVATExtractor(host="https://app.cvat.ai", token="fake")
        link_job = ext.build_deep_link(task_id=217, job_id=1719)
        self.assertEqual(link_job, "https://app.cvat.ai/tasks/217/jobs/1719")

        link_frame = ext.build_deep_link(task_id=217, job_id=1719, frame=142)
        self.assertEqual(link_frame, "https://app.cvat.ai/tasks/217/jobs/1719?frame=142")

    def test_annotations_summary_success(self):
        labels = [{"id": 1, "name": "vehicle"}, {"id": 2, "name": "pedestrian"}]
        annotations = [
            {
                "job_id": 101,
                "status": "success",
                "data": {
                    "shapes": [{"label_id": 1, "frame": 0}, {"label_id": 2, "frame": 1}],
                    "tracks": [{"label_id": 1, "shapes": [{"frame": 0}, {"frame": 5}]}],
                    "tags": [{"label_id": 1}],
                },
            }
        ]
        summary = CVATExtractor.summarize_annotations(annotations, labels)
        self.assertEqual(summary["status"], "available")
        self.assertEqual(summary["totals"]["shapes"], 2)
        self.assertEqual(summary["totals"]["tracks"], 1)
        self.assertEqual(summary["totals"]["tags"], 1)
        self.assertEqual(summary["totals"]["track_shape_records"], 2)

    def test_annotations_summary_partial_on_failure(self):
        annotations = [
            {"job_id": 101, "status": "failed", "error": "timeout"},
            {"job_id": 102, "status": "success", "data": {"shapes": [], "tracks": [], "tags": []}},
        ]
        summary = CVATExtractor.summarize_annotations(annotations)
        self.assertEqual(summary["status"], "partial")
        self.assertIsNone(summary["jobs"][0]["counts"])
        self.assertIsNotNone(summary["jobs"][1]["counts"])

    def test_annotations_summary_unavailable_when_none(self):
        summary = CVATExtractor.summarize_annotations(None)
        self.assertEqual(summary["status"], "unavailable")


if __name__ == "__main__":
    unittest.main()
