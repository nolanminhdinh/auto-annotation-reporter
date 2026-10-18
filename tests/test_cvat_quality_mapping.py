"""QA contracts: matching counts, sampled conflicts, scopes and missing history."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from powerbi.create_demo_snapshot import create_demo
from src.processors.cvat_quality import matrix_counts, quality_evidence
from src.reporting_pipeline import build_tables


def fixture(jid=1, tid=10):
    group = {'parameters': {'enabled': True, 'annotation_type': 'rectangle', 'filter': '', 'parent_requirement': None},
             'comparison_summary': {'calculation': {'status': 'computed'}, 'confusion_matrix': {
                 'labels': ['car', 'truck', 'unmatched'], 'axes': {'rows': 'ds', 'cols': 'gt'},
                 'rows': [[7, 1, 1], [0, 2, 0], [3, 0, 0]]}},
             'conflicts': [{'frame_id': 0, 'type': 'mismatching_label', 'severity': 'error',
                            'annotation_ids': [{'job_id': jid, 'obj_id': 55, 'type': 'shape'}]}]}
    parent = {'status': 'success', 'metadata': {'id': 100, 'task_id': tid, 'target': 'task', 'created_date': '2026-10-18T00:00:00Z'}, 'data': {}}
    child = {'status': 'success', 'metadata': {'id': 101, 'task_id': tid, 'job_id': jid, 'parent_id': 100, 'created_date': '2026-10-18T00:00:01Z'},
             'data': {'job_id': jid, 'task_id': tid, 'parent_id': 100, 'groups': {'boxes': group}}}
    return {'quality_reports_data': {'status': 'available', 'reports': [parent, child]},
            'annotations': [{'job_id': jid, 'status': 'success', 'data': {'shapes': [{'id': 55, 'label_id': 1}]}}]}


class CVATQualityMappingTests(unittest.TestCase):
    def evidence(self, raw):
        return quality_evidence(raw, [{'id': 1, 'start_frame': 0, 'stop_frame': 19}], 10, 'https://cvat.test')

    def test_micro_f1_counts_wrong_class_as_false_positive_and_negative(self):
        evals, defects, warnings = self.evidence(fixture())
        self.assertAlmostEqual(evals[0]['precision'], 9/11)
        self.assertAlmostEqual(evals[0]['recall'], 9/13)
        self.assertAlmostEqual(evals[0]['f1_score'], 18/24)
        self.assertIsNone(evals[0]['mean_iou'])
        self.assertIsNone(defects[0]['review_id'])
        self.assertEqual(defects[0]['label_key'], '10:1')
        self.assertTrue(warnings)

    def test_unsupported_axes_or_negative_counts_do_not_publish_metrics(self):
        for axes, value in [({'rows': 'gt', 'cols': 'ds'}, 1), ({'rows': 'ds', 'cols': 'gt'}, -1)]:
            raw=fixture(); matrix=raw['quality_reports_data']['reports'][1]['data']['groups']['boxes']['comparison_summary']['confusion_matrix']
            matrix['axes']=axes; matrix['rows'][0][0]=value
            self.assertEqual(self.evidence(raw)[0], [])

    def test_parent_and_child_are_not_double_counted(self):
        raw=fixture(); raw['quality_reports_data']['reports'][0]['data']['groups']=copy.deepcopy(raw['quality_reports_data']['reports'][1]['data']['groups'])
        self.assertEqual(len(self.evidence(raw)[0]), 1)
        self.assertEqual(len(self.evidence(raw)[1]), 1)

    def test_old_children_and_wrong_task_are_excluded(self):
        for key,value in [('parent_id',99),('task_id',99),('job_id',99)]:
            raw=fixture();raw['quality_reports_data']['reports'][1]['metadata'][key]=value
            self.assertEqual(self.evidence(raw)[0], [])

    def test_overlapping_requirements_are_not_summed(self):
        raw=fixture();groups=raw['quality_reports_data']['reports'][1]['data']['groups'];groups['duplicate']=copy.deepcopy(groups['boxes'])
        self.assertEqual(self.evidence(raw)[0], [])

    def test_no_predictions_with_gt_has_zero_f1(self):
        raw=fixture(); group=raw['quality_reports_data']['reports'][1]['data']['groups']['boxes']
        group['comparison_summary']['confusion_matrix']['rows']=[[0,0,0],[0,0,0],[3,0,0]]
        self.assertEqual(self.evidence(raw)[0][0]['f1_score'],0)

    def test_duplicate_conflicts_and_invalid_frames(self):
        raw=fixture(); conflicts=raw['quality_reports_data']['reports'][1]['data']['groups']['boxes']['conflicts']
        conflicts.append(copy.deepcopy(conflicts[0]));bad=copy.deepcopy(conflicts[0]);bad['frame_id']=99;conflicts.append(bad)
        self.assertEqual(len(self.evidence(raw)[1]),1)

    def test_pipeline_keeps_hours_and_human_review_missing(self):
        with tempfile.TemporaryDirectory() as folder:
            source=create_demo(Path(folder)/'source'); (source/'operations.json').unlink()
            p=source/'cvat.json';raw=json.loads(p.read_text(encoding='utf-8'));jid=raw['jobs'][0]['id'];tid=raw['task']['id']
            raw['quality_reports_data']=fixture(jid,tid)['quality_reports_data']
            p.write_text(json.dumps(raw),encoding='utf-8');_,tables,_=build_tables(source)
            kpi={r['metric']:r['expected_value'] for r in tables['kpi_reconciliation']}
            self.assertEqual(kpi['Avg_F1_Score'],.75)
            self.assertEqual(kpi['Total_Defects'],1)
            self.assertIsNone(kpi['Defect_Density_Per_100F'])
            self.assertIsNone(kpi['Total_Active_Hours'])
            self.assertIsNone(kpi['First_Time_Pass_Rate'])
            self.assertIsNone(kpi['Avg_mIoU_Score'])
            self.assertEqual(tables['fact_qa_reviews'],[])

    def test_human_reviews_do_not_change_automatic_defect_denominator(self):
        with tempfile.TemporaryDirectory() as folder:
            source=create_demo(Path(folder)/'source')
            op=source/'operations.json'; operations=json.loads(op.read_text(encoding='utf-8'))
            operations['availability'].update(defects=False,ground_truth=False)
            operations['defects']=[];operations['ground_truth_evals']=[]
            op.write_text(json.dumps(operations),encoding='utf-8')
            p=source/'cvat.json';raw=json.loads(p.read_text(encoding='utf-8'))
            raw['quality_reports_data']=fixture(raw['jobs'][0]['id'],raw['task']['id'])['quality_reports_data']
            p.write_text(json.dumps(raw),encoding='utf-8');_,tables,_=build_tables(source)
            kpi={r['metric']:r['expected_value'] for r in tables['kpi_reconciliation']}
            self.assertEqual(kpi['Avg_Defects_Per_Job'],1)
            self.assertIsNone(kpi['Defect_Density_Per_100F'])


if __name__=='__main__':unittest.main()
