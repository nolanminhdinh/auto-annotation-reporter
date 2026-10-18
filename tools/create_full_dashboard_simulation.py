"""Create a clearly marked local dashboard simulation; never write to CVAT."""
import argparse
import copy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def create(source, destination):
    destination.mkdir(parents=True, exist_ok=False)
    manifest, cvat = read(source/'manifest.json'), read(source/'cvat.json')
    jobs = sorted([j for j in cvat['jobs'] if j.get('type') == 'annotation'], key=lambda j: j['start_frame'])
    if len(jobs) != 6:
        raise ValueError('This scenario requires the six-job CVAT acceptance snapshot')
    now = datetime.now(timezone.utc)
    tid = cvat['task']['id']
    manifest.update(fixture=True, content_provenance='full_local_simulation_from_cvat_test_snapshot',
                    simulation={'is_simulated':True, 'source_snapshot':str(source.resolve()),
                                'fields':['assignees','job_states','annotations_for_pending_job','hours','review_history','defects','ground_truth_scores','completion_dates','team_reports','extra_issues'],
                                'external_writes':False})
    manifest['started_at'] = now.isoformat()
    manifest['finished_at'] = now.isoformat()
    cvat['task']['name'] = 'MÔ PHỎNG ĐẦY ĐỦ | Urban Mobility QA'
    operations = {'schema_version':1, 'is_simulated':True,
                  'provenance':'Synthetic benchmark only; not observed human work or measured GT evaluation.',
                  'availability':{'reviews':True,'defects':True,'ground_truth':True},
                  'job_times':[], 'reviews':[], 'defects':[], 'ground_truth_evals':[]}
    label_ids = [l['id'] for l in cvat['labels']]
    hours = [.25,.5,1,2,1.5,.75]
    iou = [.94,.80,.90,.73,.68,.92]
    precision = [.97,.88,.95,.82,.77,.96]
    recall = [.95,.80,.91,.74,.65,.94]
    for index, job in enumerate(jobs):
        jid = job['id']
        day = now.date() - timedelta(days=7-index)
        stamp = lambda hour: f'{day.isoformat()}T{hour:02d}:00:00Z'
        job['assignee'] = {'id':800001+index, 'username':f'sim_annotator_{index+1:02d}',
                           'first_name':'Mô phỏng', 'last_name':f'Gán nhãn {index+1:02d}',
                           'joined_date':'2026-09-01'}
        job['stage'], job['state'] = ('acceptance','completed') if index < 4 else [('annotation','rejected'),('acceptance','in progress')][index-4]
        operations['job_times'].append({'job_id':jid, 'active_time_hours':hours[index],
                                        'completed_at':stamp(15) if index<4 else None})
        reviewer = f'SIM_REVIEWER_{"A" if index%2==0 else "B"}'
        rejected = index in (1,3,4)
        first_id = f'SIM_R{jid}_1'
        operations['reviews'].append({'review_id':first_id, 'job_id':jid,'reviewer_id':reviewer,
                                     'reviewer_name':f'MÔ PHỎNG · QA {reviewer[-1]}','review_iteration':1,
                                     'review_decision':'Rejected' if rejected else 'Accepted','reviewed_at':stamp(12)})
        if rejected and index<4:
            operations['reviews'].append({'review_id':f'SIM_R{jid}_2','job_id':jid,'reviewer_id':reviewer,
                                         'reviewer_name':f'MÔ PHỎNG · QA {reviewer[-1]}','review_iteration':2,
                                         'review_decision':'Accepted','reviewed_at':stamp(14)})
        # Defect-density numerator belongs only to the completed, fully reviewed jobs.
        for k in range([1,3,1,4,0,0][index]):
            operations['defects'].append({'defect_id':f'SIM_D{jid}_{k}','review_id':first_id,
                'frame_idx':job['start_frame']+k,'label_id':label_ids[k%len(label_ids)],
                'defect_type':['box_displacement','wrong_class','missing_object','wrong_attr'][k%4],
                'severity':['Minor','Major','Blocker'][k%3]})
        operations['ground_truth_evals'].append({'eval_id':f'SIM_GT{jid}','job_id':jid,
            'mean_iou':iou[index],'precision':precision[index],'recall':recall[index],
            'f1_score':2*precision[index]*recall[index]/(precision[index]+recall[index]),
            'evaluated_at':stamp(16)})

    # Populate the originally empty annotation job locally using synthetic reference geometry.
    reference = read(ROOT/'data/cvat_realistic_seed/batch_1/reference_geometry.json')
    label_map = {l['name']:l['id'] for l in cvat['labels']}
    last = jobs[-1]
    record = next(r for r in cvat['annotations'] if r['job_id']==last['id'])
    shapes=[]
    for i, shape in enumerate(reference):
        if not last['start_frame']<=shape['frame']<=last['stop_frame']:
            continue
        item={k:copy.deepcopy(v) for k,v in shape.items() if k!='label'}
        item.update(id=900000000+i,label_id=label_map[shape['label']],attributes=[],source='manual',z_order=0,rotation=0)
        shapes.append(item)
    record['data']['shapes']=shapes
    cvat['jobs']=[j for j in cvat['jobs'] if j.get('type')!='annotation']+jobs

    github = read(source/'github.json')
    links = read(source/'links.json')
    host = manifest['scope']['cvat_host'].rstrip('/')
    for index, (label,title) in enumerate([
        ('blocker','Ảnh ngược sáng cần thống nhất cách xử lý'),
        ('mentor-question','Thống nhất quy tắc đối tượng bị che khuất'),
        ('ca-kho','Phân biệt cyclist và pedestrian ở vùng xa')]):
        job=jobs[index]; no=900001+index; frame=job['start_frame']+2
        url=f'{host}/tasks/{tid}/jobs/{job["id"]}?frame={frame}'
        github['issues'].append({'number':no,'title':'[MÔ PHỎNG] '+title,'state':'open',
            'labels':[{'name':label}],'body':'Tình huống mô phỏng local để thử dashboard; chưa tạo issue trên GitHub. '+title,
            'user':{'login':'sim_manager'},'html_url':None})
        links.append({'github_issue':no,'cvat_task_id':tid,'cvat_job_id':job['id'],'frame':frame,
                      'status':'verified','relationship_verified':True,'simulation':True})
    teams=[{'report_id':f'SIM_TR_{i+1:02d}','team':team,'reporter':'sim_manager',
            'report_text':'[MÔ PHỎNG] '+text,'reported_at':now.isoformat()} for i,(team,text) in enumerate([
                ('Tổ gán nhãn','Đã hoàn thành bốn jobs; hai jobs đang xử lý và chờ nghiệm thu.'),
                ('Tổ QA','Đã mô phỏng tám vòng review, có trường hợp trả về và duyệt lại.'),
                ('Tổ quản lý','Blocker mô phỏng: cần thống nhất cách xử lý ảnh ngược sáng; đề nghị mentor chốt guideline.')])]
    for name,value in [('manifest.json',manifest),('cvat.json',cvat),('github.json',github),
                       ('links.json',links),('operations.json',operations),('team_reports.json',teams)]:
        save(destination/name,value)
    save(destination/'simulation_receipt.json',{'source':str(source.resolve()),'destination':str(destination.resolve()),
        'annotation_jobs':6,'simulated_annotators':6,'simulated_reviewers':2,'completed_jobs':4,
        'reviews':len(operations['reviews']),'defects':len(operations['defects']),
        'ground_truth_evals':6,'external_writes':False})
    return destination


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path)
    parser.add_argument('--destination',type=Path,default=ROOT/'data/dashboard_simulation_full')
    args=parser.parse_args()
    source=args.source or Path(read(ROOT/'data/runs/latest.json')['run_folder'])
    print(create(source,args.destination))
