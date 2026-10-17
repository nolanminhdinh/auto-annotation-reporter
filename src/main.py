"""One entrypoint for live/offline ingestion, reporting and Power BI publication."""
from __future__ import annotations
import argparse
import json
import os
import shutil
import sqlite3
from contextlib import closing
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from src.reporting_pipeline import DEFAULT_DB, publish_snapshot, read_json


def atomic_json(path,payload):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    temporary.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    temporary.replace(path)


def finish_run(run_root,destination,publication,notification):
    receipt={'status':'data_and_reports_ready','completed_at_utc':datetime.now(timezone.utc).isoformat(),
             'snapshot_id':publication['snapshot_id'],'run_folder':str(destination.resolve()),
             'mentor_report':str((destination/'MENTOR_REPORT_DRAFT.md').resolve()),
             'notification':notification,'desktop_status':'refresh_and_save_required'}
    atomic_json(destination/'run_status.json',receipt)
    atomic_json(run_root/'latest.json',receipt)

def frame_size(value):
    try:
        width,height=map(int,value.lower().split('x'))
        if width<=0 or height<=0: raise ValueError()
        return width,height
    except ValueError:
        raise argparse.ArgumentTypeError('Use positive WIDTHxHEIGHT, e.g. 1920x1080')

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=['offline','live'],default='offline')
    parser.add_argument('--snapshot',type=Path,help='Offline source snapshot; defaults to sample_data/powerbi_demo')
    parser.add_argument('--task-id',type=int)
    parser.add_argument('--repo')
    parser.add_argument('--session',default='Mentor report')
    parser.add_argument('--operations',type=Path,help='Optional validated time/review/GT supplement')
    parser.add_argument('--team-reports',type=Path,help='Optional team_reports.json')
    parser.add_argument('--llm-summary',action='store_true',help='Include evidence-linked team synthesis (offline extraction by default)')
    parser.add_argument('--summary-provider',choices=['offline','gemini'],default='offline',help='Gemini is used only when explicitly selected in live mode')
    parser.add_argument('--notify',choices=['none','preview','telegram','discord'],default='none',help='Remote channels send a real message; preview only writes a local draft')
    parser.add_argument('--dashboard-url',help='Optional HTTPS dashboard URL for notification preview')
    parser.add_argument('--frame-size',type=frame_size)
    parser.add_argument('--db',type=Path,default=DEFAULT_DB)
    parser.add_argument('--output',type=Path,default=ROOT/'data'/'runs')
    parser.add_argument('--powerbi-output',type=Path,default=ROOT/'data'/'processed')
    parser.add_argument('--export-powerbi',action='store_true',help='Compatibility flag; publication is always included')
    args=parser.parse_args(argv)
    from src.sync import run_pipeline
    run_root=args.output.resolve()
    destination=None; result=None
    try:
        from src.notifiers.bot import format_message,send_message
        if args.dashboard_url: format_message({'snapshot_id':'pending'},{},False,args.dashboard_url)
        if args.mode=='offline':
            source=(args.snapshot or ROOT/'sample_data'/'powerbi_demo').resolve()
            if not source.is_dir(): raise ValueError(f'Snapshot not found: {source}')
            destination=run_root/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
            destination.mkdir(parents=True,exist_ok=False)
            atomic_json(destination/'run_status.json',{'status':'running','mode':args.mode})
            for name in ('manifest.json','cvat.json','github.json','links.json','operations.json','team_reports.json'):
                if (source/name).exists(): shutil.copyfile(source/name,destination/name)
            manifest=read_json(destination/'manifest.json',{})
            manifest['mentor_session']=args.session
            (destination/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
            if args.operations: shutil.copyfile(args.operations,destination/'operations.json')
            code=run_pipeline(offline_snapshot=destination,session_name=args.session)
        else:
            run_root.mkdir(parents=True,exist_ok=True)
            destination=run_root/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
            destination.mkdir(parents=True,exist_ok=False)
            atomic_json(destination/'run_status.json',{'status':'running','mode':args.mode})
            code=run_pipeline(task_id=args.task_id,repo=args.repo,session_name=args.session,output_dir=run_root,snapshot_folder=destination)
            if args.operations: shutil.copyfile(args.operations,destination/'operations.json')
        if code:
            atomic_json(destination/'run_status.json',{'status':'source_failed','exit_code':code})
            return code
        if args.team_reports: shutil.copyfile(args.team_reports,destination/'team_reports.json')
        team_summary=None
        if args.llm_summary:
            from src.generators.team_summary import synthesize
            team_summary=synthesize(
                read_json(destination/'team_reports.json',[]),
                provider=args.summary_provider if args.mode=='live' else 'offline',
                api_key=os.getenv('GEMINI_API_KEY'),model=os.getenv('GEMINI_MODEL'),
            )
            (destination/'team_summary.json').write_text(json.dumps(team_summary,ensure_ascii=False,indent=2),encoding='utf-8')
        result=publish_snapshot(destination,args.db,args.powerbi_output,args.frame_size)
        with closing(sqlite3.connect(args.db)) as conn:
            metrics=conn.execute('SELECT metric,expected_value,unit FROM gold_kpi_reconciliation WHERE snapshot_id=?',(result['snapshot_id'],)).fetchall()
            demo=conn.execute('SELECT is_demo FROM gold_report_status WHERE snapshot_id=?',(result['snapshot_id'],)).fetchone()[0]
        headline='DEMO — DỮ LIỆU GIẢ LẬP' if demo else 'SNAPSHOT NGUỒN — CẦN NHÓM TRƯỞNG DUYỆT'
        summary=['## '+headline,'','| KPI đối chiếu Power BI | Giá trị | Đơn vị |','|---|---:|---|']
        summary.extend('| '+name+' | '+('Chưa đủ dữ liệu' if value is None else f'{value:.6g}')+' | '+unit+' |' for name,value,unit in metrics)
        summary.extend(['','> '+result['warnings'],''])
        draft=destination/'MENTOR_REPORT_DRAFT.md'
        original=draft.read_text(encoding='utf-8')
        title,_,body=original.partition('\n')
        draft.write_text(title+'\n\n'+'\n'.join(summary)+'\n'+body,encoding='utf-8')
        if team_summary is not None:
            from src.generators.team_summary import markdown
            with draft.open('a',encoding='utf-8') as f: f.write('\n---\n\n'+markdown(team_summary))
        (destination/'publication.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        message=format_message(result,{name:value for name,value,_ in metrics},bool(demo),args.dashboard_url)
        (destination/'notification_preview.txt').write_text(message,encoding='utf-8')
        receipt={'status':'not_requested' if args.notify=='none' else 'preview_only'}
        if args.notify in ('telegram','discord'):
            try:
                receipt=send_message(args.notify,message,os.environ)
            except (ValueError,RuntimeError) as error:
                receipt={'channel':args.notify,'status':'failed_or_unconfirmed','error':str(error)}
                (destination/'notification_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
                finish_run(run_root,destination,result,receipt)
                print(f'Data published, but notification did not complete: {error}',file=sys.stderr)
                return 2
        (destination/'notification_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
        finish_run(run_root,destination,result,receipt)
        print(json.dumps(result,ensure_ascii=False,indent=2))
        print('Power BI: refresh AnnotationReporter; CSV bundle: '+str(args.powerbi_output/'current.json'))
        return 0
    except (ValueError,OSError,KeyError,TypeError,sqlite3.Error) as error:
        if destination is not None and destination.is_dir():
            try:
                atomic_json(destination/'run_status.json',{'status':'failed_after_publication' if result else 'failed_before_publication','error_type':type(error).__name__,'snapshot_id':result['snapshot_id'] if result else None})
            except OSError: pass
        print(f'Pipeline did not complete: {error}',file=sys.stderr)
        return 1

if __name__=='__main__': raise SystemExit(main())
