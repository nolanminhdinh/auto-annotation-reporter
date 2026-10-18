"""Publication boundaries: replay, changed snapshots, missing sources and canonical KPI."""
import csv
import json
import sqlite3
import tempfile
import unittest
import contextlib
import io
from contextlib import closing
from pathlib import Path
from unittest.mock import patch
from powerbi.create_demo_snapshot import create_demo
from src.reporting_pipeline import publish_snapshot,build_tables

class ReportingPipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.source=create_demo(self.root/'source')
        self.db=self.root/'report.db';self.out=self.root/'output'

    def edit(self,name,change):
        path=self.source/name;data=json.loads(path.read_text(encoding='utf-8'));change(data);path.write_text(json.dumps(data),encoding='utf-8')

    def publish(self): return publish_snapshot(self.source,self.db,self.out,(1920,1080))

    def query(self,sql):
        with closing(sqlite3.connect(self.db)) as conn: return conn.execute(sql).fetchall()

    def test_demo_reconciles_facts_and_kpi(self):
        self.publish()
        self.assertEqual(self.query('SELECT sum(total_frames) FROM pbi_fact_job_sessions WHERE status="completed"')[0][0],1000)
        self.assertEqual(self.query('SELECT expected_value FROM pbi_kpi_reconciliation WHERE metric="Total_Completed_Frames"')[0][0],1000)
        self.assertEqual(self.query('SELECT count(*) FROM pbi_fact_annotations')[0][0],285)
        self.assertEqual(self.query('SELECT sum(total_objects) FROM pbi_fact_job_sessions')[0][0],285)
        self.assertEqual(self.query('SELECT is_demo FROM pbi_report_status'),[(1,)])

    def test_replay_is_idempotent_and_bronze_immutable(self):
        a=self.publish();b=self.publish()
        self.assertEqual(a['snapshot_id'],b['snapshot_id'])
        self.assertEqual(self.query('SELECT count(*) FROM bronze_snapshots'),[(1,)])

    def test_changed_snapshot_does_not_sum_history(self):
        self.publish()
        self.edit('cvat.json',lambda d:d['jobs'][0].update(state='in progress'))
        self.publish()
        self.assertEqual(self.query('SELECT count(*) FROM bronze_snapshots'),[(2,)])
        self.assertEqual(self.query('SELECT count(*) FROM gold_fact_job_sessions'),[(30,)])
        self.assertEqual(self.query('SELECT count(*) FROM pbi_fact_job_sessions'),[(15,)])

    def test_failed_source_keeps_last_publication(self):
        a=self.publish();pointer=(self.out/'current.json').read_bytes()
        self.edit('manifest.json',lambda d:d['sources']['cvat'].update(status='failed'))
        with self.assertRaises(ValueError): self.publish()
        self.assertEqual(self.query('SELECT snapshot_id FROM serving_state'),[(a['snapshot_id'],)])
        self.assertEqual((self.out/'current.json').read_bytes(),pointer)

    def test_partial_annotations_rejected(self):
        self.edit('cvat.json',lambda d:d['annotations'][0].update(status='failed'))
        with self.assertRaises(ValueError): self.publish()

    def test_no_hours_or_reviews_stay_null(self):
        (self.source/'operations.json').unlink()
        self.publish()
        self.assertEqual(self.query('SELECT expected_value FROM pbi_kpi_reconciliation WHERE metric="Velocity_Frames_Per_Hour"'),[(None,)])
        self.assertEqual(self.query('SELECT expected_value FROM pbi_kpi_reconciliation WHERE metric="First_Time_Pass_Rate"'),[(None,)])
        self.assertEqual(self.query('SELECT DISTINCT active_time_hours FROM pbi_fact_job_sessions'),[(None,)])

    def test_unknown_review_job_rejected(self):
        self.edit('operations.json',lambda d:d['reviews'][0].update(job_id=999))
        with self.assertRaises(ValueError): self.publish()

    def test_duplicate_first_review_rejected(self):
        self.edit('operations.json',lambda d:d['reviews'].append(dict(d['reviews'][0])))
        with self.assertRaises(ValueError): self.publish()

    def test_dimensions_scoped_to_snapshot(self):
        self.publish()
        self.edit('cvat.json',lambda d:[j['assignee'].update(first_name='Changed name') for j in d['jobs'] if j['assignee']['id']==1])
        self.publish()
        self.assertEqual(self.query('SELECT full_name FROM pbi_dim_annotators WHERE annotator_id="1"'),[('Changed name',)])
        self.assertEqual(len(self.query('SELECT full_name FROM gold_dim_annotators WHERE annotator_id="1"')),2)

    def test_ground_truth_latest_only(self):
        def add(d):
            e=dict(d['ground_truth_evals'][0]);e.update(eval_id='new',evaluated_at='2026-10-17T00:00:00Z',mean_iou=.99)
            d['ground_truth_evals'].append(e)
        self.edit('operations.json',add)
        self.publish()
        self.assertEqual(self.query('SELECT mean_iou FROM pbi_fact_ground_truth_eval WHERE job_id=7001'),[(.99,)])

    def test_canonical_csv_schema_and_empty_tables(self):
        (self.source/'operations.json').unlink();self.publish()
        pointer=json.loads((self.out/'current.json').read_text())
        with (Path(pointer['folder'])/'fact_qa_reviews.csv').open(encoding='utf-8-sig') as f:
            self.assertIn('review_decision',next(csv.reader(f)))

    def test_no_fake_completion_dates(self):
        (self.source/'operations.json').unlink();self.publish()
        self.assertEqual(self.query('SELECT DISTINCT date_key FROM pbi_fact_job_sessions'),[(None,)])

    def test_overlapping_frames_rejected(self):
        self.edit('cvat.json',lambda d:d['jobs'][1].update(start_frame=50))
        with self.assertRaises(ValueError): self.publish()

    def test_invalid_gt_score_rejected(self):
        self.edit('operations.json',lambda d:d['ground_truth_evals'][0].update(mean_iou=1.1))
        with self.assertRaises(ValueError): self.publish()

    def test_unified_cli_publishes_without_modifying_source(self):
        from src.main import main
        original={p.name:p.read_bytes() for p in self.source.iterdir()}
        with contextlib.redirect_stdout(io.StringIO()):
            code=main(['--snapshot',str(self.source),'--db',str(self.db),'--output',str(self.root/'runs'),'--powerbi-output',str(self.out),'--frame-size','1920x1080'])
        self.assertEqual(code,0)
        self.assertEqual(original,{p.name:p.read_bytes() for p in self.source.iterdir()})
        draft=next((self.root/'runs').glob('*/MENTOR_REPORT_DRAFT.md')).read_text(encoding='utf-8')
        self.assertIn('DỮ LIỆU GIẢ LẬP',draft)
        self.assertIn('Total_Completed_Frames',draft)

    def test_pat_authorization_uses_bearer(self):
        from src.extractors.cvat_extractor import CVATExtractor
        ext=CVATExtractor('https://example.org','fake-test-token')
        self.assertEqual(ext.client.session.headers['Authorization'],'Bearer fake-test-token')

    def test_offline_summary_and_notification_preview_without_network(self):
        from src.main import main
        with patch('requests.post') as post, contextlib.redirect_stdout(io.StringIO()):
            code=main(['--snapshot',str(self.source),'--db',str(self.db),'--output',str(self.root/'runs'),'--powerbi-output',str(self.out),'--llm-summary','--summary-provider','gemini','--notify','preview'])
        self.assertEqual(code,0)
        post.assert_not_called()
        summary=json.loads(next((self.root/'runs').glob('*/team_summary.json')).read_text(encoding='utf-8'))
        self.assertEqual(len(summary['source_report_ids']),3)
        receipt=json.loads(next((self.root/'runs').glob('*/notification_receipt.json')).read_text())
        self.assertEqual(receipt['status'],'preview_only')

if __name__=='__main__': unittest.main()
