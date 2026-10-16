# Hợp đồng dữ liệu integration v1

**Cập nhật:** 16/10/2026 · **schema_version:** 1 · **Luồng chính:** src/sync.py.

Tài liệu này mô tả output **đang được code tạo**, không trộn trường dự kiến.
[README](README.md) hướng dẫn chạy; [HANDOFF](HANDOFF.md) chứa đề xuất mở rộng.

## 1. Cách đọc output

```text
manifest.json → kiểm tra phạm vi, lỗi nguồn và annotations
report_data.json → dùng cho xử lý/BI/báo cáo
cvat.json + github.json + links.json → đối chiếu dữ liệu
MENTOR_REPORT_DRAFT.md → nhóm trưởng đọc và review
```

| Quy tắc | Ý nghĩa |
|---|---|
| null | Chưa có/chưa xác định; không phải 0 |
| available + items rỗng | Không có bản ghi phù hợp quy ước trong snapshot |
| unavailable | Không cung cấp được dữ liệu; không tính thành 0 |
| partial | Dữ liệu chưa đầy đủ; kiểm tra từng job |
| integer ID | ID task/job/issue là số nguyên |
| Timestamp ISO 8601 | JSON dùng UTC; Markdown hiển thị UTC+7 |

Các trường mới có thể được thêm trong v1; consumer bỏ qua trường chưa dùng.
Đổi ý nghĩa hoặc kiểu trường hiện có cần tăng version. Raw giữ payload API,
các trường phụ thuộc loại annotation/phiên bản; không phải mọi object đều cùng khóa.

## 2. manifest.json — kết quả lần chạy

| Đường dẫn | Kiểu | Ý nghĩa |
|---|---|---|
| schema_version | integer | Phiên bản cấu trúc |
| started_at, finished_at | string | Cửa sổ thu thập, không phải giờ làm/nộp |
| scope.task_id | integer | Task được chọn |
| scope.repo | string | OWNER/REPO |
| scope.cvat_host | string | URL CVAT |
| scope.org | string/null | Workspace/organization |
| sources.cvat, sources.github | object | Kết quả từng nguồn |
| sources.<nguồn>.status | string | success/failed |
| sources.<nguồn>.file | string, nếu success | Tên file JSON nguồn |
| sources.<nguồn>.counts | object, nếu success | Số bản ghi theo nhóm |
| sources.<nguồn>.started_at, finished_at | string | Cửa sổ lấy nguồn |
| sources.<nguồn>.error_type, error | string, nếu có | Lỗi; error không luôn có |
| sources.cvat.annotations.successful_jobs, failed_jobs | integer, nếu CVAT success | Kết quả lấy annotations theo job |
| links.file, links.counts | string/object | File và số liên kết theo status |
| links.status, links.reason | string, nếu skipped | Không có dữ liệu GitHub để xác minh |

Nguồn CVAT có thể success dù một job annotations failed. Đọc thêm failed_jobs
và annotations.status trong report_data. counts.annotations đếm các **bản ghi
theo job**, không đếm shapes/tracks. Nguồn failed không xuất file dữ liệu giả rỗng.

Đây là cấu trúc của src/sync.py theo bản main refactor. Lỗi comments/Quality Reports đang có thể bị bỏ qua, nên trạng thái success chưa chứng minh dữ liệu tùy chọn đầy đủ. API chạy lại trên Cloud vẫn cần kiểm chứng riêng.

## 3. report_data.json — đầu vào chính

```text
schema_version
metadata
batch_progress
scores
annotations
edge_cases
open_questions
blockers
guideline_updates
```

### metadata

| Trường | Kiểu | Ý nghĩa |
|---|---|---|
| snapshot | string | Thư mục nguồn |
| snapshot_started_at, snapshot_finished_at | string/null | Cửa sổ thu thập |
| generated_at | string | Lúc render nháp; có thể thay đổi khi render offline |
| mentor_session | string/null | Tên phiên, từ --session |
| scope | object/null | Phạm vi từ manifest |
| warnings | string[] | Nguồn thiếu, annotations thiếu, liên kết chưa xác minh |
| excluded_issues | object[] | number, reason; có thể thêm task_id |

excluded_issues.reason gồm api_test hoặc other_task. Danh sách này không phải
toàn bộ issues bị bỏ qua: issue closed/không mang nhãn phù hợp không luôn được ghi.
generated_at không phải giờ nộp hoặc thời gian người dùng soạn.

### batch_progress

Hiện một task được trình bày làm batch thử, chưa gom nhiều task.

| Trường | Kiểu | Ý nghĩa |
|---|---|---|
| status | string | available/unavailable |
| task_id, task_name, total_frames | integer/string/integer hoặc null | Task ID, tên, size |
| jobs | object[] | Các jobs được lấy |
| jobs_by_stage, jobs_by_state | object<string, integer> | Counts mọi loại job theo trạng thái |
| annotation_job_count | integer | Chỉ job type annotation |
| completed_annotation_job_count | integer | Annotation job state completed |
| completed_annotation_job_percent | number/null | Tỷ lệ theo số annotation jobs |
| completed_frames, completion_percent | null | Chưa tính hoàn thành frame |
| note | string | Giới hạn |

```text
completed_annotation_job_percent = completed_annotation_job_count / annotation_job_count × 100
```

Làm tròn hai chữ số; null khi không có annotation job. Loại Ground Truth/replica
không tham gia công thức. Khi CVAT unavailable, các counts mặc định không được
dùng để kết luận. Tỷ lệ này không phải % frame, QA pass hay tiến độ theo kế hoạch.

Mỗi jobs[]:

| Trường | Kiểu | Ý nghĩa |
|---|---|---|
| job_id | integer | ID job |
| type, stage, state | string/null | Giá trị từ CVAT |
| assignee | string/null | Username; null nếu chưa phân công |
| frame_count | integer/null | Số frame thuộc job |
| source_url | string | Link giao diện job |

### scores

| Trường | Hiện tại |
|---|---|
| status | available khi raw quality_report không rỗng, còn lại unavailable |
| value | Lấy mean_iou hoặc quality_score trong metadata, có thể vẫn null |
| method | CVAT Quality Report (Ground Truth) khi có report |
| source_url, scored_at | API URL report và created_date nếu có |
| details | Raw quality_report khi có report |
| reason | Có khi unavailable |

Extractor hiện đọc phần tử đầu của danh sách reports, chưa tải /data hoặc conflicts, chưa bảo đảm đó là report mới nhất. available không bảo đảm value có số hợp lệ. Không có report và lỗi đọc report hiện đều có thể thành null; chưa chốt thang điểm hoặc có dữ liệu reviewer. Cần đối chiếu nguồn trước khi dùng làm điểm QA chính thức.

### annotations

| Trường | Kiểu | Ý nghĩa |
|---|---|---|
| status | string | available/partial/unavailable |
| jobs | object[] | job_id, status, counts theo job |
| totals | object/null | Tổng bản ghi từ jobs lấy thành công |
| by_label | object[] | label_id, label_name, shapes, tracks, tags |
| note | string, khi có thống kê | Cách đếm/giới hạn |
| reason | string, khi unavailable | Snapshot chưa có annotations |

totals và jobs[].counts gồm:

| Trường | Ý nghĩa |
|---|---|
| shapes | Shape độc lập |
| tracks | Track |
| tags | Tag |
| track_shape_records | Bản ghi shape được lưu trong tracks, không nội suy |

Job failed có counts null. Totals cộng mọi loại job lấy thành công, **khác** bộ
đếm tiến độ chỉ dùng annotation jobs. partial không được coi là số đầy đủ.
Không loại trùng giữa jobs, nội suy, hoặc thống kê skeleton elements/intervals riêng.
Số annotations không phải frame hoàn thành. Frame không có đối tượng vẫn có thể
đã được kiểm tra xong. Snapshot cũ không chứa annotations vẫn render được với unavailable.

### edge_cases và open_questions

Mỗi mục có status (available/unavailable) và items[]. Status phản ánh nguồn
GitHub lấy được, không bảo đảm mọi item có link hợp lệ. blockers và guideline_updates có cùng cấu trúc và được chọn theo labels blocker/guideline-update.

| Trường items[] | Kiểu | Ý nghĩa |
|---|---|---|
| number | integer | Số issue trong repo |
| title | string/null | Tiêu đề |
| description | string | Body nguyên văn, rỗng nếu không có |
| labels | string[] | Tên labels |
| source_url | string/null | Link issue |
| state | string/null | Trạng thái |
| author | string/null | Login người tạo |
| updated_at | string/null | Thời điểm cập nhật nguồn |
| task_id, job_id | integer/null | ID đọc từ body |
| link_status | string | Status trong links, mặc định unlinked |
| cvat_job_url | string/null | Sinh khi task/job verified, thêm ?frame nếu đọc được frame |
| frame | integer/null | Đọc từ body nếu có; chưa xác minh phạm vi frame |

Quy tắc: issue open + ca-kho vào edge_cases; open + mentor-question vào
open_questions; cả hai label xuất hiện ở cả hai mục. Loại title bắt đầu [API test]
(không phân biệt hoa/thường) hoặc label api-test. Loại tham chiếu task khác khi
đọc được ID. Không tự suy đoán issue không ID thuộc task; câu hỏi chung giữ kèm
cảnh báo. Description chưa tổng hợp comments. CVAT issues chưa tự chuyển thành ca khó.

## 4. links.json — quan hệ issue/task/job

Array gồm các trường tùy kết quả:

| Trường | Ý nghĩa |
|---|---|
| github_issue, github_url, github_issue_updated_at | Số, link, ngày cập nhật issue |
| cvat_task_id, cvat_job_id | ID đọc từ body |
| actual_cvat_task_id | Task thực tế của job do CVAT trả |
| relationship_verified | Boolean, có khi kiểm tra được |
| status | Phân loại bên dưới |
| frame | Số đọc từ body, có thể null; không chứng nhận phạm vi |
| error_type, error | Thông tin lỗi tùy kết quả |

| Status | Ý nghĩa |
|---|---|
| verified | Job thuộc task được ghi |
| mismatch | Job thuộc task khác |
| unlinked | Không có dòng tham chiếu theo mẫu |
| invalid_reference | Thiếu, trùng hoặc sai định dạng ID |
| verification_failed | Lỗi API/phản hồi không đủ để xác minh |

Mỗi loại ID cần một dòng số nguyên dương. Link chỉ chứng minh quan hệ task/job,
không chứng nhận chất lượng, ngày nộp, phạm vi frame hoặc URL do người nhập đúng.
links lưu cả các issues không đưa vào bản nháp; counts không phải số ca khó/câu hỏi.

## 5. cvat.json và github.json — dữ liệu nguồn

### CVAT

| Nhóm | Trường chính | Endpoint GET |
|---|---|---|
| task (object) | id, name, project_id/name, owner, assignee, size, status, created_date, updated_date, validation_mode, jobs, labels | /api/tasks/{id} |
| jobs[] | id, task_id, type, stage, state, assignee, frame_count, start_frame, stop_frame, created_date, updated_date | /api/jobs?task_id=... |
| labels[] | id, name, type, color, attributes, sublabels | /api/labels?task_id=... |
| issues[] | id, job, frame, position, owner, assignee, resolved, created_date, updated_date, comments nếu nguồn có | /api/issues?task_id=... |
| comments[] | id, issue, owner, message, created_date, updated_date nếu nguồn có | /api/comments?issue_id=... |
| annotations[] | job_id, status, data hoặc error_type/error | /api/jobs/{id}/annotations/ |
| quality_report | Metadata phần tử đầu của danh sách hoặc null | /api/quality/reports?task_id=... |

task.labels chỉ là URL; labels[] ở cấp ngoài mới chứa danh mục. labels là schema
nhãn, annotations là dữ liệu đã vẽ. Issues/comments chưa có trong task thử đầu,
không được coi field inventory là bằng chứng đã kiểm chứng payload thật mọi loại.

annotations[].data giữ payload: version, tags, shapes, tracks, intervals nếu có.
Shape thường có id, label_id, frame, type, points, attributes; track có id,
label_id, frame, shapes, attributes, elements; shape trong track có frame,
points, outside, occluded và các trường hình học. Trường tùy loại/phiên bản.

### GitHub

| Nhóm | Trường chính | Endpoint GET |
|---|---|---|
| issues[] | id, number, title, body, state, user, assignees, labels, html_url, created_at, updated_at, closed_at | /repos/{owner}/{repo}/issues?state=all |
| labels[] | id, name, color, description | /repos/{owner}/{repo}/labels |
| comments[] | id, issue_url, body, user, created_at, updated_at, html_url | /repos/{owner}/{repo}/issues/{number}/comments |

Issues gồm open/closed, loại PR. Các trường nguồn giữ nguyên khi API có; không
phải tất cả đã map vào report_data. closed_at của issue không phải ngày nộp job.
updated_date của CVAT cũng không phải submitted_at.

## 6. Giới hạn và sử dụng an toàn

Snapshot lưu nhiều request, không phải giao dịch nhất quán. Counts chỉ phản ánh
phạm vi/thời điểm lấy. Không có issue không chứng minh không có lỗi annotation.
Giờ lấy, giờ tạo nháp, giờ làm và giờ nộp là bốn khái niệm khác nhau.

Giờ làm, ngày nộp, review và đo thời gian chưa tích hợp. Ground Truth hiện chỉ có bước thử đọc metadata; kết quả chất lượng đầy đủ còn cần kiểm chứng và mở rộng, xem [HANDOFF](HANDOFF.md). Không bổ sung giá trị suy đoán
vào schema hiện tại để lấp chỗ trống.
