"""Create a separate DirectQuery report, preserving the existing Desktop design."""
from __future__ import annotations
import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))


def build(output=None,port=55432,refresh_seconds=10):
    if type(port) is not int or not 1024 <= port <= 65535: raise ValueError('Invalid PostgreSQL port')
    if type(refresh_seconds) is not int or not 1 <= refresh_seconds <= 3600: raise ValueError('Invalid refresh interval')
    output=Path(output or ROOT/'powerbi/project_auto')
    if output.exists(): raise ValueError('DirectQuery project already exists; preserve edits or choose a new --output folder')
    source=ROOT/'powerbi/project_desktop'
    shutil.copytree(source,output,ignore=shutil.ignore_patterns('.pbi'))
    model_path=output/'AnnotationReporter.SemanticModel/model.bim'
    model=json.loads(model_path.read_text(encoding='utf-8'))
    model['name']='AnnotationReporter_Auto'
    model['model']['expressions']=[]
    for table in model['model']['tables']:
        table['partitions']=[{'name':table['name'],'mode':'directQuery','source':{'type':'m','expression':[
            'let',
            f'    Database = PostgreSQL.Database("127.0.0.1:{port}", "annotation_reporting", [CreateNavigationProperties=false]),',
            '    Source = Database{[Schema="public", Item="pbi_'+table['name']+'"]}[Data]',
            'in Source',
        ]}}]
        for measure in table.get('measures',[]):
            if measure['name']=='Annotator_Segment':
                measure['expression']='IF(HASONEVALUE(dim_annotators[annotator_id]), ('+measure['expression']+'))'
    model_path.write_text(json.dumps(model,ensure_ascii=False,indent=2),encoding='utf-8')
    configure_page_refresh(output,refresh_seconds)
    return output/'AnnotationReporter.pbip'


def configure_page_refresh(output,refresh_seconds=10):
    # Serialized by Power BI Desktop's native Page refresh control (10 seconds).
    for page_path in (Path(output)/'AnnotationReporter.Report/definition/pages').glob('*/page.json'):
        page=json.loads(page_path.read_text(encoding='utf-8'))
        page.setdefault('objects',{})['pageRefresh']=[{'properties':{
            'show':{'expr':{'Literal':{'Value':'true'}}},
            'duration':{'expr':{'Literal':{'Value':f"'PT{refresh_seconds}S'"}}},
        }}]
        page_path.write_text(json.dumps(page,ensure_ascii=False,indent=2),encoding='utf-8')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--port',type=int,default=55432)
    parser.add_argument('--refresh-seconds',type=int,default=10)
    args=parser.parse_args()
    print(build(args.output,args.port,args.refresh_seconds))
