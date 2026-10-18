from pathlib import Path
import unittest

from src.processors.normalizer import normalize_snapshot


class NormalizerTests(unittest.TestCase):
    def test_native_cvat_issues_scope_resolution_and_frame_validation(self):
        cvat={'task':{'id':10},'jobs':[{'id':1,'type':'annotation','start_frame':0,'stop_frame':9}],
              'issues':[{'id':7,'job':1,'frame':3,'resolved':False},
                        {'id':8,'job':1,'frame':30,'resolved':False},
                        {'id':9,'job':1,'frame':3,'resolved':True},
                        {'id':10,'job':99,'frame':3,'resolved':False}],
              'comments':[{'issue':7,'message':'Check actual box','created_date':'2026-10-18'}]}
        result=normalize_snapshot({'scope':{'cvat_host':'https://cvat.test'}},cvat,{'issues':[]},[],Path('sample'))
        items=result['edge_cases']['items']
        self.assertEqual([i['number'] for i in items],[7,8])
        self.assertEqual(items[0]['case_id'],'cvat:10:7')
        self.assertEqual(items[0]['description'],'Check actual box')
        self.assertTrue(items[0]['cvat_job_url'].endswith('?frame=3'))
        self.assertIsNone(items[1]['cvat_job_url'])

    def test_other_task_issue_excluded_and_general_question_kept(self):
        issues = [
            {"number": 1, "title": "Specific Case", "state": "open", "labels": [{"name": "mentor-question"}]},
            {"number": 2, "title": "General Question", "state": "open", "labels": [{"name": "mentor-question"}]},
        ]
        links = [
            {"github_issue": 1, "cvat_task_id": 9999, "cvat_job_id": 30, "status": "verified"},
        ]
        manifest = {"scope": {"task_id": 1001, "cvat_host": "https://cvat.test"}, "sources": {}}

        data = normalize_snapshot(manifest, None, {"issues": issues}, links, Path("sample"))
        questions = data["open_questions"]["items"]

        self.assertEqual([q["number"] for q in questions], [2])
        self.assertEqual(data["metadata"]["excluded_issues"][0]["reason"], "other_task")
        self.assertEqual(data["metadata"]["excluded_issues"][0]["task_id"], 9999)

    def test_ground_truth_job_excluded_from_progress(self):
        cvat = {
            "task": {"id": 10, "name": "Test Task", "size": 100},
            "jobs": [
                {"id": 1, "type": "annotation", "state": "completed", "frame_count": 50},
                {"id": 2, "type": "annotation", "state": "in progress", "frame_count": 50},
                {"id": 3, "type": "ground_truth", "state": "completed", "frame_count": 10},
            ],
        }
        manifest = {"scope": {"task_id": 10}, "sources": {}}
        data = normalize_snapshot(manifest, cvat, None, [], Path("sample"))

        self.assertEqual(data["batch_progress"]["annotation_job_count"], 2)
        self.assertEqual(data["batch_progress"]["completed_annotation_job_count"], 1)
        self.assertEqual(data["batch_progress"]["completed_annotation_job_percent"], 50.0)

    def test_deep_link_generates_frame_query_parameter(self):
        issues = [
            {"number": 42, "title": "Occluded Car", "state": "open", "labels": [{"name": "ca-kho"}], "body": "test"}
        ]
        links = [
            {
                "github_issue": 42,
                "cvat_task_id": 1001,
                "cvat_job_id": 2002,
                "frame": 142,
                "status": "verified",
            }
        ]
        manifest = {"scope": {"task_id": 1001, "cvat_host": "https://app.cvat.ai"}, "sources": {}}
        data = normalize_snapshot(manifest, None, {"issues": issues}, links, Path("sample"))

        item = data["edge_cases"]["items"][0]
        self.assertEqual(item["frame"], 142)
        self.assertEqual(item["cvat_job_url"], "https://app.cvat.ai/tasks/1001/jobs/2002?frame=142")


if __name__ == "__main__":
    unittest.main()
