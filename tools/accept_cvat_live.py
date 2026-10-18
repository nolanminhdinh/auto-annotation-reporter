"""Read-only live CVAT acceptance, isolated from serving data and demo reports."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))

from dotenv import load_dotenv
from src.extractors.cvat_extractor import CVATExtractor


def save(path,payload):
    path.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--task-id',type=int,required=True)
    parser.add_argument('--host',help='Defaults to CVAT_HOST in .env')
    parser.add_argument('--org',help='Defaults to CVAT_ORG in .env')
    parser.add_argument('--expected-frames',type=int,help='Expected task size from the UI/fixture')
    parser.add_argument('--expected-shapes',type=int,help='Expected saved API shape count from the UI/fixture')
    args=parser.parse_args()
    if any(v is not None and v<0 for v in (args.expected_frames,args.expected_shapes)):
        parser.error('Expected counts cannot be negative')
    load_dotenv(ROOT/'.env')
    token=os.getenv('CVAT_TOKEN','').strip()
    host=(args.host or os.getenv('CVAT_HOST','')).rstrip('/')
    if args.task_id<=0 or not host or not token or token.startswith('your_'):
        print('Configure CVAT_HOST and CVAT_TOKEN in .env and provide a positive --task-id. Never send the token in chat.',file=sys.stderr)
        return 1
    started=datetime.now(timezone.utc)
    folder=ROOT/'data/live_acceptance/cvat'/started.strftime('%Y%m%dT%H%M%S%fZ')
    folder.mkdir(parents=True,exist_ok=False)
    receipt={'started_at':started.isoformat(),'task_id':args.task_id,'read_only':True,
             'scope':'CVAT extractor only; no GitHub extraction, warehouse publication or Desktop acceptance',
             'status':'running'}
    save(folder/'acceptance.json',receipt)
    extractor=None
    try:
        extractor=CVATExtractor(host,token,args.org if args.org is not None else os.getenv('CVAT_ORG'))
        payload=extractor.extract_snapshot(args.task_id)
        save(folder/'cvat.json',payload)
        jobs=[job for job in payload['jobs'] if job.get('type','annotation')=='annotation']
        records={record['job_id']:record for record in payload['annotations']}
        failed=[job['id'] for job in jobs if records.get(job['id'],{}).get('status')!='success']
        core={'task_identity':payload['task']['id']==args.task_id,
              'has_annotation_jobs':bool(jobs),'all_annotation_jobs_downloaded':not failed}
        summary=extractor.summarize_annotations([records[j['id']] for j in jobs if j['id'] in records],payload['labels'])
        if args.expected_frames is not None: core['expected_task_frames']=payload['task'].get('size')==args.expected_frames
        if args.expected_shapes is not None: core['expected_saved_shapes']=summary['totals']['shapes']==args.expected_shapes
        optional=payload.get('optional_sources',{})
        quality=payload.get('quality_reports_data',{})
        limitations=[]
        for source,status in optional.items():
            if status.get('status')!='available': limitations.append(source+': '+str(status.get('status')))
        if quality.get('status')!='available': limitations.append('quality_reports: '+str(quality.get('status')))
        non_annotation_failures=[r['job_id'] for r in payload['annotations'] if r['job_id'] not in {j['id'] for j in jobs} and r['status']!='success']
        if non_annotation_failures: limitations.append('Non-annotation job payload failures; see raw snapshot')
        receipt.update(status='failed' if not all(core.values()) else 'passed_with_limitations' if limitations else 'passed',
                       checks=core,annotation_job_count=len(jobs),failed_annotation_job_ids=failed,
                       counts={key:len(payload[key]) for key in ('jobs','labels','issues','comments','annotations','media_metadata')},
                       annotation_summary=summary,
                       optional_sources=optional,quality_reports_status=quality.get('status'),
                       quality_list_sources=quality.get('list_sources',{}),limitations=limitations,
                       ui_comparison='pending manual comparison with the selected task in CVAT')
    except Exception as error:
        receipt.update(status='failed',error_type=type(error).__name__)
        if isinstance(getattr(error,'status_code',None),int): receipt['http_status']=error.status_code
    finally:
        if extractor is not None: extractor.close()
    receipt['finished_at']=datetime.now(timezone.utc).isoformat()
    save(folder/'acceptance.json',receipt)
    print(json.dumps({'status':receipt['status'],'task_id':args.task_id,'folder':str(folder),
                      'checks':receipt.get('checks'),'limitations':receipt.get('limitations',[]),
                      'error_type':receipt.get('error_type'),'http_status':receipt.get('http_status')},ensure_ascii=False,indent=2))
    return 1 if receipt['status']=='failed' else 2 if receipt['status']=='passed_with_limitations' else 0


if __name__=='__main__': raise SystemExit(main())
