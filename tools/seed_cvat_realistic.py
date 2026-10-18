"""Seed only the dedicated synthetic CVAT project; resume from a local receipt."""
import argparse
import json
import os
from pathlib import Path
import time
import zipfile

from dotenv import load_dotenv
from PIL import Image, ImageDraw
import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/cvat_realistic_seed'
PROJECT = 455373
LABELS = ['car', 'pedestrian', 'cyclist', 'truck', 'traffic_sign', 'motorbike']


def save(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding='utf-8')


def prepare():
    OUT.mkdir(parents=True, exist_ok=True)
    for batch in range(3):
        folder = OUT / f'batch_{batch+1}'
        folder.mkdir(exist_ok=True)
        truth = []
        for frame in range(120):
            image = Image.new('RGB', (960, 540), ['#bcd9eb', '#45536b', '#b6bcc2'][batch])
            draw = ImageDraw.Draw(image)
            draw.rectangle((0, 210, 960, 540), fill='#48505a')
            for x in range(0, 960, 120):
                draw.rectangle((x, 370, x+65, 377), fill='#eeeecc')
            draw.text((15, 15), f'SYNTHETIC TEST ONLY | batch {batch+1} | frame {frame:04}', fill='white')
            shapes = []
            for k in range(6):
                w, h = [(20, 25), (55, 75), (140, 90)][(frame+k)%3]
                x = 25 + (frame*13+k*143)%740
                y = 225 + (frame*7+k*29)%190
                box = [x, y, x+w, y+h]
                color = ['#e53935','#43a047','#00acc1','#fb8c00','#8e24aa','#1e88e5'][k]
                draw.rectangle(box, fill=color, outline='white', width=2)
                draw.text((x+2,y+2), LABELS[k], fill='white')
                polygon = k == 4 and frame%2 == 0
                points = [x,y,x+w,y,x+w,y+h,x,y+h] if polygon else box
                shapes.append({'frame':frame,'type':'polygon' if polygon else 'rectangle',
                               'label':LABELS[k],'points':points,'occluded':(frame+k)%7==0})
            image.save(folder / f'synthetic_{frame:04}.png')
            truth.extend(shapes)
        save(folder/'reference_geometry.json', truth)
        with zipfile.ZipFile(OUT/f'batch_{batch+1}.zip','w',zipfile.ZIP_DEFLATED) as archive:
            for file in sorted(folder.glob('*.png')):
                archive.write(file,file.name)
    save(OUT/'plan.json', {'synthetic':True,'project_id':PROJECT,'frames':360,'tasks':3,
         'planned_annotation_jobs':18,'labels':LABELS,'roles_pending':['supervisor','annotator','reviewer'],
         'note':'Reference geometry is synthetic, not a measured CVAT quality report. No fabricated work hours or review history.'})
    print('Prepared 360 synthetic images and geometry reference',flush=True)


def seed():
    load_dotenv(ROOT/'.env')
    host=os.environ['CVAT_HOST'].rstrip('/')
    session=requests.Session()
    session.headers['Authorization']='Bearer '+os.environ['CVAT_TOKEN']
    receipt_path=OUT/'seed_receipt.json'
    receipt=json.loads(receipt_path.read_text()) if receipt_path.exists() else {'project_id':PROJECT,'tasks':[]}

    def api(method,path,**kwargs):
        response=session.request(method,host+path,timeout=(15,120),allow_redirects=False,**kwargs)
        if response.status_code not in (200,201,202):
            raise RuntimeError(f'{method} {path}: HTTP {response.status_code}: {response.text[:350]}')
        return response.json() if response.content else {}

    project=api('GET',f'/api/projects/{PROJECT}')
    if not project['name'].startswith('SYNTHETIC E2E - Urban Mobility QA'):
        raise RuntimeError('Unexpected project; refusing writes')
    labels=api('GET',f'/api/labels?project_id={PROJECT}&page_size=100')['results']
    label_ids={label['name']:label['id'] for label in labels}
    for batch in range(3):
        entry=next((x for x in receipt['tasks'] if x['batch']==batch+1),None)
        if entry is None:
            try:
                task=api('POST','/api/tasks',json={'name':f'SYNTHETIC Batch {batch+1} - '+['Day traffic','Night occlusion','Rain mixed scale'][batch],
                         'project_id':PROJECT,'segment_size':20,'overlap':0})
            except RuntimeError as error:
                if 'maximum number of tasks' not in str(error): raise
                receipt['task_quota_limit']=True
                save(receipt_path,receipt)
                break
            entry={'batch':batch+1,'id':task['id'],'uploaded':False,'jobs':[]}
            receipt['tasks'].append(entry); save(receipt_path,receipt)
        tid=entry['id']
        if not entry['uploaded']:
            if not entry.get('upload_requested'):
                with (OUT/f'batch_{batch+1}.zip').open('rb') as file:
                    result=api('POST',f'/api/tasks/{tid}/data',data={'image_quality':90,'sorting_method':'lexicographical'},
                               files={'client_files[0]':(f'batch_{batch+1}.zip',file,'application/zip')})
                entry['upload_requested']=result; save(receipt_path,receipt)
            for _ in range(90):
                task=api('GET',f'/api/tasks/{tid}')
                if task.get('size')==120: break
                time.sleep(2)
            else: raise RuntimeError(f'Task {tid} upload not ready; resume later')
            entry['uploaded']=True; save(receipt_path,receipt)
        jobs=api('GET',f'/api/jobs?task_id={tid}&page_size=100')['results']
        jobs=sorted((j for j in jobs if j.get('type','annotation')=='annotation'),key=lambda j:j['start_frame'])
        truth=json.loads((OUT/f'batch_{batch+1}/reference_geometry.json').read_text())
        for index,job in enumerate(jobs):
            jid=job['id']
            if any(x['id']==jid for x in entry['jobs']): continue
            # Leave one job new, one partially annotated, others fully populated.
            stop=job['stop_frame'] if index!=4 else job['start_frame']+9
            selected=[] if index==5 else [s for s in truth if job['start_frame']<=s['frame']<=stop]
            payload=[]
            for shape in selected:
                s={k:v for k,v in shape.items() if k!='label'}
                s.update(label_id=label_ids[shape['label']],attributes=[],source='manual',z_order=0,rotation=0)
                payload.append(s)
            api('PUT',f'/api/jobs/{jid}/annotations',json={'version':0,'tags':[],'shapes':payload,'tracks':[]})
            stage,state=[('acceptance','completed'),('validation','new'),('validation','in progress'),
                         ('annotation','rejected'),('annotation','in progress'),('annotation','new')][index%6]
            api('PATCH',f'/api/jobs/{jid}',json={'stage':stage,'state':state})
            issue=api('POST','/api/issues',json={'job':jid,'frame':job['start_frame'],
                'position':[50,240,190,330],'message':f'[SYNTHETIC QA TEST] {['wrong class','boundary displacement','missing object','occlusion dispute','small object','pending annotation'][index%6]}; batch {batch+1}. Test fixture, not a production defect.',
                'resolved':index==0})
            record={'id':jid,'start_frame':job['start_frame'],'stop_frame':job['stop_frame'],
                    'stage':stage,'state':state,'shapes':len(payload),'issue_id':issue['id']}
            entry['jobs'].append(record); save(receipt_path,receipt)
            print(json.dumps({'task':tid,**record}),flush=True)
        actual=api('GET',f'/api/tasks/{tid}/annotations')
        entry['verified_shapes']=len(actual['shapes']); entry['verified_frames']=api('GET',f'/api/tasks/{tid}')['size']
        save(receipt_path,receipt)
    receipt['status']='seeded_and_read_back'; receipt['real_role_assignment']='pending: only one visible account'
    save(receipt_path,receipt)
    print(json.dumps(receipt),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--apply',action='store_true'); args=parser.parse_args()
    if args.apply: seed()
    else: prepare()
