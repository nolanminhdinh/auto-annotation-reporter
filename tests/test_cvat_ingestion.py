"""Offline API contract regressions; never connects to a real CVAT server."""
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from src.extractors.cvat_extractor import CVATExtractor
from src.extractors.base_client import APIError
from src.processors.normalizer import normalize_snapshot


class CVATIngestionTests(unittest.TestCase):
    def setUp(self):
        self.ext=CVATExtractor('https://cvat.test','fake')
        self.addCleanup(self.ext.close)

    def test_pat_uses_bearer(self):
        self.assertEqual(self.ext.client.session.headers['Authorization'],'Bearer fake')

    def test_task_identity_mismatch_rejected(self):
        with patch.object(self.ext.client,'get',return_value=Mock(json=lambda:{'id':999})):
            with self.assertRaises(ValueError): self.ext.get_task(1)

    def test_jobs_duplicate_or_wrong_task_rejected(self):
        for jobs in ([{'id':1,'task_id':2}], [{'id':1,'task_id':1}]*2, [{'id':True,'task_id':1}]):
            with patch.object(self.ext.client,'listing',return_value=jobs), self.assertRaises(ValueError):
                self.ext.get_jobs(1)

    def test_annotations_missing_arrays_and_bad_track_rejected(self):
        for data in ({}, {'tags':[],'shapes':[None],'tracks':[]}, {'tags':[],'shapes':[],'tracks':[{'shapes':[None]}]}):
            with patch.object(self.ext.client,'get',return_value=Mock(json=lambda:data)), self.assertRaises(ValueError):
                self.ext.get_job_annotations(1)

    def test_quality_lists_both_targets_and_keeps_nullable_job_task_id(self):
        task={'id':10,'task_id':1,'job_id':None,'target':'task','created_date':'2026-10-01T00:00:00Z'}
        older={**task,'id':9,'created_date':'2026-09-01T00:00:00Z'}
        job={'id':20,'task_id':None,'job_id':7,'target':'job'}
        with patch.object(self.ext.client,'listing',side_effect=[[older,task],[job,{'id':30,'job_id':999}]] ) as listing, patch.object(self.ext.client,'get',return_value=Mock(json=lambda:{'summary':{}})) as get:
            result=self.ext.get_quality_bundle(1,{7})
        self.assertEqual([c.args[1]['target'] for c in listing.call_args_list],['task','job'])
        self.assertEqual(result['status'],'available')
        self.assertEqual(result['latest_task_report']['id'],10)
        self.assertEqual({r['metadata']['id'] for r in result['reports']},{10,20})
        self.assertEqual(get.call_count,2)

    def test_quality_list_failure_is_distinct_from_no_reports(self):
        with patch.object(self.ext.client,'listing',side_effect=APIError('/api/quality/reports',403)):
            result=self.ext.get_quality_bundle(1,set())
        self.assertEqual(result['status'],'failed')
        self.assertEqual(result['list_sources']['task']['http_status'],403)
        with patch.object(self.ext.client,'listing',return_value=[]):
            self.assertEqual(self.ext.get_quality_bundle(1,set())['status'],'unavailable')

    def test_partial_quality_retains_successful_data(self):
        report={'id':10,'task_id':1,'job_id':None}
        with patch.object(self.ext.client,'listing',side_effect=[[report],APIError('/api/quality/reports',404)]), patch.object(self.ext.client,'get',return_value=Mock(json=lambda:{})):
            result=self.ext.get_quality_bundle(1,set())
        self.assertEqual(result['status'],'partial')
        self.assertEqual(result['reports'][0]['status'],'success')

    def test_quality_data_failure_preserves_http_status(self):
        report={'id':10,'task_id':1,'job_id':None}
        with patch.object(self.ext.client,'listing',side_effect=[[report],[]]), patch.object(self.ext.client,'get',side_effect=APIError('/api/quality/reports/10/data',403)):
            result=self.ext.get_quality_bundle(1,set())
        self.assertEqual(result['status'],'partial')
        self.assertEqual(result['reports'][0]['http_status'],403)

    def test_issues_failure_does_not_discard_core_snapshot(self):
        with patch.object(self.ext,'get_task',return_value={'id':1}), patch.object(self.ext,'get_jobs',return_value=[]), patch.object(self.ext,'get_labels',return_value=[]), patch.object(self.ext,'get_issues',side_effect=APIError('/api/issues',403)), patch.object(self.ext,'get_quality_bundle',return_value={'status':'unavailable'}):
            result=self.ext.extract_snapshot(1)
        self.assertEqual(result['task']['id'],1)
        self.assertEqual(result['optional_sources']['issues']['http_status'],403)
        self.assertEqual(result['optional_sources']['comments']['status'],'unavailable')

    def test_quality_metadata_is_not_an_available_numeric_score(self):
        for report,expected,status in [({'id':1},None,'unavailable'),({'id':1,'mean_iou':0.0,'quality_score':.9},0.0,'available')]:
            result=normalize_snapshot({'scope':{},'sources':{}},{'task':{},'quality_report':report},None,[],Path('snapshot'))
            self.assertEqual(result['scores']['value'],expected)
            self.assertEqual(result['scores']['status'],status)

    def test_optional_failures_reach_report_warnings(self):
        cvat={'task':{},'optional_sources':{'issues':{'status':'failed'}},'quality_reports_data':{'status':'partial'}}
        result=normalize_snapshot({'scope':{},'sources':{}},cvat,None,[],Path('snapshot'))
        warnings=' '.join(result['metadata']['warnings'])
        self.assertIn('issues: failed',warnings)
        self.assertIn('Quality Reports',warnings)
