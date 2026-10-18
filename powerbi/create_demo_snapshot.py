"""Create a deterministic, explicitly synthetic snapshot for the five-page report."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def create_demo(folder=None, completed_jobs=10):
    if not isinstance(completed_jobs,int) or not 0 <= completed_jobs <= 15:
        raise ValueError('completed_jobs must be between 0 and 15')
    folder=Path(folder or ROOT/'sample_data'/'powerbi_demo'); folder.mkdir(parents=True,exist_ok=True)
    names=['Minh (demo)','Tu (demo)','Duy (demo)','Tuan (demo)','Ngoc (demo)']
    jobs=[]; annotations=[]; times=[]; reviews=[]; defects=[]; evals=[]
    for i in range(15):
        jid=7001+i; person=i%5; done=i<completed_jobs; day=10+i//3
        jobs.append({'id':jid,'task_id':700,'type':'annotation','stage':'annotation' if i<12 else 'validation','state':'completed' if done else 'in progress','frame_count':100,'start_frame':i*100,'stop_frame':i*100+99,'assignee':{'id':person+1,'username':'demo_'+str(person+1),'first_name':names[person]}})
        shapes=[]
        for k in range(12+i):
            size=[20,55,120][k%3]
            shapes.append({'id':k+1,'type':'rectangle','frame':i*100+k,'label_id':k%4+1,'points':[10,20,10+size,20+size]})
        annotations.append({'job_id':jid,'status':'success','data':{'shapes':shapes,'tracks':[],'tags':[]}})
        hours=[1.5,2.2,4,1.8,3][person]
        times.append({'job_id':jid,'active_time_hours':hours,'completed_at':f'2026-10-{day:02d}T10:00:00Z' if done else None})
        if done:
            rejected=person in (0,2)
            rid=f'R{jid}-1'
            reviews.append({'review_id':rid,'job_id':jid,'reviewer_id':'qa-demo','reviewer_name':'Reviewer (demo)','review_iteration':1,'review_decision':'Rejected' if rejected else 'Accepted','reviewed_at':f'2026-10-{day:02d}T12:00:00Z'})
            if rejected:
                defects.append({'defect_id':f'D{jid}','review_id':rid,'frame_idx':i*100+3,'label_id':1,'defect_type':'box_displacement' if person==0 else 'missing_object','severity':'Major'})
                reviews.append({'review_id':f'R{jid}-2','job_id':jid,'reviewer_id':'qa-demo','reviewer_name':'Reviewer (demo)','review_iteration':2,'review_decision':'Accepted','reviewed_at':f'2026-10-{day+1:02d}T12:00:00Z'})
            score=[.80,.95,.84,.97,.92][person]
            evals.append({'eval_id':f'GT{jid}','job_id':jid,'mean_iou':[.76,.94,.82,.96,.91][person],'f1_score':score,'precision':score,'recall':score,'evaluated_at':f'2026-10-{day:02d}T13:00:00Z'})
    issues=[]; links=[]
    for i,(label,title) in enumerate([('ca-kho','Vehicle partly occluded'),('mentor-question','How to label reflections?'),('blocker','Guideline decision required'),('ca-kho','Small object at image edge')],1):
        jid=7000+i; frame=(i-1)*100+5
        issues.append({'number':i,'title':'[DEMO] '+title,'state':'open','body':f'CVAT task ID: 700\nCVAT job ID: {jid}\nFrame index: {frame}\nSynthetic example for layout and interaction.','labels':[{'name':label}],'user':{'login':'demo_annotator'},'html_url':f'https://example.org/demo/issues/{i}'})
        links.append({'github_issue':i,'cvat_task_id':700,'cvat_job_id':jid,'actual_cvat_task_id':700,'frame':frame,'status':'verified','relationship_verified':True})
    values={
        'manifest.json':{'schema_version':1,'fixture':True,'started_at':'2026-10-16T10:00:00Z','finished_at':'2026-10-16T10:01:00Z','scope':{'task_id':700,'repo':'demo/annotation','cvat_host':'https://example.org'},'sources':{'cvat':{'status':'success'},'github':{'status':'success'}}},
        'cvat.json':{'task':{'id':700,'name':'DEMO — Vehicle annotation operations','size':1500,'mode':'annotation'},'jobs':jobs,'labels':[{'id':i,'name':name} for i,name in enumerate(['car','motorbike','pedestrian','truck'],1)],'issues':[],'comments':[],'annotations':annotations,
                     'media_metadata':[{'job_id':j['id'],'status':'success','data':{'size':100,'frames':[{'frame':frame,'width':1920,'height':1080} for frame in range(j['start_frame'],j['stop_frame']+1)]}} for j in jobs]},
        'github.json':{'issues':issues,'labels':[],'comments':[]},'links.json':links,
        'operations.json':{'schema_version':1,'availability':{'reviews':True,'defects':True,'ground_truth':True},'job_times':times,'reviews':reviews,'defects':defects,'ground_truth_evals':evals},
        'team_reports.json':[
            {'report_id':'TR-001','team':'Team Vehicles (DEMO)','reporter':'demo_1','report_text':'Đã hoàn thành phần việc được giao. Có tranh chấp guideline khi xe bị che khuất, cần Mentor xác nhận cách xử lý.','reported_at':'2026-10-16T09:00:00Z'},
            {'report_id':'TR-002','team':'Team Pedestrians (DEMO)','reporter':'demo_2','report_text':'Blocker: một nhóm ảnh bị lóa nên không thể xác định nhãn. Có cần loại ảnh này khỏi batch không?','reported_at':'2026-10-16T09:15:00Z'},
            {'report_id':'TR-003','team':'Team QA (DEMO)','reporter':'demo_qa','report_text':'Reviewer đã rà soát các lỗi được ghi nhận. Cần thống nhất quy chuẩn bounding box cho vật thể ở mép ảnh trước phiên Mentor.','reported_at':'2026-10-16T09:30:00Z'},
        ],
    }
    for name,data in values.items(): (folder/name).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    return folder

if __name__=='__main__': print(create_demo())
