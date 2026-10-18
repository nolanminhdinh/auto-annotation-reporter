"""One command: demo ingestion -> reports -> PostgreSQL -> automatic DirectQuery visuals."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
import secrets
import subprocess
import sys
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from src.main import atomic_json
from src.reporting_pipeline import publication_lock

STATE=ROOT/'data/directquery'


def desktop_configuration_verified(report):
    """Local acceptance applies only to the exact PBIX observed in Desktop."""
    try:
        ready=json.loads((STATE/'desktop_ready.json').read_text(encoding='utf-8'))
        return (report.suffix.lower()=='.pbix' and ready.get('status')=='verified'
                and ready.get('report_sha256')==hashlib.sha256(report.read_bytes()).hexdigest())
    except (OSError,ValueError):
        return False


def command(arguments,timeout=120):
    try:
        result=subprocess.run(arguments,cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout)
    except (OSError,subprocess.TimeoutExpired):
        raise RuntimeError('Unable to run '+arguments[0]+' within the time limit') from None
    if result.returncode:
        STATE.mkdir(parents=True,exist_ok=True)
        (STATE/'last_process_error.log').write_text(result.stderr,encoding='utf-8')
        raise RuntimeError(arguments[0]+' command failed; see data/directquery/last_process_error.log')
    return result.stdout


def configuration():
    STATE.mkdir(parents=True,exist_ok=True)
    path=STATE/'connection.json'
    if path.exists():
        config=json.loads(path.read_text(encoding='utf-8'))
        if config.get('version')!=1 or any(not isinstance(config.get(k),str) or not config[k] for k in ('owner_password','reader_password')):
            raise ValueError('Invalid local DirectQuery configuration')
    else:
        config={'version':1,'owner_password':secrets.token_urlsafe(32),'reader_password':secrets.token_urlsafe(32)}
        atomic_json(path,config)
    # Keep credentials only in ignored runtime files, never in PBIP or command arguments.
    (STATE/'postgres.env').write_text('ANNOTATION_PG_OWNER_PASSWORD='+config['owner_password']+'\n',encoding='utf-8')
    atomic_json(STATE/'powerbi_connection.json',{'server':'127.0.0.1:55432','database':'annotation_reporting','username':'annotation_reader','password':config['reader_password']})
    return config


def ensure_docker():
    try: command(['docker','info','--format','{{.ServerVersion}}'],timeout=10)
    except RuntimeError:
        command(['docker','desktop','start','--detach'],timeout=15)
        for attempt in range(45):
            try:
                command(['docker','info','--format','{{.ServerVersion}}'],timeout=3)
                return
            except RuntimeError: time.sleep(1)
        raise RuntimeError('Docker engine is not running. Open Docker Desktop and resolve its startup message.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--setup',action='store_true',help='Install the optional Python PostgreSQL driver if missing')
    parser.add_argument('--open-report',action='store_true')
    parser.add_argument('--completed-jobs',type=int,choices=range(16),default=10)
    args=parser.parse_args()
    STATE.mkdir(parents=True,exist_ok=True)
    stage='startup'
    try:
        with publication_lock(STATE/'.auto-run.lock'):
            print('[0/4] Checking the local runtime and Docker engine...',flush=True)
            if importlib.util.find_spec('pg8000') is None:
                if not args.setup: raise RuntimeError('Install requirements-auto.txt or run with --setup once')
                command([sys.executable,'-m','pip','install','-r',str(ROOT/'requirements-auto.txt')],timeout=180)
            ensure_docker()
            config=configuration()
            stage='database_startup'
            print('[1/4] Starting the dedicated local reporting database...',flush=True)
            command(['docker','compose','--env-file',str(STATE/'postgres.env'),'-f',str(ROOT/'infra/directquery/compose.yaml'),'up','-d','--wait','--wait-timeout','90'],timeout=240)
            print('[2/4] Creating demo data and generating the canonical reports...',flush=True)
            stage='canonical_pipeline'
            from powerbi.create_demo_snapshot import create_demo
            from src.main import main as run_pipeline
            with publication_lock(ROOT/'data/.demo-run.lock'):
                snapshot=create_demo(STATE/'demo_snapshot',completed_jobs=args.completed_jobs)
                code=run_pipeline(['--snapshot',str(snapshot),'--session','Power BI Auto Demo','--llm-summary','--verify','--no-brief','--notify','preview'])
            if code: raise RuntimeError('Canonical pipeline failed; DirectQuery serving data was not changed')
            print('[3/4] Publishing the immutable snapshot to DirectQuery...',flush=True)
            stage='directquery_publication'
            from src.directquery_store import publish
            publication=publish(config)
            project=ROOT/'powerbi/project_auto/AnnotationReporter.pbip'
            if not project.exists():
                from powerbi.build_directquery_project import build
                build(project.parent)
            preferred=ROOT/'powerbi/AnnotationReporter_Auto.pbix'
            report=preferred if preferred.exists() else project
            receipt=json.loads((ROOT/'data/runs/latest.json').read_text(encoding='utf-8'))
            receipt.update(directquery=publication,desktop_status='database_published_waiting_for_visuals',report_path=str(report))
            atomic_json(Path(receipt['run_folder'])/'run_status.json',receipt)
            atomic_json(ROOT/'data/runs/latest.json',receipt)
            atomic_json(STATE/'latest.json',receipt)
            print('[4/4] Database published: '+publication['snapshot_id'],flush=True)
            print('Report: '+str(report))
            if not desktop_configuration_verified(report):
                print('ONE-TIME SETUP PENDING: connect using data/directquery/powerbi_connection.json, enable automatic page refresh, and save AnnotationReporter_Auto.pbix.')
            else:
                print('DirectQuery with automatic page refresh is configured. The active page reads new data without import Refresh or data Save.')
            if args.open_report:
                stage='open_report'
                if os.name!='nt': raise RuntimeError('Open the DirectQuery project in Power BI Desktop on Windows')
                try:
                    with report.open('r+b'): pass
                except PermissionError:
                    print('Report already in use or read-only; no duplicate opened.')
                    return 0
                os.startfile(str(report))
        return 0
    except Exception as error:
        # Driver exceptions can contain SQL/credentials: record only the type for unknown failures.
        message=str(error) if isinstance(error,(ValueError,RuntimeError)) else type(error).__name__
        sqlstate=error.args[0].get('C') if error.args and isinstance(error.args[0],dict) else None
        failure={'status':'failed','stage':stage,'error_type':type(error).__name__,'sqlstate':sqlstate}
        try: atomic_json(STATE/'last_failure.json',failure)
        except OSError: pass
        if sqlstate: message+=' (SQLSTATE '+sqlstate+')'
        print('Automatic run did not complete: '+message,file=sys.stderr)
        return 1


if __name__=='__main__': raise SystemExit(main())
