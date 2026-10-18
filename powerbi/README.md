# Báo cáo Power BI — đường chạy hiện tại

**Dành cho máy mới:** [MULTI_MACHINE_SETUP.md](MULTI_MACHINE_SETUP.md). `START_AUTO.cmd` tự chuẩn bị `.venv` và thư viện; `SETUP_AUTO.cmd` chỉ chuẩn bị runtime. Cấu hình `config/desktop.local.json` chọn demo/offline/live, cổng và chu kỳ refresh. Chạy `START_AUTO.cmd --doctor` để chẩn đoán. Cần cài sẵn Python, Docker, Power BI và đăng nhập PostgreSQL lần đầu trên từng máy.

Bản giao diện tiếng Việt: **project_desktop/AnnotationReporter.pbip**; bản Desktop đóng gói là **AnnotationReporter_Desktop.pbix**. Báo cáo có 5 trang, 43 visuals và 31 measures (20 KPI chính). Xem [hướng dẫn trình bày](DESKTOP_PRESENTATION.md). AnnotationReporter.pbix và project/ giữ bản trước để đối chiếu; các file Dashboard*.pbix và HTML cũ là prototype.

**Bản tự cập nhật đã chạy được trên máy này:** bấm **START_AUTO.cmd**, mở **AnnotationReporter_Auto.pbix**. Cả 5 trang dùng DirectQuery và chu kỳ 10 giây; đã quan sát visual tự đổi 1.000 → 1.100 → 1.000 frames, không bấm Refresh/Save khi đổi dữ liệu. Hai tình huống đều khớp 20/20 KPI bằng engine Desktop. Xem [AUTO_DESKTOP.md](AUTO_DESKTOP.md). Phạm vi hiện tại là demo local, chạy khi khởi động launcher; chưa có lịch chạy nền hoặc kết nối CVAT thật.

## Chạy demo local

Cách nhanh trên máy này: bấm đúp **START_DEMO.cmd** ở gốc repo. Sau khi xuất dữ liệu, chọn **Refresh → Save** trong Desktop. Hướng dẫn đầy đủ và cách xử lý lỗi: [END_TO_END_LOCAL.md](END_TO_END_LOCAL.md).

Theo lựa chọn hiện tại, dùng dữ liệu giả lập trên máy trước; không cần CVAT_TOKEN. Kịch bản và số liệu trình bày: [DEMO_SCENARIO.md](DEMO_SCENARIO.md).

Tại thư mục gốc repo, Python 3.10+:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-runtime.txt
.\powerbi\RUN_DEMO.ps1
```

Script tạo fixture trong sample_data/powerbi_demo, chạy ingestion offline, tổng hợp phản ánh nhóm và publication. Project chỉ tạo khi chưa có; cờ -RebuildProject sẽ tạo lại từ template. Mở powerbi/AnnotationReporter_Desktop.pbix trong Desktop, chọn **Refresh**, sau đó **Save**.

Không rebuild project khi đang sửa bố cục trong Desktop: build_project.py tạo lại model/visuals từ mã nguồn. Để cập nhật số liệu, chỉ chạy src/main.py rồi Refresh; không chạy build_project.py. Khi dùng máy khác, chạy `python powerbi/build_project.py --output powerbi/project_desktop` lần đầu để đặt SourceFolder đúng máy hoặc sửa tham số SourceFolder trong Power Query.

## Chạy trên snapshot của nhóm

```powershell
.\.venv\Scripts\python.exe -X utf8 src/main.py --mode offline --snapshot data/raw/TEN_SNAPSHOT --session "Mentor tuần 2"
```

Nguồn giữ nguyên. Mỗi lần chạy tạo thư mục data/runs/<timestamp> chứa raw, report_data.json, Markdown, publication.json. Warehouse mới là data/annotation_reporting.db; database annotation_warehouse.db cũ được giữ để đối chiếu, không dùng cho report mới.

Đầu ra Power BI:

```text
data/processed/current.json
data/processed/snapshots/<snapshot_id>/*.csv
data/annotation_reporting.db
```

Các CSV theo bundle có cùng snapshot; current.json chỉ thay sau khi ghi đủ các bảng. Power BI đọc relative_folder trong pointer, không cần ODBC hay Python connector. Chạy pipeline xong rồi mới Refresh; không refresh đồng thời với lúc thay pointer.

Publication dùng khóa writer, staging directory và bundle CSV không ghi đè khi replay. source_snapshot trong bảng report_status là mã snapshot ổn định; đường dẫn thư mục mỗi lần chạy nằm trong data/runs/latest.json. Nếu pointer switch lỗi thông thường, phục hồi serving state của SQLite. SQLite/filesystem không có transaction chung; sau mất điện hoặc dừng cưỡng bức cần chạy lại pipeline trước khi Refresh.

SQLite cung cấp pbi_* views cho một snapshot đang publish. Facts và dimensions lịch sử đều có snapshot_id; không SELECT * từ gold_* để tính tổng hiện tại. Snapshot cùng nội dung và cấu hình được nhận diện theo hash, không thêm lần hai. Các thay đổi phiên bản transform tạo snapshot mới.

## Chạy live

Điền CVAT_HOST, CVAT_TOKEN (PAT), CVAT_TASK_ID, GITHUB_REPO và GITHUB_TOKEN trong .env. Public GitHub repo có thể đọc không token. Không gửi token trong chat hoặc commit .env.

```powershell
.\.venv\Scripts\python.exe -X utf8 src/main.py --mode live --session "Mentor tuần 2"
```

CVAT PAT dùng Bearer. Hai nguồn phải success, payload annotations của mọi annotation job phải đầy đủ thì mới publish. Lỗi nguồn/thiếu annotations dừng publication, giữ nguyên serving snapshot trước đó. Snapshot lỗi vẫn có thể nằm trong data/runs để điều tra. Thông báo CLI không thay thế việc đọc manifest/publication.

## Giờ làm, review và Ground Truth

API ingestion hiện chưa lấy lịch sử hoạt động/review đầy đủ. Cách bổ sung có kiểm soát: file operations.json trong snapshot hoặc cờ --operations PATH. Đây là dữ liệu đã được nhóm thu thập/xác nhận; không suy diễn từ GitHub comments hoặc updated_date.

```json
{
  "schema_version": 1,
  "availability": {"reviews": true, "defects": true, "ground_truth": true},
  "job_times": [
    {"job_id": 101, "active_time_hours": 2.5, "completed_at": "2026-10-16T10:00:00Z"}
  ],
  "reviews": [
    {"review_id": "R101-1", "job_id": 101, "reviewer_id": "qa1", "review_iteration": 1, "review_decision": "Accepted", "reviewed_at": "2026-10-16T11:00:00Z"}
  ],
  "defects": [],
  "ground_truth_evals": [
    {"eval_id": "G101", "job_id": 101, "mean_iou": 0.91, "f1_score": 0.93, "evaluated_at": "2026-10-16T12:00:00Z"}
  ]
}
```

Chỉ đặt availability=true khi nguồn tương ứng đầy đủ trong phạm vi snapshot. Mảng rỗng có availability=true nghĩa là nguồn đã kiểm tra và không có bản ghi. Không có nguồn thì không đặt true; các KPI phụ thuộc hiển thị BLANK. Các IDs minh họa phải thay bằng job thật trong snapshot.

Defect cần defect_id, review_id, frame_idx, defect_type; tùy chọn label_id, severity. Loại lỗi dùng 4 mã box_displacement/wrong_class/missing_object/wrong_attr. GT yêu cầu evaluated_at và chỉ giữ lần mới nhất mỗi job. Điểm phải trong 0–1. Mỗi job có tối đa một review_iteration=1.

--frame-size WIDTHxHEIGHT chỉ dùng khi biết đúng kích thước ảnh chung của snapshot. Nếu không chỉ định, pipeline đọc media metadata của job: dùng frame có ánh xạ rõ ràng hoặc danh sách đầy đủ có kích thước đồng nhất. Thiếu bằng chứng về kích thước thì tỷ lệ diện tích frame để null.

## Quy tắc model và KPI

- Grain: một snapshot, một task, một dòng/annotation job. Ground Truth/replica jobs không cộng sản lượng.
- dim_tasks_batches và dim_annotators lọc dim_jobs, rồi dim_jobs lọc các fact theo job_id; không có đường active song song.
- Reviewer là danh mục riêng. Label dùng khóa ghép task_id:label_id. Annotation dùng khóa ghép job/type/id/frame.
- dim_date liên kết ngày hoàn thành có bằng chứng ở fact_job_sessions. Không dùng updated_date làm ngày nộp. Trang sản lượng theo ngày bỏ qua job không có ngày hoàn thành; KPI tổng vẫn bao gồm job completed.
- Completed frames là proxy theo trạng thái job, không khẳng định số unique frames đã QA pass. Nếu phát hiện frame ranges chồng lấn hoặc tổng frame job vượt size task, dừng publish để giải quyết quy tắc đếm.
- Vận tốc = frame completed / giờ của mọi job trong filter. Thiếu giờ ở bất kỳ job trong filter thì BLANK, không làm tăng vận tốc do bỏ mẫu số.
- Đối tượng là shapes và keyframes không outside; không nội suy track. Small% tính trên các bản ghi đo được hình học.
- FTPR = accepted lần đầu / số lượt đầu; Rejection = rejected / mọi lượt review. Hai chỉ số không có cùng mẫu số.
- GT là trung bình số học các kết quả mới nhất/job, không phải F1/mIoU gộp theo mọi object.
- DAX Count_At_Risk xét FTPR <80%, rejection >=20% hoặc F1 <85%, không bỏ sót FTPR=0. Thiếu dữ liệu được ghi rõ thay vì coi là đạt chuẩn.
- Phân khúc trong report là measure động theo filter. Không suy ra Inactive/Onboarding khi thiếu nguồn hoạt động hoặc joined_date; hiển thị Insufficient data. Người tốc độ 20–59 nhưng rủi ro cao hiện Needs QA support, tránh xếp Core mặc định.
- Web URL chỉ xác minh quan hệ task/job từ snapshot; frame từ Issue chưa phải bằng chứng đã kiểm tra ảnh/frame.

## Kiểm tra và nghiệm thu

```powershell
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m pip install jsonschema
.\.venv\Scripts\python.exe powerbi/validate_project.py
```

kpi_reconciliation.csv chứa giá trị Python kỳ vọng của 20 KPI với bộ lọc toàn snapshot. Trong Desktop cần so sánh các measures DAX với bảng này, sau đó thử lọc annotator/task và chọn issue. JSON schema validation xác nhận cấu trúc report; không thay thế việc refresh/kiểm tra DAX bằng engine của Desktop.

Đã kiểm tra ngày 17/10/2026: 86 unit/integration tests pass, 54 JSON artifacts hợp lệ theo schema Microsoft, và 20/20 KPI DAX khớp Python trên demo, sai số tuyệt đối tối đa 1e-9. Kết quả từ engine Desktop lưu tại reports/POWERBI_DAX_RECONCILIATION.json. Có thể chạy lại powerbi/check_dax.ps1 với -ClientPath trỏ tới ADOMD client của Microsoft và Desktop đang mở report; dependency ADOMD không được commit vào repo.

Kiểm tra này dùng toàn snapshot, chưa thay thế UAT trên dữ liệu CVAT thật. Cả 5 trang đã được quan sát trực tiếp trong Desktop; trang Edge Cases hiển thị 4 ca mở, 1 blocker và tương tác chọn ca hoạt động. Các URL/frame thật cần dữ liệu và quyền CVAT của nhóm.

## Automation

.github/workflows/annotation-report.yml chạy tests và pipeline, lưu report/database/CSV dưới dạng GitHub artifact. Mặc định offline/demo. Muốn lịch chạy live, cấu hình repository variable ANNOTATION_REPORT_MODE=live cùng các vars/secrets ghi trong workflow. Lịch: thứ Năm 17:00 và Chủ Nhật 18:00 UTC+7.

Workflow chưa được dispatch từ phiên làm việc local này. Mục tiêu hiện tại là Power BI Desktop; Power BI Service chưa được cấu hình.

## Vận hành Desktop và tổng hợp nhóm

Sau khi ghép cập nhật GitHub: `src/main.py` giữ luồng canonical và nhận thêm `--verify`, `--brief`, `--no-brief`, cùng alias `--mode online` cho live. `--verify` đối chiếu Markdown với warehouse đang phục vụ và lưu agent_reconciliation.json; kiểm tra DAX Desktop vẫn dùng check_dax.ps1. API run_full_pipeline được giữ qua wrapper. ReportReaderAgent và summarize_from_warehouse nhận được cả warehouse canonical lẫn database prototype cũ; khi đọc canonical không trộn lịch sử hoặc tự điền KPI/ETA thiếu. Chatbot có thể chạy `python -m src.generators.report_agent --db data/annotation_reporting.db --report DUONG_DAN_BAO_CAO -i`.

Chạy từ gốc repo, sau đó Refresh và Save trong Desktop:

```powershell
.\powerbi\RUN_LOCAL.ps1 -CheckOnly
.\powerbi\RUN_LOCAL.ps1 -Mode offline -Snapshot data/raw/TEN_SNAPSHOT -Session "Mentor tuần 2"
# Khi đã cấu hình .env cho nguồn thật:
.\powerbi\RUN_LOCAL.ps1 -Mode live -Session "Mentor tuần 2"
```

Cờ tùy chọn: -Operations PATH, -TeamReports PATH, -FrameSize WIDTHxHEIGHT. RUN_LOCAL giữ nguyên thiết kế báo cáo. RUN_DEMO dùng fixture riêng để minh họa.

-CheckOnly chỉ đọc cấu hình và bộ CSV hiện tại, ghi data/desktop_readiness.json; không gọi API và không xuất token. Chế độ live tự kiểm tra cấu hình trước khi truy cập mạng. Kết quả configuration_ready không xác nhận quyền API: quyền truy cập chỉ được xác nhận sau khi chạy nguồn thật thành công.

team_reports.json là mảng các object gồm report_id, team, text; xem sample_data/powerbi_demo/team_reports.json. Runner tạo team_summary.json và ghép vào Markdown khi có --llm-summary. Mặc định trích xuất offline, giữ mã báo cáo nguồn và yêu cầu nhóm trưởng duyệt. Gemini chỉ được gọi khi chọn rõ --mode live --llm-summary --summary-provider gemini và cấu hình GEMINI_API_KEY/GEMINI_MODEL; lỗi API dùng bản offline. Chưa gọi Gemini thật trong phiên này.

Mỗi lần chạy lưu notification_preview.txt. RUN_LOCAL/RUN_DEMO chỉ tạo bản xem trước, không gửi tin. CLI có --notify telegram/discord để gửi thật khi được chủ động lựa chọn và cấu hình thông tin đích; chưa gửi tin thật trong phiên này. Không tự retry khi giao nhận không xác định. Các module summary/notifier đã có 19 bài kiểm thử dùng mock; lượt chạy trước đạt 36 bài cho hai module này cùng pipeline, trước các chỉnh sửa tăng độ bền cuối phiên.

CVAT extractor thu thập thêm media metadata và quality report/data mới nhất theo task/job. Lỗi nguồn tùy chọn được ghi trạng thái thiếu/partial. Raw quality report chưa tự chuyển thành review history/GT KPI: vẫn cần xác nhận mapping và dữ liệu nguồn để điền operations.json.
