"""Configured demo/offline/live ingestion -> reports -> PostgreSQL -> DirectQuery."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
import secrets
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from src.main import atomic_json
from src.reporting_pipeline import publication_lock
from src.desktop_config import load_settings

STATE=ROOT/'data/directquery'


def desktop_configuration_verified(report,settings=None):
    """Local acceptance applies only to the exact PBIX observed in Desktop."""
    try:
        ready=json.loads((STATE/'desktop_ready.json').read_text(encoding='utf-8'))
        return (report.suffix.lower()=='.pbix' and ready.get('status') in ('verified','user_confirmed')
                and ready.get('automatic_page_refresh_seconds')==(settings or {}).get('refresh_seconds',10)
                and ready.get('endpoint','127.0.0.1:55432')=='127.0.0.1:'+str((settings or {}).get('port',55432))
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


def configuration(settings=None):
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
    config['port']=(settings or {}).get('port',55432)
    (STATE/'postgres.env').write_text('ANNOTATION_PG_OWNER_PASSWORD='+config['owner_password']+'\nANNOTATION_PG_PORT='+str(config['port'])+'\n',encoding='utf-8')
    atomic_json(STATE/'powerbi_connection.json',{'server':'127.0.0.1:'+str(config['port']),'database':'annotation_reporting','username':'annotation_reader','password':config['reader_password']})
    return config


def ensure_docker():
    if not shutil.which('docker'): raise RuntimeError('Docker CLI missing. Install Docker Desktop and reopen the launcher.')
    command(['docker','compose','version'],timeout=10)
    try: command(['docker','info','--format','{{.ServerVersion}}'],timeout=10)
    except RuntimeError:
        command(['docker','desktop','start','--detach'],timeout=15)
        for attempt in range(45):
            try:
                command(['docker','info','--format','{{.ServerVersion}}'],timeout=3)
                return
            except RuntimeError: time.sleep(1)
        raise RuntimeError('Docker engine is not running. Open Docker Desktop and resolve its startup message.')


def check_port(port):
    """Never replace another container or claim its occupied endpoint."""
    result=subprocess.run(['docker','inspect','annotation-reporter-db'],capture_output=True,text=True,timeout=10)
    if result.returncode==0:
        container=json.loads(result.stdout)[0]
        labels=container.get('Config',{}).get('Labels') or {}
        if labels.get('com.docker.compose.project')!='annotation-reporter-auto':
            raise RuntimeError('Container name annotation-reporter-db belongs to another project. Resolve the name conflict first.')
        if not (STATE/'connection.json').is_file():
            raise RuntimeError('An existing reporting database has credentials from another checkout. Use its original checkout or restore its data/directquery credentials; do not delete its volume.')
        bindings=container.get('NetworkSettings',{}).get('Ports',{}).get('5432/tcp') or []
        if container.get('State',{}).get('Running') and any(b['HostPort']==str(port) and b['HostIp']=='127.0.0.1' for b in bindings): return
    with socket.socket() as probe:
        try: probe.bind(('127.0.0.1',port))
        except OSError: raise RuntimeError('Reporting port is occupied. Choose another port in config/desktop.local.json.') from None


def pipeline_arguments(settings):
    arguments=['--llm-summary','--verify','--no-brief','--notify','preview']
    mode=settings['mode']
    if mode=='demo':
        from powerbi.create_demo_snapshot import create_demo
        snapshot=create_demo(STATE/'demo_snapshot',completed_jobs=settings['completed_jobs'])
        arguments+=['--mode','offline','--snapshot',str(snapshot),'--session','Power BI Auto Demo']
    elif mode=='offline':
        arguments+=['--mode','offline','--snapshot',settings['snapshot'],'--session','Power BI Snapshot Report']
    else:
        arguments+=['--mode','live','--session','Power BI Live Report']
        if settings['task_id']: arguments+=['--task-id',str(settings['task_id'])]
        if settings['repo']: arguments+=['--repo',settings['repo']]
    if mode!='demo':
        for key,flag in [('operations','--operations'),('team_reports','--team-reports')]:
            if settings[key]: arguments += [flag,settings[key]]
    return arguments


def validate_source(settings):
    if settings['mode']=='offline':
        if not settings['snapshot'] or not (Path(settings['snapshot'])/'manifest.json').is_file() or not (Path(settings['snapshot'])/'cvat.json').is_file():
            raise ValueError('Offline mode needs a snapshot folder containing manifest.json and cvat.json')
    if settings['mode']!='demo':
        for key in ('operations','team_reports'):
            if settings[key] and not Path(settings[key]).is_file(): raise ValueError(key+' file not found')
    if settings['mode']=='live':
        from dotenv import load_dotenv
        import re
        from urllib.parse import urlsplit
        load_dotenv(ROOT/'.env')
        task=settings['task_id'] or os.getenv('CVAT_TASK_ID','')
        repo=settings['repo'] or os.getenv('GITHUB_REPO','')
        token=os.getenv('CVAT_TOKEN','').strip()
        host=urlsplit(os.getenv('CVAT_HOST',''))
        if not str(task).isdigit() or int(task)<=0 or not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repo):
            raise ValueError('Configure a positive CVAT_TASK_ID and GITHUB_REPO=OWNER/REPO for live mode')
        if not token or token.startswith('your_') or host.scheme not in ('http','https') or not host.hostname or host.hostname.endswith('example.org'):
            raise ValueError('Configure real CVAT_HOST and CVAT_TOKEN in .env; never put tokens in desktop.local.json')


def report_for(settings):
    if settings['port']==55432 and settings['refresh_seconds']==10:
        project=ROOT/'powerbi/project_auto/AnnotationReporter.pbip'
        preferred=ROOT/'powerbi/AnnotationReporter_Auto.pbix'
    else:
        folder=STATE/'reports'/f"p{settings['port']}-r{settings['refresh_seconds']}"
        project=folder/'AnnotationReporter.pbip'
        preferred=folder/'AnnotationReporter_Auto.pbix'
    if not project.exists() and not preferred.exists():
        from powerbi.build_directquery_project import build
        build(project.parent,settings['port'],settings['refresh_seconds'])
    return preferred if preferred.exists() else project


def doctor(settings):
    checks={'python':sys.version.split()[0],'platform':sys.platform,'mode':settings['mode'],
            'endpoint':'127.0.0.1:'+str(settings['port']),'refresh_seconds':settings['refresh_seconds'],
            'docker_cli':bool(shutil.which('docker'))}
    for label,arguments in [('docker_engine',['docker','info','--format','{{.ServerVersion}}']),('docker_compose',['docker','compose','version'])]:
        try:
            result=subprocess.run(arguments,capture_output=True,timeout=10)
            checks[label]=result.returncode==0
        except (OSError,subprocess.TimeoutExpired): checks[label]=False
    try: validate_source(settings); checks['source_configuration']=True
    except (ValueError,ImportError): checks['source_configuration']=False
    checks['desktop_note']='Power BI Desktop must be installed, and source credentials entered once on each Windows machine.'
    if os.name=='nt':
        import winreg
        associated=False
        for hive,path in [(winreg.HKEY_CURRENT_USER,r'Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\.pbix\UserChoice'),(winreg.HKEY_CLASSES_ROOT,'.pbix')]:
            try:
                with winreg.OpenKey(hive,path): associated=True
            except OSError: pass
        checks['pbix_file_association']=associated
    if checks.get('docker_engine'):
        try: check_port(settings['port']); checks['reporting_port']=True
        except (RuntimeError,OSError,subprocess.TimeoutExpired): checks['reporting_port']=False
    print(json.dumps(checks,ensure_ascii=False,indent=2))
    required=['docker_cli','docker_engine','docker_compose','source_configuration','reporting_port']
    if os.name=='nt': required.append('pbix_file_association')
    return 0 if all(checks.get(k) for k in required) else 1


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--setup',action='store_true',help='Install the optional Python PostgreSQL driver if missing')
    parser.add_argument('--open-report',action='store_true')
    parser.add_argument('--doctor',action='store_true',help='Inspect prerequisites without publishing or starting Docker')
    parser.add_argument('--confirm-desktop',action='store_true',help='Record YOUR confirmation after saving PBIX and observing visuals update on this machine; does not prove DAX reconciliation')
    parser.add_argument('--config',type=Path)
    parser.add_argument('--mode',choices=['demo','offline','live'])
    parser.add_argument('--port',type=int)
    parser.add_argument('--refresh-seconds',type=int)
    parser.add_argument('--completed-jobs',type=int,choices=range(16))
    parser.add_argument('--snapshot')
    parser.add_argument('--task-id',type=int)
    parser.add_argument('--repo')
    parser.add_argument('--operations')
    parser.add_argument('--team-reports')
    args=parser.parse_args()
    STATE.mkdir(parents=True,exist_ok=True)
    stage='startup'
    try:
        settings=load_settings(args.config,{key:getattr(args,key) for key in ('mode','port','refresh_seconds','completed_jobs','snapshot','task_id','repo','operations','team_reports')})
        if args.doctor: return doctor(settings)
        if args.confirm_desktop:
            with publication_lock(STATE/'.auto-run.lock'):
                from src.desktop_acceptance import confirm
                confirm(settings,report_for(settings),configuration(settings))
            return 0
        if args.open_report and os.name!='nt': raise RuntimeError('Desktop launcher requires Windows. Omit --open-report for data-only publication.')
        with publication_lock(STATE/'.auto-run.lock'):
            print('[0/4] Checking the local runtime and Docker engine...',flush=True)
            if any(importlib.util.find_spec(module) is None for module in ('pg8000','requests','dotenv')):
                if not args.setup: raise RuntimeError('Install requirements-auto.txt or run with --setup once')
                command([sys.executable,'-m','pip','install','-r',str(ROOT/'requirements-auto.txt')],timeout=180)
            validate_source(settings)
            ensure_docker()
            check_port(settings['port'])
            config=configuration(settings)
            stage='database_startup'
            print('[1/4] Starting the dedicated local reporting database...',flush=True)
            command(['docker','compose','--env-file',str(STATE/'postgres.env'),'-f',str(ROOT/'infra/directquery/compose.yaml'),'up','-d','--wait','--wait-timeout','90'],timeout=240)
            print('[2/4] Source mode: '+settings['mode']+'. Generating canonical reports...',flush=True)
            stage='canonical_pipeline'
            from src.main import main as run_pipeline
            with publication_lock(ROOT/'data/.demo-run.lock'):
                code=run_pipeline(pipeline_arguments(settings))
            if code: raise RuntimeError('Canonical pipeline failed; DirectQuery serving data was not changed')
            print('[3/4] Publishing the immutable snapshot to DirectQuery...',flush=True)
            stage='directquery_publication'
            from src.directquery_store import publish
            publication=publish(config)
            report=report_for(settings)
            receipt=json.loads((ROOT/'data/runs/latest.json').read_text(encoding='utf-8'))
            receipt.update(directquery=publication,desktop_status='database_published_waiting_for_visuals',report_path=str(report))
            receipt['source_mode']=settings['mode']
            receipt['desktop_configuration_verified']=desktop_configuration_verified(report,settings)
            receipt['refresh_seconds']=settings['refresh_seconds']
            atomic_json(Path(receipt['run_folder'])/'run_status.json',receipt)
            atomic_json(ROOT/'data/runs/latest.json',receipt)
            atomic_json(STATE/'latest.json',receipt)
            print('[4/4] Database published: '+publication['snapshot_id'],flush=True)
            print('Report: '+str(report))
            if not receipt['desktop_configuration_verified']:
                print('ONE-TIME SETUP: enter credentials from data/directquery/powerbi_connection.json in Desktop. Page refresh is configured in the project; confirm visuals update on this machine.')
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
