"""Add synthetic reference jobs and request server-computed QA for seeded tasks."""
import json
import os
from pathlib import Path
import requests
from dotenv import load_dotenv

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/cvat_realistic_seed'


def main():
    load_dotenv(ROOT/'.env')
    session=requests.Session()
    session.headers['Authorization']='Bearer '+os.environ['CVAT_TOKEN']
    host=os.environ['CVAT_HOST'].rstrip('/')
    results=[]

    def api(method,path,**kwargs):
        r=session.request(method,host+path,timeout=(15,90),allow_redirects=False,**kwargs)
        if r.status_code not in (200,201,202):
            raise RuntimeError(f'{method} {path}: HTTP {r.status_code}: {r.text[:250]}')
        return r.json()

    receipt=json.loads((OUT/'seed_receipt.json').read_text())
    for task in receipt['tasks']:
        tid=task['id']
        remote=api('GET',f'/api/tasks/{tid}')
        if remote['project_id']!=455373: raise RuntimeError('Unexpected project')
        jobs=api('GET',f'/api/jobs?task_id={tid}&page_size=100')['results']
        gt=next((j for j in jobs if j['type']=='ground_truth'),None)
        frames=list(range(0,120,10))
        if gt is None:
            gt=api('POST','/api/jobs',json={'task_id':tid,'type':'ground_truth',
                   'frame_selection_method':'manual','frames':frames})
        labels=api('GET',f'/api/labels?task_id={tid}&page_size=100')['results']
        ids={x['name']:x['id'] for x in labels}
        truth=json.loads((OUT/f'batch_{task["batch"]}/reference_geometry.json').read_text())
        shapes=[]
        for item in truth:
            if item['frame'] not in frames: continue
            shape={k:v for k,v in item.items() if k!='label'}
            shape.update(label_id=ids[item['label']],attributes=[],source='manual',rotation=0,z_order=0)
            shapes.append(shape)
        api('PUT',f'/api/jobs/{gt["id"]}/annotations',json={'version':0,'tags':[],'shapes':shapes,'tracks':[]})
        api('PATCH',f'/api/jobs/{gt["id"]}',json={'stage':'acceptance','state':'completed'})
        response=api('POST','/api/quality/reports',json={'task_id':tid})
        record={'task_id':tid,'ground_truth_job_id':gt['id'],'reference_frames':frames,
                'verified_reference_shapes':len(api('GET',f'/api/jobs/{gt["id"]}/annotations')['shapes']),
                'quality_request':response}
        results.append(record)
        (OUT/'ground_truth_receipt.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
        print(json.dumps(record),flush=True)


if __name__=='__main__': main()
