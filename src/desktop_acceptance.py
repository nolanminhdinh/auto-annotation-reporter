"""Record a user's explicit Desktop observation; never claim automated visual QA."""
import hashlib
import json
import zipfile
from datetime import datetime, timezone
from src.main import atomic_json
from src.directquery_store import connect
from src.desktop_config import ROOT


def confirm(settings,report,config):
    if report.suffix.lower()!='.pbix':
        raise ValueError('Save the configured project as AnnotationReporter_Auto.pbix in the same folder first')
    state=ROOT/'data/directquery'
    latest=json.loads((state/'latest.json').read_text(encoding='utf-8'))
    if latest['directquery']['endpoint']!='127.0.0.1:'+str(settings['port']):
        raise ValueError('Publish with the selected port before confirming Desktop')
    pages=[]
    with zipfile.ZipFile(report) as archive:
        for name in archive.namelist():
            if name.startswith('Report/definition/pages/') and name.endswith('/page.json'):
                page=json.loads(archive.read(name))
                properties=page.get('objects',{}).get('pageRefresh',[{}])[0].get('properties',{})
                if (properties.get('show',{}).get('expr',{}).get('Literal',{}).get('Value')!='true'
                    or properties.get('duration',{}).get('expr',{}).get('Literal',{}).get('Value')!=f"'PT{settings['refresh_seconds']}S'"):
                    raise ValueError('Save the configured Page refresh settings on every page before confirming')
                pages.append(page['displayName'])
    if len(pages)!=5: raise ValueError('Expected five report pages')
    connection=connect(config,reader=True)
    try:
        cursor=connection.cursor()
        cursor.execute('SELECT source_snapshot FROM pbi_report_status')
        source=cursor.fetchone()[0]
    finally: connection.close()
    if source!=latest['snapshot_id']: raise ValueError('Serving snapshot changed; rerun the launcher before confirming')
    atomic_json(state/'desktop_ready.json',{
        'status':'user_confirmed','checked_at':datetime.now(timezone.utc).isoformat(),
        'report':str(report),'report_sha256':hashlib.sha256(report.read_bytes()).hexdigest(),
        'endpoint':'127.0.0.1:'+str(settings['port']),
        'automatic_page_refresh_seconds':settings['refresh_seconds'],'configured_pages':pages,
        'snapshot_id':source,'visual_observation':'User explicitly confirmed using --confirm-desktop',
        'dax_reconciliation':'not_checked_by_this_command',
    })
    print('Recorded your Desktop confirmation. PBIX page refresh and database identity checked; no automated visual or DAX acceptance claimed.')
