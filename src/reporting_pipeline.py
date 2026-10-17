"""Snapshot -> validated canonical tables -> atomic SQLite publication -> Power BI CSV.

No credentials or live requests here. All rows, including dimensions, belong to a
snapshot. pbi_* views expose one published snapshot, so refresh cannot sum history.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import sqlite3
import uuid
from contextlib import closing, contextmanager, ExitStack
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from src.processors.geometry import measure_shape
from src.processors.models import Review, GroundTruthEval
from src.processors.quality import first_time_pass_rate, rejection_rate, avg_miou, avg_f1, normalize_defect_type

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / 'data' / 'annotation_reporting.db'
SCHEMA_VERSION = 2
TRANSFORM_VERSION = '2026-10-17.3'

# Canonical serving contract. CSVs, SQL views, M and DAX use these names.
TABLES = {
    'dim_annotators': {'annotator_id':'TEXT', 'full_name':'TEXT', 'username':'TEXT', 'role':'TEXT', 'joined_date':'TEXT'},
    'dim_reviewers': {'reviewer_id':'TEXT', 'full_name':'TEXT'},
    'dim_tasks_batches': {'task_id':'INTEGER', 'batch_id':'TEXT', 'task_name':'TEXT', 'total_frames_target':'INTEGER'},
    'dim_classes_labels': {'label_key':'TEXT', 'label_id':'INTEGER', 'task_id':'INTEGER', 'label_name':'TEXT', 'color_hex':'TEXT'},
    'dim_date': {'date_key':'TEXT', 'year':'INTEGER', 'month_num':'INTEGER', 'month_name':'TEXT', 'day_name':'TEXT', 'week_num':'INTEGER'},
    'dim_jobs': {'job_id':'INTEGER', 'task_id':'INTEGER', 'annotator_id':'TEXT', 'stage':'TEXT', 'state':'TEXT', 'frame_count':'INTEGER'},
    'fact_job_sessions': {'job_id':'INTEGER', 'task_id':'INTEGER', 'annotator_id':'TEXT', 'date_key':'TEXT', 'status':'TEXT', 'total_frames':'INTEGER', 'total_objects':'INTEGER', 'active_time_hours':'REAL'},
    'fact_annotations': {'annotation_id':'TEXT', 'job_id':'INTEGER', 'label_key':'TEXT', 'frame_idx':'INTEGER', 'shape_type':'TEXT', 'area_pixels':'REAL', 'frame_area_pct':'REAL', 'size_scale':'TEXT'},
    'fact_qa_reviews': {'review_id':'TEXT', 'job_id':'INTEGER', 'reviewer_id':'TEXT', 'review_iteration':'INTEGER', 'review_decision':'TEXT', 'reviewed_at':'TEXT'},
    'fact_qa_defects': {'defect_id':'TEXT', 'review_id':'TEXT', 'job_id':'INTEGER', 'label_key':'TEXT', 'frame_idx':'INTEGER', 'defect_type':'TEXT', 'severity':'TEXT', 'cvat_deep_link':'TEXT'},
    'fact_ground_truth_eval': {'eval_id':'TEXT', 'job_id':'INTEGER', 'mean_iou':'REAL', 'precision':'REAL', 'recall':'REAL', 'f1_score':'REAL', 'evaluated_at':'TEXT'},
    'fact_edge_cases': {'case_id':'TEXT', 'number':'INTEGER', 'task_id':'INTEGER', 'job_id':'INTEGER', 'title':'TEXT', 'description':'TEXT', 'labels':'TEXT', 'state':'TEXT', 'severity':'TEXT', 'frame':'INTEGER', 'link_status':'TEXT', 'cvat_deep_link':'TEXT', 'source_url':'TEXT'},
    'report_status': {'task_id':'INTEGER', 'as_of':'TEXT', 'is_demo':'INTEGER', 'source_snapshot':'TEXT', 'reviews_available':'INTEGER', 'defects_available':'INTEGER', 'hours_available':'INTEGER', 'annotations_available':'INTEGER', 'gt_available':'INTEGER', 'warnings':'TEXT'},
    'kpi_reconciliation': {'metric':'TEXT', 'expected_value':'REAL', 'unit':'TEXT'},
}
KEYS = {t: next(iter(c)) for t,c in TABLES.items()}
KEYS['report_status'] = 'task_id'
KEYS['kpi_reconciliation'] = 'metric'


def read_json(path: Path, default=None):
    return json.loads(path.read_text(encoding='utf-8-sig')) if path.exists() else default


def iso_date(value):
    return datetime.fromisoformat(value.replace('Z','+00:00')).date().isoformat() if value else None


def number(value, name, maximum=None):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (float,int)) or not math.isfinite(value) or value < 0 or (maximum is not None and value > maximum):
        raise ValueError(f'Invalid {name}: expected finite number in range, received {value!r}')
    return value


def ratio(a,b):
    return a / b if a is not None and b is not None and b > 0 else None


def source_frame_size(cvat, job_id, frame):
    """Only use explicit frame mapping, or a complete uniform-size media list."""
    record = next((r for r in cvat.get('media_metadata', []) if r.get('job_id') == job_id and r.get('status') == 'success'), None)
    if not record: return None
    meta = record.get('data', {})
    frames = meta.get('frames', [])
    selected = [f for f in frames if f.get('frame') == frame and frame is not None]
    if not selected:
        complete = len(frames) == meta.get('size') or (cvat.get('task', {}).get('mode') == 'interpolation' and len(frames) == 1)
        if complete and frames:
            dimensions = {(f.get('width'), f.get('height')) for f in frames}
            if len(dimensions) == 1: selected = [frames[0]]
    if len(selected) != 1: return None
    size = selected[0].get('width'), selected[0].get('height')
    try:
        return size if all(number(v, 'media dimension') is not None and v > 0 for v in size) else None
    except ValueError:
        return None


def build_tables(folder: Path, frame_size=None):
    manifest = read_json(folder/'manifest.json')
    cvat = read_json(folder/'cvat.json')
    if not isinstance(manifest,dict) or not isinstance(cvat,dict):
        raise ValueError('Snapshot requires manifest.json and cvat.json')
    if any(manifest.get('sources',{}).get(s,{}).get('status') != 'success' for s in ('cvat','github')):
        raise ValueError('Both CVAT and GitHub sources must succeed before publishing')
    github = read_json(folder/'github.json')
    if not isinstance(github,dict):
        raise ValueError('Successful GitHub source requires github.json')
    operations = read_json(folder/'operations.json',{})
    if operations and operations.get('schema_version') != 1:
        raise ValueError('operations.json requires schema_version=1')
    if frame_size and (len(frame_size)!=2 or any(number(v,'frame size') == 0 for v in frame_size)):
        raise ValueError('Frame size must contain two positive numbers')
    scope = manifest.get('scope',{})
    task = cvat.get('task',{})
    tid = task.get('id')
    if not isinstance(tid,int) or isinstance(tid,bool) or tid <= 0 or scope.get('task_id',tid) != tid:
        raise ValueError('Task ID missing or disagrees with manifest')
    started = manifest.get('started_at')
    if not started:
        raise ValueError('Snapshot requires started_at')
    as_of = date.fromisoformat(iso_date(started))
    rows = {t:[] for t in TABLES}
    warnings = ['Completed frames are a job-state proxy, not a count of QA-accepted unique frames.']
    repo = scope.get('repo','')
    host = scope.get('cvat_host','').rstrip('/')
    users = {}
    jobs = []
    for j in cvat.get('jobs',[]):
        if j.get('type','annotation') != 'annotation':
            continue
        if j.get('task_id',tid) != tid:
            raise ValueError('Job belongs to another task')
        jobs.append(j)
        person=j.get('assignee')
        if person and person.get('id') is not None:
            aid=str(person['id'])
            users[aid]={'annotator_id':aid,'full_name':(' '.join([person.get('first_name',''),person.get('last_name','')])).strip() or person.get('username',aid),'username':person.get('username'),'role':'Annotator','joined_date':person.get('joined_date')}
    job_ids = {j['id'] for j in jobs}
    times={}
    for r in operations.get('job_times',[]):
        jid=r['job_id']
        if jid not in job_ids or jid in times:
            raise ValueError('Unknown or duplicate job_times.job_id')
        number(r.get('active_time_hours'),'active_time_hours')
        if r.get('completed_at'): iso_date(r['completed_at'])
        times[jid]=r
    records={}
    for r in cvat.get('annotations',[]):
        if r.get('job_id') in job_ids:
            if r['job_id'] in records: raise ValueError('Duplicate annotation payload for job')
            records[r['job_id']]=r
    annotations_available=all(records.get(jid,{}).get('status')=='success' for jid in job_ids)
    if not annotations_available:
        warnings.append('Annotations incomplete; publication stopped to prevent partial geometry totals.')
        raise ValueError(warnings[-1])
    label_map={l['id']:l for l in cvat.get('labels',[])}
    for lid,l in label_map.items():
        rows['dim_classes_labels'].append({'label_key':f'{tid}:{lid}','label_id':lid,'task_id':tid,'label_name':l.get('name',str(lid)),'color_hex':l.get('color')})
    for j in jobs:
        jid=j['id']; payload=records[jid]['data']
        drawn=[]
        for idx,s in enumerate(payload.get('shapes',[])):
            if not s.get('outside',False): drawn.append((f'{jid}:shape:{s.get("id",idx)}',s,s.get('label_id')))
        for ti,tr in enumerate(payload.get('tracks',[])):
            for ki,s in enumerate(tr.get('shapes',[])):
                if not s.get('outside',False): drawn.append((f'{jid}:track:{tr.get("id",ti)}:{s.get("frame",ki)}',s,tr.get('label_id')))
        for aid,s,lid in drawn:
            if lid not in label_map: raise ValueError(f'Unknown annotation label {lid}')
            shape_type=s.get('type','')
            pts=s.get('points',[])
            for coordinate in pts:
                if not isinstance(coordinate,(float,int)) or not math.isfinite(coordinate): raise ValueError('Invalid shape coordinate')
            # Open polylines have no filled area. No invented bbox or frame dimensions.
            dimensions = frame_size or source_frame_size(cvat, jid, s.get('frame')) or (0,0)
            g=measure_shape(shape_type if shape_type!='polyline' else 'unsupported',pts,*dimensions)
            rows['fact_annotations'].append({'annotation_id':aid,'job_id':jid,'label_key':f'{tid}:{lid}','frame_idx':s.get('frame'),'shape_type':shape_type,'area_pixels':g.area_pixels,'frame_area_pct':g.frame_area_pct,'size_scale':g.size_scale})
        person=j.get('assignee') or {}
        annotator_id=str(person['id']) if person.get('id') is not None else None
        status='completed' if j.get('state')=='completed' or (not j.get('state') and j.get('status')=='completed') else ('validation' if j.get('stage') in ('validation','acceptance') else 'annotation')
        fc=number(j.get('frame_count'),'frame_count')
        if fc is None or int(fc)!=fc: raise ValueError('Annotation jobs require integer frame_count')
        rows['dim_jobs'].append({'job_id':jid,'task_id':tid,'annotator_id':annotator_id,'stage':j.get('stage'),'state':j.get('state'),'frame_count':fc})
        rows['fact_job_sessions'].append({'job_id':jid,'task_id':tid,'annotator_id':annotator_id,'date_key':iso_date(times.get(jid,{}).get('completed_at')) if status=='completed' else None,'status':status,'total_frames':fc,'total_objects':len(drawn),'active_time_hours':times.get(jid,{}).get('active_time_hours')})
    rows['dim_annotators']=list(users.values())
    target=number(task.get('size'),'task.size')
    if target is None: raise ValueError('Task target frame count is required')
    rows['dim_tasks_batches']=[{'task_id':tid,'batch_id':str(task.get('batch_id') or f'Task-{tid}'),'task_name':task.get('name',str(tid)),'total_frames_target':target}]
    ranges=sorted((j['start_frame'],j['stop_frame']) for j in jobs if j.get('start_frame') is not None and j.get('stop_frame') is not None)
    if any(a[1]>=b[0] for a,b in zip(ranges,ranges[1:])):
        raise ValueError('Annotation job frame ranges overlap; unique-frame aggregation is required')
    if sum(j['total_frames'] for j in rows['fact_job_sessions']) > target:
        raise ValueError('Sum of annotation job frames exceeds task size; resolve overlap before publication')
    if len(ranges)!=len(jobs): warnings.append('Job frame ranges unavailable; confirm that annotation jobs do not overlap.')

    reviewers={}
    rounds=set()
    for r in operations.get('reviews',[]):
        if r['job_id'] not in job_ids: raise ValueError('Review references unknown annotation job')
        key=(r['job_id'],r['review_iteration'])
        if key in rounds or not isinstance(r['review_iteration'],int) or r['review_iteration']<1: raise ValueError('Duplicate or invalid review iteration')
        rounds.add(key)
        if r['review_decision'] not in ('Accepted','Rejected'): raise ValueError('Invalid review decision')
        reviewer=str(r['reviewer_id']); reviewers[reviewer]={'reviewer_id':reviewer,'full_name':r.get('reviewer_name',reviewer)}
        if r.get('reviewed_at'): iso_date(r['reviewed_at'])
        rows['fact_qa_reviews'].append({**r,'reviewer_id':reviewer})
    rows['dim_reviewers']=list(reviewers.values())
    reviews_by_id={r['review_id']:r for r in rows['fact_qa_reviews']}
    for d in operations.get('defects',[]):
        if d['review_id'] not in reviews_by_id: raise ValueError('Defect references unknown review')
        jid=reviews_by_id[d['review_id']]['job_id']; lid=d.get('label_id')
        if lid is not None and lid not in label_map: raise ValueError('Defect references unknown label')
        severity=d.get('severity','Minor')
        if severity not in ('Blocker','Major','Minor'): raise ValueError('Invalid defect severity')
        rows['fact_qa_defects'].append({**d,'job_id':jid,'label_key':f'{tid}:{lid}' if lid is not None else None,'severity':severity,'defect_type':normalize_defect_type(d['defect_type']),'cvat_deep_link':f'{host}/tasks/{tid}/jobs/{jid}?frame={d["frame_idx"]}' if host else None})
    # Multiple evaluations must carry a timestamp; take the latest per job.
    gt_by_job={}
    for e in operations.get('ground_truth_evals',[]):
        jid=e['job_id']
        if jid not in job_ids: raise ValueError('GT references unknown job')
        if not e.get('evaluated_at'): raise ValueError('GT requires evaluated_at')
        stamp=datetime.fromisoformat(e['evaluated_at'].replace('Z','+00:00'))
        if stamp.tzinfo is None: stamp=stamp.replace(tzinfo=timezone.utc)
        for k in ('mean_iou','precision','recall','f1_score'): number(e.get(k),k,1)
        e=dict(e)
        if e.get('f1_score') is None and e.get('precision') is not None and e.get('recall') is not None:
            e['f1_score']=ratio(2*e['precision']*e['recall'],e['precision']+e['recall'])
        if jid not in gt_by_job or stamp>gt_by_job[jid][0]: gt_by_job[jid]=(stamp,e)
    rows['fact_ground_truth_eval']=[e for _,e in gt_by_job.values()]

    from src.processors.normalizer import normalize_snapshot
    report=normalize_snapshot(manifest,cvat,github,read_json(folder/'links.json',[]),folder,manifest.get('mentor_session'))
    warnings.extend(report['metadata']['warnings'])
    cases={}
    for group in ('edge_cases','open_questions','blockers'):
        for item in report[group]['items']:
            cases[item['number']]=item
    for no,item in cases.items():
        labels=item['labels']; jid=item.get('job_id')
        link_status = item.get('link_status')
        link = item.get('cvat_job_url')
        linked_job = next((j for j in jobs if j['id'] == jid), None)
        frame = item.get('frame')
        if linked_job and frame is not None and linked_job.get('start_frame') is not None and linked_job.get('stop_frame') is not None:
            if not linked_job['start_frame'] <= frame <= linked_job['stop_frame']:
                link_status = 'invalid_frame'; link = None
                warnings.append(f'Issue #{no} references a frame outside its job range; CVAT URL suppressed.')
        rows['fact_edge_cases'].append({'case_id':f'{repo}#{no}','number':no,'task_id':tid,'job_id':jid if jid in job_ids else None,'title':item.get('title'),'description':item.get('description'),'labels':', '.join(labels),'state':item.get('state'),'severity':'Blocker' if 'blocker' in labels else None,'frame':frame,'link_status':link_status,'cvat_deep_link':link,'source_url':item.get('source_url')})
    if any(a['area_pixels'] is not None and a['frame_area_pct'] is None for a in rows['fact_annotations']): warnings.append('Frame dimensions missing for some records; their frame_area_pct is null.')
    for source, result in cvat.get('optional_sources', {}).items():
        if result.get('status') in ('failed','partial'): warnings.append(f'Optional CVAT source {source} is {result["status"]}.')
    if cvat.get('quality_reports_data', {}).get('status') in ('failed','partial'):
        warnings.append('CVAT quality report data is incomplete; inspect raw quality_reports_data.')
    hours_available=bool(jobs) and all(j['active_time_hours'] is not None for j in rows['fact_job_sessions'])
    if not hours_available: warnings.append('Active time incomplete; velocity and AHT are unavailable.')
    if any(j['status']=='completed' and j['date_key'] is None for j in rows['fact_job_sessions']): warnings.append('Completion timestamps missing; daily production excludes undated jobs.')
    availability=operations.get('availability',{})
    reviews_available=availability.get('reviews') is True
    defects_available=availability.get('defects') is True
    gt_available=availability.get('ground_truth') is True
    if rows['fact_qa_reviews'] and not reviews_available: raise ValueError('Reviews require availability.reviews=true')
    if rows['fact_qa_defects'] and not defects_available: raise ValueError('Defects require availability.defects=true')
    if rows['fact_ground_truth_eval'] and not gt_available: raise ValueError('GT requires availability.ground_truth=true')
    if not reviews_available: warnings.append('Review history unavailable; FTPR and rejection remain null.')
    if not defects_available: warnings.append('Defect history unavailable; missing defects do not mean zero defects.')
    if not gt_available: warnings.append('Ground Truth evaluations unavailable.')
    rows['report_status']=[{'task_id':tid,'as_of':as_of.isoformat(),'is_demo':int(manifest.get('fixture') is True),'source_snapshot':str(folder.resolve()),'reviews_available':int(reviews_available),'defects_available':int(defects_available),'hours_available':int(hours_available),'annotations_available':int(annotations_available),'gt_available':int(gt_available),'warnings':' | '.join(warnings)}]
    dates=[as_of]+[date.fromisoformat(j['date_key']) for j in rows['fact_job_sessions'] if j['date_key']]
    current=date(min(dates).year,1,1); last=date(max(dates).year,12,31)
    while current<=last:
        rows['dim_date'].append({'date_key':current.isoformat(),'year':current.year,'month_num':current.month,'month_name':current.strftime('%B'),'day_name':current.strftime('%A'),'week_num':current.isocalendar()[1]})
        current+=timedelta(days=1)
    review_models=[Review(**{k:r.get(k) for k in ('review_id','job_id','reviewer_id','review_iteration','review_decision')}) for r in rows['fact_qa_reviews']]
    gt_models=[GroundTruthEval(**{k:r.get(k) for k in ('eval_id','job_id','mean_iou','precision','recall','f1_score')}) for r in rows['fact_ground_truth_eval']]
    completed=sum(j['total_frames'] for j in rows['fact_job_sessions'] if j['status']=='completed')
    hours=sum(j['active_time_hours'] or 0 for j in rows['fact_job_sessions']) if hours_available else None
    nobjects=len(rows['fact_annotations']); ndefects=len(rows['fact_qa_defects']) if defects_available else None
    areas=[a['area_pixels'] for a in rows['fact_annotations'] if a['area_pixels'] is not None]
    frame_pcts=[a['frame_area_pct'] for a in rows['fact_annotations'] if a['frame_area_pct'] is not None]
    scales=[a['size_scale'] for a in rows['fact_annotations'] if a['size_scale'] is not None]
    expected={
        'Total_Completed_Frames':(completed,'frames (job proxy)'), 'Total_Objects_Created':(nobjects,'drawn records'),
        'Total_Active_Hours':(hours,'hours'), 'Velocity_Frames_Per_Hour':(ratio(completed,hours),'frames/hour'),
        'Velocity_Objects_Per_Hour':(ratio(nobjects,hours),'records/hour'),
        'Avg_Time_Per_Frame_Mins':(ratio(hours*60 if hours is not None else None,completed),'minutes/frame'),
        'Avg_Time_Per_Object_Secs':(ratio(hours*3600 if hours is not None else None,nobjects),'seconds/record'),
        'First_Time_Pass_Rate':(first_time_pass_rate(review_models) if reviews_available else None,'ratio'),
        'Rejection_Rate':(rejection_rate(review_models) if reviews_available else None,'ratio'),
        'Total_Defects':(ndefects,'defects'), 'Defect_Density_Per_100F':(ratio(ndefects*100 if ndefects is not None else None,completed),'defects/100 frames'),
        'Avg_Defects_Per_Job':(ratio(ndefects,len({r.job_id for r in review_models})) if reviews_available else None,'defects/job'),
        'Avg_mIoU_Score':(avg_miou(gt_models) if gt_available else None,'ratio'),
        'Avg_F1_Score':(avg_f1(gt_models) if gt_available else None,'ratio'),
        'Avg_Object_Area_Pixels':(sum(areas)/len(areas) if areas else None,'pixels^2'),
        'Avg_Area_Frame_Pct':(sum(frame_pcts)/len(frame_pcts)/100 if frame_pcts else None,'ratio'),
        'Pct_Small_Objects':(ratio(scales.count('Small'),len(scales)),'ratio'),
        'Project_Progress_Pct':(ratio(completed,target),'ratio'),
        'System_Avg_Velocity':(ratio(completed,hours),'frames/hour'),
    }
    at_risk=0; evaluated_people=0
    for aid in users:
        ids={j['job_id'] for j in rows['fact_job_sessions'] if j['annotator_id']==aid}
        rs=[r for r in review_models if r.job_id in ids]; gs=[g for g in gt_models if g.job_id in ids]
        ftpr=first_time_pass_rate(rs) if reviews_available else None
        rr=rejection_rate(rs) if reviews_available else None
        f1=avg_f1(gs) if gt_available else None
        if any(v is not None for v in (ftpr,rr,f1)):
            evaluated_people+=1
            at_risk+=int((ftpr is not None and ftpr<.8) or (rr is not None and rr>=.2) or (f1 is not None and f1<.85))
    expected['Count_At_Risk_Annotators']=(at_risk if evaluated_people else None,'people')
    rows['kpi_reconciliation']=[{'metric':k,'expected_value':v,'unit':u} for k,(v,u) in expected.items()]
    for table,values in rows.items():
        seen=set()
        for r in values:
            key=r.get(KEYS[table])
            if key is None or key in seen: raise ValueError(f'Missing/duplicate key in {table}: {key}')
            seen.add(key)
    payload={'manifest':manifest,'cvat':cvat,'github':github,'links':read_json(folder/'links.json',[]),'operations':operations,'team_reports':read_json(folder/'team_reports.json',[]),'frame_size':frame_size,'schema_version':SCHEMA_VERSION,'transform_version':TRANSFORM_VERSION}
    sid='S'+hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:24]
    # A replay has the same identity even when copied into a new run folder.
    # Absolute run paths belong in run receipts, not immutable serving rows.
    rows['report_status'][0]['source_snapshot']=sid
    return sid,rows,payload


@contextmanager
def publication_lock(path):
    """OS releases this lock on process exit; no stale PID lock recovery needed."""
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a+b') as handle:
        handle.seek(0,2)
        if handle.tell()==0: handle.write(b'0'); handle.flush()
        handle.seek(0)
        try:
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(),fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise ValueError('Another publication is running. Wait for it to finish, then retry.') from None
        try:
            yield
        finally:
            handle.seek(0)
            if os.name=='nt': msvcrt.locking(handle.fileno(),msvcrt.LK_UNLCK,1)
            else: fcntl.flock(handle.fileno(),fcntl.LOCK_UN)


def _file_digest(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''): digest.update(chunk)
    return digest.hexdigest()


def _prepare_bundle(output_dir,sid,rows):
    """Write a complete new directory; never rewrite a bundle already being read."""
    root=Path(output_dir)/'snapshots'; root.mkdir(parents=True,exist_ok=True)
    bundle=root/sid
    staging=root/('.partial-'+uuid.uuid4().hex); staging.mkdir()
    hashes={}
    for name,columns in TABLES.items():
        target=staging/(name+'.csv')
        with target.open('w',encoding='utf-8-sig',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=list(columns),extrasaction='ignore')
            writer.writeheader(); writer.writerows(rows[name])
        hashes[name+'.csv']=_file_digest(target)
    (staging/'bundle.json').write_text(json.dumps({'snapshot_id':sid,'sha256':hashes},indent=2),encoding='utf-8')
    if bundle.exists():
        for name,digest in hashes.items():
            if not (bundle/name).is_file() or _file_digest(bundle/name)!=digest:
                raise ValueError('Existing CSV snapshot is incomplete or modified: '+sid)
        # Only remove files created in this invocation, within the staging directory.
        for child in staging.iterdir(): child.unlink()
        staging.rmdir()
    else:
        staging.replace(bundle)
    return bundle


def publish_snapshot(folder: Path, db_path: Path=DEFAULT_DB, output_dir: Path | None=None, frame_size=None):
    """Validate, serialize writers, stage immutable CSVs, then switch publication."""
    db_path=Path(db_path)
    sid,rows,payload=build_tables(Path(folder),frame_size)
    locks={db_path.resolve().with_suffix('.publish.lock')}
    if output_dir: locks.add(Path(output_dir).resolve()/'.publish.lock')
    with ExitStack() as stack:
        for path in sorted(locks,key=str): stack.enter_context(publication_lock(path))
        return _publish_tables(sid,rows,payload,db_path,output_dir)


def _publish_tables(sid,rows,payload,db_path,output_dir):
    bundle=_prepare_bundle(output_dir,sid,rows) if output_dir else None
    db_path.parent.mkdir(parents=True,exist_ok=True)
    with closing(sqlite3.connect(db_path)) as conn, conn:
        conn.execute('PRAGMA foreign_keys=ON')
        conn.execute('CREATE TABLE IF NOT EXISTS bronze_snapshots (snapshot_id TEXT PRIMARY KEY, created_at TEXT NOT NULL, manifest_json TEXT NOT NULL, raw_json TEXT NOT NULL)')
        conn.execute('CREATE TABLE IF NOT EXISTS serving_state (id INTEGER PRIMARY KEY CHECK(id=1), snapshot_id TEXT NOT NULL REFERENCES bronze_snapshots(snapshot_id))')
        previous=conn.execute('SELECT snapshot_id FROM serving_state WHERE id=1').fetchone()
        conn.execute('CREATE TABLE IF NOT EXISTS silver_entities (snapshot_id TEXT NOT NULL, entity_type TEXT NOT NULL, entity_id TEXT NOT NULL, payload_json TEXT NOT NULL, PRIMARY KEY(snapshot_id,entity_type,entity_id))')
        existed=conn.execute('SELECT 1 FROM bronze_snapshots WHERE snapshot_id=?',(sid,)).fetchone()
        if not existed:
            conn.execute('INSERT INTO bronze_snapshots VALUES (?,?,?,?)',(sid,datetime.now(timezone.utc).isoformat(),json.dumps(payload['manifest'],ensure_ascii=False),json.dumps(payload,ensure_ascii=False)))
        for name,columns in TABLES.items():
            definition=', '.join(f'"{k}" {t}' for k,t in columns.items())
            conn.execute(f'CREATE TABLE IF NOT EXISTS gold_{name} (snapshot_id TEXT NOT NULL, {definition}, PRIMARY KEY(snapshot_id,"{KEYS[name]}"))')
            conn.execute(f'CREATE VIEW IF NOT EXISTS pbi_{name} AS SELECT t.* FROM gold_{name} t JOIN serving_state s ON t.snapshot_id=s.snapshot_id WHERE s.id=1')
            if not existed:
                fields=['snapshot_id']+list(columns)
                sql=f'INSERT INTO gold_{name} ({",".join(fields)}) VALUES ({",".join("?" for _ in fields)})'
                conn.executemany(sql,[(sid,)+tuple(r.get(k) for k in columns) for r in rows[name]])
                if name.startswith('fact_'):
                    conn.executemany('INSERT INTO silver_entities VALUES (?,?,?,?)',[(sid,name,str(r[KEYS[name]]),json.dumps(r,ensure_ascii=False)) for r in rows[name]])
        conn.execute('INSERT INTO serving_state VALUES (1,?) ON CONFLICT(id) DO UPDATE SET snapshot_id=excluded.snapshot_id',(sid,))
    # SQLite and the filesystem cannot share a transaction. Compensate a failed
    # pointer switch so serving views keep their previous snapshot on normal errors.
    if output_dir:
        output_dir=Path(output_dir)
        pointer=output_dir/('current.'+uuid.uuid4().hex+'.tmp')
        try:
            pointer.write_text(json.dumps({'schema_version':SCHEMA_VERSION,'snapshot_id':sid,'folder':str(bundle.resolve()),'relative_folder':'snapshots/'+sid,'is_demo':bool(rows['report_status'][0]['is_demo'])},indent=2),encoding='utf-8')
            pointer.replace(output_dir/'current.json')
        except OSError:
            with closing(sqlite3.connect(db_path)) as conn, conn:
                if previous: conn.execute('UPDATE serving_state SET snapshot_id=? WHERE id=1',previous)
                else: conn.execute('DELETE FROM serving_state WHERE id=1')
            raise
    return {'snapshot_id':sid,'database':str(db_path.resolve()),'tables':{k:len(v) for k,v in rows.items()},'warnings':rows['report_status'][0]['warnings']}
