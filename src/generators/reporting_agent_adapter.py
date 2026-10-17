"""Bridge the incoming report agent to the snapshot-scoped Desktop warehouse."""
import json
import math
import re
import sqlite3
from contextlib import closing


def read_canonical(path):
    if not path.exists(): return None
    with closing(sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True)) as conn:
        conn.row_factory=sqlite3.Row
        if not conn.execute("SELECT 1 FROM sqlite_master WHERE name='pbi_kpi_reconciliation'").fetchone(): return None
        state=conn.execute('SELECT snapshot_id FROM serving_state WHERE id=1').fetchone()
        if not state: return {'canonical':True,'snapshot_id':None,'metrics':{},'edge_cases':[],'annotators':[],'team_reports':[]}
        sid=state[0]
        raw=conn.execute('SELECT raw_json FROM bronze_snapshots WHERE snapshot_id=?',(sid,)).fetchone()
        return {'canonical':True,'snapshot_id':sid,
                'metrics':{r['metric']:r['expected_value'] for r in conn.execute('SELECT metric,expected_value FROM gold_kpi_reconciliation WHERE snapshot_id=?',(sid,))},
                'edge_cases':[dict(r) for r in conn.execute('SELECT * FROM gold_fact_edge_cases WHERE snapshot_id=? AND state=?',(sid,'open'))],
                'annotators':[dict(r) for r in conn.execute('SELECT * FROM gold_dim_annotators WHERE snapshot_id=?',(sid,))],
                'team_reports':json.loads(raw[0]).get('team_reports',[]) if raw else []}


def reconcile(data,text,report_path,db_path):
    sid=data['snapshot_id']
    checks=[{'target':'Snapshot ID','db_value':sid,'status':'PASS' if sid and f'Snapshot: `{sid}`' in text else 'FAIL','detail':'Đối chiếu mã snapshot của Markdown và serving warehouse.'}]
    values={name:value.strip() for name,value in re.findall(r'^\|\s*([A-Za-z_][A-Za-z0-9_]*)\s*\|\s*([^|]+)\|',text,re.MULTILINE)}
    for metric,expected in data['metrics'].items():
        try:
            actual=values[metric]
            matches=actual=='Chưa đủ dữ liệu' if expected is None else math.isclose(float(actual),expected,rel_tol=1e-5,abs_tol=1e-6)
        except (KeyError,ValueError): matches=False
        checks.append({'target':metric,'db_value':expected,'status':'PASS' if matches else 'FAIL','detail':'Markdown dùng 6 chữ số có nghĩa; đây không phải đối chiếu engine DAX.'})
    return {'report_file':str(report_path),'database_file':str(db_path),'snapshot_id':sid,'checks':checks,'overall_consistent':bool(data['metrics']) and all(c['status']=='PASS' for c in checks)}


def briefing(data):
    metrics=data['metrics']
    def value(key,pct=False):
        v=metrics.get(key)
        return 'Chưa đủ dữ liệu' if v is None else (f'{v*100:.1f}%' if pct else f'{v:,.3f}'.rstrip('0').rstrip('.'))
    lines=['# BẢN TÓM TẮT ĐIỀU HÀNH',f'Snapshot: `{data["snapshot_id"]}`','',
           '## Tiến Độ & Vận Tốc Cốt Lõi',
           '- Tiến độ frames theo trạng thái job: '+value('Project_Progress_Pct',True),
           '- Frames hoàn thành: '+value('Total_Completed_Frames'),
           '- Vận tốc: '+value('Velocity_Frames_Per_Hour')+' frames/giờ.',
           '- ETA: chưa có nguồn dự báo đã xác nhận.','',
           '## Chất Lượng QA/QC',
           '- FTPR: '+value('First_Time_Pass_Rate',True)+'; rejection: '+value('Rejection_Rate',True),
           '- mIoU: '+value('Avg_mIoU_Score')+'; F1: '+value('Avg_F1_Score'),'',
           '## Điểm Nghẽn & Ca Khó',f'- Ca khó/câu hỏi đang mở: {len(data["edge_cases"])}.']
    lines.extend(f'- #{e["number"]}: {e["title"]}' for e in data['edge_cases'])
    lines+=['','## Nhân sự',f'- Có {len(data["annotators"])} người trong snapshot; chỉ số QA cần chú ý: '+value('Count_At_Risk_Annotators')+'.',
            '- Không suy ra thứ hạng năng lực hoặc thời hạn từ dữ liệu thiếu.']
    return '\n'.join(lines)
