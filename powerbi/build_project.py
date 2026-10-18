"""Build an editable native Power BI Project (PBIP + semantic model + PBIR visuals).

Generated files are source artifacts, not a browser dashboard. Open the PBIP in
Desktop and refresh to populate its import model from a published CSV bundle.
"""
from __future__ import annotations
import argparse
import json
import sys
import uuid
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from src.reporting_pipeline import TABLES

MEASURES={
 'Total_Completed_Frames':('COALESCE(CALCULATE(SUM(fact_job_sessions[total_frames]), fact_job_sessions[status] = "completed"), 0)','#,0'),
 'Total_Objects_Created':('IF(MAX(report_status[annotations_available]) = 1, COALESCE(COUNTROWS(fact_annotations), 0))','#,0'),
 'Total_Active_Hours':('IF(COUNTROWS(fact_job_sessions) > 0 && COUNT(fact_job_sessions[active_time_hours]) = COUNTROWS(fact_job_sessions), SUM(fact_job_sessions[active_time_hours]))','0.00'),
 'Velocity_Frames_Per_Hour':('DIVIDE([Total_Completed_Frames], [Total_Active_Hours])','0.0'),
 'Velocity_Objects_Per_Hour':('DIVIDE([Total_Objects_Created], [Total_Active_Hours])','0.0'),
 'Avg_Time_Per_Frame_Mins':('DIVIDE([Total_Active_Hours] * 60, [Total_Completed_Frames])','0.00'),
 'Avg_Time_Per_Object_Secs':('DIVIDE([Total_Active_Hours] * 3600, [Total_Objects_Created])','0.00'),
 'First_Time_Pass_Rate':('IF(MAX(report_status[reviews_available]) = 1, DIVIDE(COALESCE(CALCULATE(COUNTROWS(fact_qa_reviews), fact_qa_reviews[review_iteration] = 1, fact_qa_reviews[review_decision] = "Accepted"), 0), CALCULATE(COUNTROWS(fact_qa_reviews), fact_qa_reviews[review_iteration] = 1)))','0.0%'),
 'Rejection_Rate':('IF(MAX(report_status[reviews_available]) = 1, DIVIDE(COALESCE(CALCULATE(COUNTROWS(fact_qa_reviews), fact_qa_reviews[review_decision] = "Rejected"), 0), COUNTROWS(fact_qa_reviews)))','0.0%'),
 'Total_Defects':('IF(MAX(report_status[defects_available]) = 1, COALESCE(COUNTROWS(fact_qa_defects), 0))','#,0'),
 'Defect_Density_Per_100F':('DIVIDE([Total_Defects] * 100, [Total_Completed_Frames])','0.00'),
 'Avg_Defects_Per_Job':('DIVIDE([Total_Defects], DISTINCTCOUNT(fact_qa_reviews[job_id]))','0.00'),
 'Avg_mIoU_Score':('IF(MAX(report_status[gt_available]) = 1, AVERAGE(fact_ground_truth_eval[mean_iou]))','0.000'),
 'Avg_F1_Score':('IF(MAX(report_status[gt_available]) = 1, AVERAGE(fact_ground_truth_eval[f1_score]))','0.000'),
 'Avg_Object_Area_Pixels':('AVERAGE(fact_annotations[area_pixels])','#,0.0'),
 'Avg_Area_Frame_Pct':('DIVIDE(AVERAGE(fact_annotations[frame_area_pct]), 100)','0.00%'),
 'Pct_Small_Objects':('DIVIDE(COALESCE(CALCULATE(COUNTROWS(fact_annotations), fact_annotations[size_scale] = "Small"), 0), CALCULATE(COUNTROWS(fact_annotations), NOT ISBLANK(fact_annotations[size_scale])))','0.0%'),
 'Count_At_Risk_Annotators':('VAR People = ADDCOLUMNS(VALUES(dim_annotators[annotator_id]), "F", [First_Time_Pass_Rate], "R", [Rejection_Rate], "G", [Avg_F1_Score]) VAR Assessed = FILTER(People, NOT ISBLANK([F]) || NOT ISBLANK([R]) || NOT ISBLANK([G])) RETURN IF(COUNTROWS(Assessed) > 0, COALESCE(COUNTROWS(FILTER(Assessed, (NOT ISBLANK([F]) && [F] < 0.8) || (NOT ISBLANK([R]) && [R] >= 0.2) || (NOT ISBLANK([G]) && [G] < 0.85))), 0))','#,0'),
 'System_Avg_Velocity':('CALCULATE([Velocity_Frames_Per_Hour], REMOVEFILTERS(dim_annotators))','0.0'),
 'Project_Progress_Pct':('DIVIDE([Total_Completed_Frames], SUM(dim_tasks_batches[total_frames_target]))','0.0%'),
 'Total_Target_Frames':('SUM(dim_tasks_batches[total_frames_target])','#,0'),
 'Frames_In_Annotation':('COALESCE(CALCULATE(SUM(fact_job_sessions[total_frames]), fact_job_sessions[status] = "annotation"), 0)','#,0'),
 'Frames_In_Validation':('COALESCE(CALCULATE(SUM(fact_job_sessions[total_frames]), fact_job_sessions[status] = "validation"), 0)','#,0'),
 'Daily_Completed_Frames':('CALCULATE(SUM(fact_job_sessions[total_frames]), fact_job_sessions[status] = "completed")','#,0'),
 'Total_Open_Edge_Cases':('COALESCE(CALCULATE(COUNTROWS(fact_edge_cases), fact_edge_cases[state] = "open"), 0)','#,0'),
 'Total_Blockers':('COALESCE(CALCULATE(COUNTROWS(fact_edge_cases), fact_edge_cases[state] = "open", fact_edge_cases[severity] = "Blocker"), 0)','#,0'),
 'Active_Annotators':('COALESCE(COUNTROWS(FILTER(VALUES(dim_annotators[annotator_id]), NOT ISBLANK(dim_annotators[annotator_id]) && CALCULATE(COUNTROWS(fact_job_sessions)) > 0)), 0)','#,0'),
 'Source_Label':('IF(MAX(report_status[is_demo]) = 1, "DEMO / DỮ LIỆU GIẢ LẬP", "DỮ LIỆU NGUỒN") & "  |  " & FORMAT(MAX(report_status[as_of]), "dd/MM/yyyy")',None),
 'Data_Warnings':('"Nguồn: " & IF(ISBLANK([Total_Active_Hours]), "giờ làm chưa đủ", "có giờ làm") & " | " & IF(MAX(report_status[reviews_available]) = 1, "có review", "thiếu review") & " | " & IF(MAX(report_status[gt_available]) = 1, "có Ground Truth", "thiếu Ground Truth") & UNICHAR(10) & "KPI trống = chưa đủ dữ liệu. Frames hoàn thành là proxy theo trạng thái job, chưa đồng nghĩa QA pass."',None),
 'Selected_Case':('SELECTEDVALUE(fact_edge_cases[description], "Chọn một ca trong bảng phía trên để đọc mô tả. Link example.org trong bản DEMO chỉ dùng minh họa.")',None),
 'Annotator_Segment':('VAR V = [Velocity_Frames_Per_Hour] VAR F = [First_Time_Pass_Rate] VAR R = [Rejection_Rate] VAR G = [Avg_F1_Score] VAR Known = NOT ISBLANK(F) || NOT ISBLANK(R) || NOT ISBLANK(G) VAR Risk = (NOT ISBLANK(F) && F < .8) || (NOT ISBLANK(R) && R >= .2) || (NOT ISBLANK(G) && G < .85) RETURN SWITCH(TRUE(), ISBLANK(V) || NOT Known, "Insufficient data", Risk && V >= 60, "Fast and faulty", Risk && V < 20, "Needs retraining", Risk, "Needs QA support", V < 20, "Slow but steady", V >= 40, "Star annotator", "Core performer")',None),
}

# A relationship's synthetic blank member represents an unassigned job, not a person.
MEASURES['Annotator_Segment'] = (
    'IF(HASONEVALUE(dim_annotators[annotator_id]) && NOT ISBLANK(SELECTEDVALUE(dim_annotators[annotator_id])), ('
    + MEASURES['Annotator_Segment'][0] + '))', None)


def assigned_people_filter(name):
    column = {'Column': {'Expression': {'SourceRef': {'Source': 'a'}}, 'Property': 'annotator_id'}}
    return {'name': name, 'field': {'Column': {'Expression': {'SourceRef': {'Entity': 'dim_annotators'}}, 'Property': 'annotator_id'}},
            'type': 'Advanced', 'howCreated': 'User',
            'filter': {'Version': 2, 'From': [{'Name': 'a', 'Entity': 'dim_annotators', 'Type': 0}],
                       'Where': [{'Condition': {'Not': {'Expression': {'In': {'Expressions': [column], 'Values': [[{'Literal': {'Value': 'null'}}]]}}}}}]}}

TITLES = {
    'Task / batch': 'Task / đợt dữ liệu', 'Annotator': 'Người gán nhãn',
    'Completed frames · job proxy': 'Frames hoàn thành · proxy',
    'Progress vs task target': 'Tiến độ / mục tiêu task',
    'Productivity · frames/hour': 'Vận tốc · frames/giờ',
    'First-time pass rate': 'Đạt ngay lần đầu · FTPR',
    'Task progress': 'Phân bổ frames theo trạng thái',
    'Completed frames by recorded completion date': 'Frames hoàn thành theo ngày ghi nhận',
    'Data coverage and interpretation': 'Nguồn dữ liệu và cách đọc KPI',
    'Rejected review rounds': 'Tỷ lệ review bị từ chối',
    'Defects / 100 completed frames': 'Lỗi / 100 frames hoàn thành',
    'Mean IoU · latest per job': 'mIoU · mới nhất/job',
    'Mean F1 · latest per job': 'F1 · mới nhất/job',
    'Defects by category': 'Lỗi theo nhóm nguyên nhân', 'Defects by label': 'Lỗi theo lớp đối tượng',
    'Review history': 'Lịch sử review · mỗi dòng là một lượt',
    'Assigned annotators': 'Số người có job trong bộ lọc', 'Frames / hour': 'Vận tốc · frames/giờ',
    'Quality risk · assessed people': 'Người có chỉ số QA cần chú ý',
    'Speed and quality · select a person': 'Vận tốc và FTPR · chọn một người',
    'Annotator performance': 'Chi tiết sản lượng và chất lượng',
    'Drawn records · no interpolation': 'Số bản ghi hình vẽ',
    'Mean object area · px²': 'Diện tích TB · px²',
    'Mean frame area occupied': 'Diện tích frame TB · %',
    'Small / measurable records': 'Tỷ lệ object nhỏ',
    'Drawn records by class': 'Bản ghi hình vẽ theo lớp', 'COCO size distribution': 'Phân bố kích thước theo COCO',
    'Open cases and questions': 'Ca khó và câu hỏi đang mở', 'Open blockers': 'Blocker đang mở',
    'Select an issue · URLs open source context': 'Chọn ca để đọc mô tả · DEMO dùng link minh họa',
    'Selected issue': 'Nội dung ca đang chọn',
}
FIELD_LABELS = {
    'full_name': 'Người gán nhãn', 'task_name': 'Task', 'label_name': 'Lớp đối tượng',
    'date_key': 'Ngày hoàn thành', 'job_id': 'Job', 'review_iteration': 'Lượt review',
    'review_decision': 'Kết quả', 'reviewed_at': 'Thời điểm review', 'defect_type': 'Loại lỗi',
    'size_scale': 'Kích thước', 'number': 'Mã ca', 'title': 'Tiêu đề', 'state': 'Trạng thái',
    'severity': 'Mức độ', 'frame': 'Frame', 'link_status': 'Trạng thái link',
    'cvat_deep_link': 'Mở CVAT', 'source_url': 'Nguồn ca',
    'Total_Completed_Frames': 'Frames hoàn thành', 'Frames_In_Annotation': 'Đang gán nhãn',
    'Frames_In_Validation': 'Đang kiểm tra', 'Daily_Completed_Frames': 'Frames hoàn thành',
    'Total_Defects': 'Số lỗi', 'Total_Objects_Created': 'Bản ghi hình vẽ',
    'Velocity_Frames_Per_Hour': 'Frames/giờ', 'First_Time_Pass_Rate': 'FTPR',
    'Annotator_Segment': 'Phân khúc theo bộ lọc',
}

def write_json(path,data):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')

def lit(value):
    if isinstance(value,bool): value='true' if value else 'false'
    elif isinstance(value,str): value="'"+value.replace("'","''")+"'"
    else: value=str(value)+'D'
    return {'expr':{'Literal':{'Value':value}}}

def projection(table,column,measure=False):
    kind='Measure' if measure else 'Column'
    return {'field':{kind:{'Expression':{'SourceRef':{'Entity':table}},'Property':column}},'queryRef':table+'.'+column,'nativeQueryRef':column,'displayName':FIELD_LABELS.get(column,column)}

def build(output=None,source_folder=None):
    output=Path(output or ROOT/'powerbi'/'project');output.mkdir(parents=True,exist_ok=True)
    source_folder=str(Path(source_folder or ROOT/'data'/'processed').resolve())
    report=output/'AnnotationReporter.Report';semantic=output/'AnnotationReporter.SemanticModel'
    semantic.mkdir(exist_ok=True)
    write_json(output/'AnnotationReporter.pbip',{'$schema':'https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json','version':'1.0','artifacts':[{'report':{'path':'AnnotationReporter.Report'}}],'settings':{'enableAutoRecovery':True}})
    write_json(semantic/'definition.pbism',{'$schema':'https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json','version':'1.0','settings':{}})
    tables=[]
    for name,cols in TABLES.items():
        columns=[]; types=[]
        for col,sql_type in cols.items():
            datatype={'TEXT':'string','INTEGER':'int64','REAL':'double'}[sql_type]
            mtype={'TEXT':'type text','INTEGER':'Int64.Type','REAL':'type number'}[sql_type]
            if col in ('date_key','joined_date','as_of'):
                datatype='dateTime';mtype='type date'
            c={'name':col,'dataType':datatype,'sourceColumn':col,'summarizeBy':'none'}
            if col in ('cvat_deep_link','source_url'): c['dataCategory']='WebUrl'
            if datatype=='dateTime': c['formatString']='yyyy-MM-dd'
            if col.endswith('_id') or col in ('label_key','label_id'): c['isHidden']=True
            columns.append(c);types.append('{"'+col+'", '+mtype+'}')
        expression=[
          'let',
          '    Pointer = Json.Document(File.Contents(SourceFolder & "\\current.json")),',
          '    Bundle = SourceFolder & "\\" & Text.Replace(Pointer[relative_folder], "/", "\\"),',
          '    Source = Csv.Document(File.Contents(Bundle & "\\'+name+'.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),',
          '    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),',
          '    Nulls = Table.ReplaceValue(Headers, "", null, Replacer.ReplaceValue, Table.ColumnNames(Headers)),',
          '    Typed = Table.TransformColumnTypes(Nulls, {'+', '.join(types)+'}, "en-US")',
          'in Typed',
        ]
        t={'name':name,'columns':columns,'partitions':[{'name':name,'mode':'import','source':{'type':'m','expression':expression}}]}
        if name in ('kpi_reconciliation','report_status'): t['isHidden']=True
        if name=='fact_job_sessions':
            t['measures']=[{'name':n,'expression':expr,**({'formatString':fmt} if fmt else {}),'displayFolder':'KPI' if n in list(MEASURES)[:20] else 'Report helpers'} for n,(expr,fmt) in MEASURES.items()]
        tables.append(t)
    relationships=[]
    def rel(child,ck,parent,pk):
        relationships.append({'name':str(uuid.uuid5(uuid.NAMESPACE_URL,f'{child}.{ck}->{parent}.{pk}')),'fromTable':child,'fromColumn':ck,'toTable':parent,'toColumn':pk,'crossFilteringBehavior':'oneDirection','fromCardinality':'many','toCardinality':'one'})
    rel('dim_jobs','task_id','dim_tasks_batches','task_id');rel('dim_jobs','annotator_id','dim_annotators','annotator_id')
    for fact in ('fact_job_sessions','fact_annotations','fact_qa_reviews','fact_qa_defects','fact_ground_truth_eval'): rel(fact,'job_id','dim_jobs','job_id')
    rel('fact_job_sessions','date_key','dim_date','date_key')
    for fact in ('fact_annotations','fact_qa_defects'): rel(fact,'label_key','dim_classes_labels','label_key')
    rel('fact_qa_reviews','reviewer_id','dim_reviewers','reviewer_id')
    rel('fact_edge_cases','task_id','dim_tasks_batches','task_id')
    model={'name':'AnnotationReporter','compatibilityLevel':1606,'model':{'culture':'en-US','defaultPowerBIDataSourceVersion':'powerBI_V3','sourceQueryCulture':'en-US','dataAccessOptions':{'legacyRedirects':True,'returnErrorValuesAsNull':True},'expressions':[{'name':'SourceFolder','kind':'m','expression':'"'+source_folder.replace('"','""')+'" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]'}],'tables':tables,'relationships':relationships,'annotations':[{'name':'PBI_QueryOrder','value':json.dumps(list(TABLES))},{'name':'__PBI_TimeIntelligenceEnabled','value':'0'}]}}
    write_json(semantic/'model.bim',model)
    query_text=['// Canonical CSV queries. Create SourceFolder parameter, then one query per table.','// SourceFolder = "'+source_folder+'"']
    for table in tables:
        query_text.extend(['','// '+table['name'],*table['partitions'][0]['source']['expression']])
    (ROOT/'powerbi'/'power_query_scripts.m').write_text('\n'.join(query_text)+'\n',encoding='utf-8')
    write_json(report/'definition.pbir',{'$schema':'https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json','version':'4.0','datasetReference':{'byPath':{'path':'../AnnotationReporter.SemanticModel'}}})
    definition=report/'definition'
    write_json(definition/'version.json',{'$schema':'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/versionMetadata/1.0.0/schema.json','version':'2.0.0'})
    write_json(definition/'report.json',{'$schema':'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/3.1.0/schema.json','themeCollection':{'baseTheme':{'name':'CY24SU06','reportVersionAtImport':{'visual':'1.8.50','report':'2.0.50','page':'1.3.50'},'type':'SharedResources'}},'resourcePackages':[{'name':'SharedResources','type':'SharedResources','items':[{'name':'CY24SU06','path':'BaseThemes/CY24SU06.json','type':'BaseTheme'}]}]})
    # Minimal theme, using only public theme properties.
    write_json(report/'StaticResources'/'SharedResources'/'BaseThemes'/'CY24SU06.json',{'name':'Annotation Operations','dataColors':['#2563EB','#14B8A6','#F59E0B','#EF4444','#8B5CF6'],'background':'#F3F6FB','foreground':'#172B4D','tableAccent':'#2563EB','textClasses':{'label':{'fontSize':14,'fontFace':'Segoe UI'},'title':{'fontSize':18,'fontFace':'Segoe UI'},'callout':{'fontSize':32,'fontFace':'Segoe UI'}}})
    pages=[('executive','01 Tổng quan'),('quality','02 Chất lượng'),('people','03 Nhân sự'),('geometry','04 Hình học'),('cases','05 Ca khó')]
    write_json(definition/'pages'/'pages.json',{'$schema':'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.0.0/schema.json','pageOrder':[p for p,_ in pages],'activePageName':'executive'})
    count=0
    def visual(page,name,title,kind,x,y,w,h,roles):
        nonlocal count
        title=TITLES.get(title,title)
        query={role:{'projections':[projection(*f) for f in fields]} for role,fields in roles.items()}
        v={'$schema':'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.7.0/schema.json','name':name,'position':{'x':x,'y':y,'z':count,'height':h,'width':w,'tabOrder':count},'visual':{'visualType':kind,'query':{'queryState':query},'visualContainerObjects':{'title':[{'properties':{'show':lit(True),'text':lit(title),'fontSize':lit(17),'fontColor':{'solid':{'color':lit('#172B4D')}}}}],'background':[{'properties':{'show':lit(True),'color':{'solid':{'color':lit('#FFFFFF')}},'transparency':lit(0)}}]},'drillFilterOtherVisuals':True}}
        if kind=='card':
            font=22 if name=='source' else (17 if name=='warnings' else (19 if name=='description' else 34))
            v['visual']['objects']={'labels':[{'properties':{'fontSize':lit(font),'displayUnits':lit(1)}}],'categoryLabels':[{'properties':{'show':lit(False)}}]}
        if page == 'people' and name in ('leaderboard', 'matrix'):
            v['filterConfig'] = {'filters': [assigned_people_filter('assigned_people_' + name)]}
        write_json(definition/'pages'/page/'visuals'/name/'visual.json',v);count+=1
    def m(name):return ('fact_job_sessions',name,True)
    def c(t,col):return (t,col,False)
    def card(page,id,title,measure,x,y,w=280,h=120):visual(page,id,title,'card',x,y,w,h,{'Values':[m(measure)]})
    for pid,title in pages:
        write_json(definition/'pages'/pid/'page.json',{'$schema':'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.0.0/schema.json','name':pid,'displayName':title,'displayOption':'FitToPage','height':900,'width':1440,'objects':{'background':[{'properties':{'color':{'solid':{'color':lit('#F3F6FB')}},'transparency':lit(0)}}]}})
        card(pid,'source','ANNOTATION OPERATIONS / '+title,'Source_Label',24,18,1392,70)
        visual(pid,'task_filter','Task / batch','slicer',24,100,360,85,{'Values':[c('dim_tasks_batches','task_name')]})
        if pid not in ('cases',):visual(pid,'person_filter','Annotator','slicer',400,100,360,85,{'Values':[c('dim_annotators','full_name')]})
    for i,(title,metric) in enumerate([('Completed frames · job proxy','Total_Completed_Frames'),('Progress vs task target','Project_Progress_Pct'),('Productivity · frames/hour','Velocity_Frames_Per_Hour'),('First-time pass rate','First_Time_Pass_Rate')]):card('executive','kpi'+str(i),title,metric,24+i*350,205,342)
    visual('executive','batch','Task progress','barChart',24,345,680,310,{'Category':[c('dim_tasks_batches','task_name')],'Y':[m('Total_Completed_Frames'),m('Frames_In_Annotation'),m('Frames_In_Validation')]})
    visual('executive','daily','Completed frames by recorded completion date','lineChart',724,345,692,310,{'Category':[c('dim_date','date_key')],'Y':[m('Daily_Completed_Frames')]})
    card('executive','warnings','Data coverage and interpretation','Data_Warnings',24,680,1392,180)
    for i,(title,metric) in enumerate([('Rejected review rounds','Rejection_Rate'),('Defects / 100 completed frames','Defect_Density_Per_100F'),('Mean IoU · latest per job','Avg_mIoU_Score'),('Mean F1 · latest per job','Avg_F1_Score')]):card('quality','kpi'+str(i),title,metric,24+i*350,205,342)
    visual('quality','defects','Defects by category','donutChart',24,345,500,290,{'Category':[c('fact_qa_defects','defect_type')],'Y':[m('Total_Defects')]})
    visual('quality','by_class','Defects by label','barChart',544,345,872,290,{'Category':[c('dim_classes_labels','label_name')],'Y':[m('Total_Defects')]})
    visual('quality','reviews','Review history','tableEx',24,655,1392,210,{'Values':[c('fact_qa_reviews',k) for k in ('job_id','review_iteration','review_decision','reviewed_at')]})
    for i,(title,metric) in enumerate([('Assigned annotators','Active_Annotators'),('Frames / hour','Velocity_Frames_Per_Hour'),('Quality risk · assessed people','Count_At_Risk_Annotators')]):card('people','kpi'+str(i),title,metric,24+i*465,205,450)
    visual('people','matrix','Speed and quality · select a person','scatterChart',24,345,690,500,{'Category':[c('dim_annotators','full_name')],'X':[m('Velocity_Frames_Per_Hour')],'Y':[m('First_Time_Pass_Rate')]})
    visual('people','leaderboard','Annotator performance','tableEx',734,345,682,500,{'Values':[c('dim_annotators','full_name'),m('Total_Completed_Frames'),m('Velocity_Frames_Per_Hour'),m('First_Time_Pass_Rate'),m('Annotator_Segment')]})
    for i,(title,metric) in enumerate([('Drawn records · no interpolation','Total_Objects_Created'),('Mean object area · px²','Avg_Object_Area_Pixels'),('Mean frame area occupied','Avg_Area_Frame_Pct'),('Small / measurable records','Pct_Small_Objects')]):card('geometry','kpi'+str(i),title,metric,24+i*350,205,342)
    visual('geometry','classes','Drawn records by class','barChart',24,345,690,500,{'Category':[c('dim_classes_labels','label_name')],'Y':[m('Total_Objects_Created')]})
    visual('geometry','scale','COCO size distribution','donutChart',734,345,682,500,{'Category':[c('fact_annotations','size_scale')],'Y':[m('Total_Objects_Created')]})
    card('cases','open','Open cases and questions','Total_Open_Edge_Cases',24,205,450)
    card('cases','blocker','Open blockers','Total_Blockers',494,205,450)
    visual('cases','cases_table','Select an issue · URLs open source context','tableEx',24,345,1392,290,{'Values':[c('fact_edge_cases',k) for k in ('number','title','state','severity','frame','link_status','cvat_deep_link','source_url')]})
    card('cases','description','Selected issue','Selected_Case',24,655,1392,210)
    dax='\n\n'.join(n+' =\n'+expr for n,(expr,_) in MEASURES.items())+'\n'
    (ROOT/'powerbi'/'dax_measures.dax').write_text(dax,encoding='utf-8')
    print(f'Native project: {output / "AnnotationReporter.pbip"}; {len(tables)} tables, {len(MEASURES)} measures, {count} visuals')
    return output

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source-folder',type=Path);p.add_argument('--output',type=Path);a=p.parse_args();build(a.output,a.source_folder)
