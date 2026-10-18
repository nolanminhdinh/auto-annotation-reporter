import json
import unittest
from unittest.mock import Mock, patch

import requests
from src.generators.team_summary import synthesize, validate_reports, offline_summary, markdown

REPORTS = [
    {'report_id': 'T1', 'team': 'Xe', 'report_text': 'Blocker: ảnh bị lóa. Cần Mentor xác nhận guideline.'},
    {'report_id': 'T2', 'team': 'QA', 'report_text': 'Đã rà soát lỗi. Có cần review lại không?'},
]


class TeamSummaryTests(unittest.TestCase):
    @patch('src.generators.team_summary.requests.post')
    def test_offline_never_calls_network_even_if_configured(self, post):
        result = synthesize(REPORTS, api_key='fake-key', model='configured-model')
        post.assert_not_called()
        self.assertEqual(result['provider'], 'offline_extract')
        self.assertFalse(result['is_ai_generated'])
        self.assertEqual(result['summary']['critical_blockers'][0]['report_ids'], ['T1'])

    def test_fallback_is_deterministic_and_evidence_linked(self):
        self.assertEqual(synthesize(REPORTS), synthesize(REPORTS))
        result = synthesize(REPORTS)
        self.assertIn('[T1]', markdown(result))
        self.assertTrue(result['review_required'])

    def test_missing_reports_do_not_invent_blockers(self):
        result = synthesize([])
        self.assertEqual(result['source_report_ids'], [])
        self.assertEqual(result['summary']['critical_blockers'], [])

    def test_duplicate_ids_rejected(self):
        with self.assertRaises(ValueError): validate_reports([REPORTS[0], REPORTS[0]])

    def test_empty_text_rejected(self):
        with self.assertRaises(ValueError): validate_reports([{'team':'QA','report_text':''}])

    @patch('src.generators.team_summary.requests.post')
    def test_missing_configuration_falls_back_without_network(self, post):
        result = synthesize(REPORTS, provider='gemini')
        self.assertIn('not configured', result['fallback_reason'])
        post.assert_not_called()

    def response(self, summary):
        session=Mock()
        session.post.return_value.status_code=200
        session.post.return_value.json.return_value={'output':[{'type':'text','text':json.dumps(summary)}]}
        return session

    def test_valid_gemini_response_and_header_auth(self):
        session=self.response(offline_summary(REPORTS))
        result=synthesize(REPORTS, 'gemini', 'fake-key', 'configured-model', session)
        self.assertEqual(result['provider'],'gemini')
        self.assertTrue(result['is_ai_generated'])
        args,kwargs=session.post.call_args
        self.assertNotIn('fake-key',args[0])
        self.assertEqual(kwargs['headers']['x-goog-api-key'],'fake-key')
        self.assertFalse(kwargs['json']['store'])
        self.assertFalse(kwargs['allow_redirects'])

    def test_unknown_evidence_rejected_and_fallback_returned(self):
        summary=offline_summary(REPORTS)
        summary['critical_blockers'][0]['report_ids']=['invented']
        result=synthesize(REPORTS, 'gemini', 'fake-key', 'configured-model', self.response(summary))
        self.assertEqual(result['provider'],'offline_extract')
        self.assertIn('fallback_reason',result)

    def test_timeout_is_redacted_and_does_not_fail_pipeline(self):
        session=Mock();session.post.side_effect=requests.Timeout('request with fake-secret-key')
        result=synthesize(REPORTS,'gemini','fake-secret-key','configured-model',session)
        self.assertNotIn('fake-secret-key',json.dumps(result))
        self.assertEqual(session.post.call_count,1)

    def test_http_error_falls_back(self):
        session=Mock();session.post.return_value.status_code=429
        result=synthesize(REPORTS,'gemini','fake-key','configured-model',session)
        self.assertEqual(result['provider'],'offline_extract')
        self.assertIn('429',result['fallback_reason'])

    def test_malformed_model_identifier_never_sent(self):
        session=Mock()
        result=synthesize(REPORTS,'gemini','fake-key','bad/model',session)
        self.assertIn('Invalid',result['fallback_reason'])
        session.post.assert_not_called()


if __name__=='__main__': unittest.main()
