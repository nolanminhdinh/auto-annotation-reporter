"""Validate PBIR JSON against Microsoft's public schemas (requires network)."""
import argparse
import hashlib
import json
from pathlib import Path
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from jsonschema import Draft7Validator
from referencing import Registry,Resource
from referencing.jsonschema import DRAFT7

ROOT=Path(__file__).resolve().parents[1]
CACHE=ROOT/'scratch'/'pbi_schemas'
SESSION=requests.Session()
SESSION.mount('https://',HTTPAdapter(max_retries=Retry(total=2,backoff_factor=.5)))

def load(url):
    CACHE.mkdir(parents=True,exist_ok=True)
    path=CACHE/(hashlib.sha256(url.encode()).hexdigest()+'.json')
    if path.exists(): return json.loads(path.read_text())
    response=SESSION.get(url,timeout=15)
    if response.status_code==404 and 'schema.embedded.json' in url:
        response=SESSION.get(url.replace('schema.embedded.json','schema-embedded.json'),timeout=15)
    response.raise_for_status();data=response.json()
    path.write_text(json.dumps(data),encoding='utf-8');return data

def main():
    p=argparse.ArgumentParser();p.add_argument('project',type=Path,nargs='?',default=ROOT/'powerbi'/'project');a=p.parse_args()
    errors=[];count=0
    files=list(a.project.rglob('*.json'))+list(a.project.rglob('*.pbip'))+list(a.project.rglob('*.pbir'))+list(a.project.rglob('*.pbism'))
    for path in files:
        data=json.loads(path.read_text(encoding='utf-8'))
        if '$schema' not in data: continue
        schema=load(data['$schema'])
        registry=Registry(retrieve=lambda uri:Resource.from_contents(load(uri),default_specification=DRAFT7)).with_resource(data['$schema'],Resource.from_contents(schema,default_specification=DRAFT7))
        for error in Draft7Validator(schema,registry=registry).iter_errors(data): errors.append(f'{path.relative_to(a.project)}: {list(error.path)}: {error.message}')
        count+=1
    for error in errors: print(error)
    print(f'Validated {count} JSON artifacts; {len(errors)} errors')
    return bool(errors)

if __name__=='__main__': raise SystemExit(main())
