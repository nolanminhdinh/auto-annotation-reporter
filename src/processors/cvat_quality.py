"""Map CVAT job QA evidence without inventing human reviews or geometry IoU."""
import math


def matrix_counts(matrix):
    labels = matrix.get('labels', [])
    values = matrix.get('rows', [])
    if matrix.get('axes') != {'rows': 'ds', 'cols': 'gt'}:
        return None
    if len(set(labels)) != len(labels) or labels.count('unmatched') != 1 or len(values) != len(labels):
        return None
    if any(len(row) != len(labels) for row in values):
        return None
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0 or int(v) != v for row in values for v in row):
        return None
    active = [i for i, name in enumerate(labels) if name != 'unmatched']
    true_positive = sum(values[i][i] for i in active)
    predicted = sum(sum(values[i]) for i in active)
    reference = sum(sum(row[i] for row in values) for i in active)
    return true_positive, predicted, reference


def quality_evidence(cvat, jobs, task_id, host):
    """Use latest child reports of the latest task report, once per annotation job.

    Only disjoint base shape requirements are combined. Classification Jaccard
    is never interpreted as spatial IoU. Conflicts have no human review_id.
    """
    bundle = cvat.get('quality_reports_data', {})
    records = [r for r in bundle.get('reports', []) if r.get('status') == 'success']
    tasks = [r for r in records if r.get('metadata', {}).get('task_id') == task_id
             and r['metadata'].get('job_id') is None and r['metadata'].get('target', 'task') == 'task']
    if not tasks:
        return [], [], []
    parent = max(tasks, key=lambda r: (r['metadata'].get('created_date', ''), r['metadata'].get('id', 0)))
    parent_id = parent['metadata']['id']
    job_map = {j['id']: j for j in jobs}
    shapes = {}
    for record in cvat.get('annotations', []):
        if record.get('status') != 'success':
            continue
        for shape in record.get('data', {}).get('shapes', []):
            shapes[(record.get('job_id'), shape.get('id'))] = shape
    latest = {}
    for record in records:
        meta = record.get('metadata', {})
        jid = meta.get('job_id')
        if jid not in job_map or meta.get('parent_id') != parent_id or meta.get('task_id') not in (None, task_id):
            continue
        if jid not in latest or (meta.get('created_date', ''), meta['id']) > (latest[jid]['metadata'].get('created_date', ''), latest[jid]['metadata']['id']):
            latest[jid] = record
    evaluations, defects, warnings = [], [], []
    for jid, record in latest.items():
        meta, data = record['metadata'], record.get('data', {})
        if data.get('job_id') != jid or data.get('task_id', task_id) != task_id or data.get('parent_id') != parent_id:
            continue
        groups = [g for g in data.get('groups', {}).values()
                  if g.get('parameters', {}).get('enabled') is True]
        kinds = [g['parameters'].get('annotation_type') for g in groups]
        if not groups or len(kinds) != len(set(kinds)) or any(g['parameters'].get('filter') or g['parameters'].get('parent_requirement') is not None for g in groups):
            continue
        if any(g['parameters'].get('annotation_type') not in ('rectangle', 'polygon', 'tag', 'polyline', 'points') for g in groups):
            continue
        counts = [matrix_counts(g.get('comparison_summary', {}).get('confusion_matrix') or {})
                  if g.get('comparison_summary', {}).get('calculation', {}).get('status') == 'computed' else None for g in groups]
        if any(c is None for c in counts):
            continue
        tp, predicted, reference = (sum(c[i] for c in counts) for i in range(3))
        if not predicted + reference:
            continue
        stamp = meta.get('created_date')
        if not stamp:
            continue
        evaluations.append({'eval_id': f'cvat-qa:{meta["id"]}', 'job_id': jid,
                            'mean_iou': None, 'precision': tp/predicted if predicted else 0.0,
                            'recall': tp/reference if reference else 0.0,
                            'f1_score': 2*tp/(predicted+reference), 'evaluated_at': stamp})
        seen = set()
        for group in groups:
            for conflict in group.get('conflicts', []):
                frame = conflict.get('frame_id')
                job = job_map[jid]
                if type(frame) is not int or not job.get('start_frame', 0) <= frame <= job.get('stop_frame', -1):
                    continue
                refs = conflict.get('annotation_ids', [])
                identity = (frame, conflict.get('type'), tuple(sorted((str(r.get('job_id')), str(r.get('obj_id')), str(r.get('type'))) for r in refs)))
                if identity in seen:
                    continue
                seen.add(identity)
                label = next((shapes[(r.get('job_id'), r.get('obj_id'))].get('label_id') for r in refs if (r.get('job_id'), r.get('obj_id')) in shapes), None)
                kind = {'mismatching_label': 'wrong_class', 'missing_annotation': 'missing_object',
                        'extra_annotation': 'extra_annotation'}.get(conflict.get('type'), conflict.get('type', 'unclassified'))
                defects.append({'defect_id': f'cvat-qa:{meta["id"]}:{len(seen)}', 'review_id': None,
                                'job_id': jid, 'label_key': f'{task_id}:{label}' if label is not None else None,
                                'frame_idx': frame, 'defect_type': kind,
                                'severity': 'Major' if conflict.get('severity') == 'error' else 'Minor',
                                'cvat_deep_link': f'{host}/tasks/{task_id}/jobs/{jid}?frame={frame}'})
    if evaluations:
        warnings.append('CVAT QA: F1 derived from job confusion matrices on sampled Ground Truth; arithmetic mean across jobs. Geometry mIoU and human review history are not supplied. Automatic conflicts are not human review rounds; completed-frame defect density is unavailable for this sample.')
    return evaluations, defects, warnings
