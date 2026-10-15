# Kế hoạch xây dựng Power BI — Đinh Công Minh

Ngày bắt đầu: 14/10/2026. Trạng thái: bản thiết kế để Minh rà soát; các đề xuất dưới đây chưa thay thế hợp đồng ETL đã được nhóm thống nhất.

## 1. Phạm vi công việc

Nguồn: PROJECT_MANAGEMENT_PLAN.md (WBS 3.1–3.3, 4.1–4.3), PROJECT_ANALYTICS_SPEC.md và KE_HOACH_SPRINT_TUAN_02.md.

| Công việc của Minh | Sản phẩm cần tạo | Điều kiện hoàn thành |
|---|---|---|
| Chốt nghiệp vụ và hợp đồng dữ liệu | Tên bảng/cột, grain, đơn vị, định nghĩa KPI | Đầu ra ETL có thể thay dữ liệu mẫu mà không sửa visual |
| Mô hình dữ liệu và lịch | Semantic model, quan hệ và dim_date | Khóa duy nhất ở phía 1; lọc đúng task, annotator, ngày |
| 20 measures | Mã DAX, định dạng và ví dụ đối chiếu | Khớp Python trên cùng dữ liệu và bộ lọc |
| Thiết kế 5 trang | Báo cáo report_dashboard.pbix | Trả lời được câu hỏi quản trị, có drill-through và URL |
| Nghiệm thu dữ liệu | Bảng đối chiếu và danh sách lỗi | Không đếm lặp frame/job; phân biệt dữ liệu thiếu và số 0 |
| Demo/UAT | Kịch bản 15 phút, biên bản góp ý | Demo dự kiến 20:00 ngày 18/10/2026 (UTC+7) |

Minh và trợ lý có thể chuẩn bị mô hình, DAX, theme và bố cục trên fixture riêng trong powerbi/. Fixture phải ghi rõ là dữ liệu giả lập. Tuân tiếp tục làm ETL; Tú/Duy tiếp tục nguồn API; Ngọc tiếp tục điều phối. Tích hợp sau bằng cách đổi nguồn và đối chiếu số liệu.

## 2. Thứ tự triển khai phần Power BI

1. Chốt grain, khóa và ý nghĩa bộ lọc; đánh dấu các quyết định cần Minh duyệt.
2. Tạo fixture riêng và Power Query có tham số thư mục nguồn.
3. Dựng model; kiểm tra trường hợp một job có nhiều annotations, reviews và defects.
4. Viết nhóm measures tiến độ, thời gian, QA, hình học và nhân sự.
5. Dựng trang Executive 360 trước, sau đó QA, Annotator, Geometry, Edge Cases.
6. Thay fixture bằng CSV ETL thật; đối chiếu cùng phạm vi và bộ lọc.
7. Chạy demo và ghi fixlist/UAT.

## 3. Mô hình đề xuất để làm độc lập

Bản MVP lấy trạng thái mới nhất, một dòng/job. Không nối nhiều snapshot lịch sử vào cùng bảng rồi cộng total_frames. Nếu cần lịch sử, bổ sung snapshot_date và thiết kế fact snapshot riêng.

| Bảng nguồn/mô hình | Grain và khóa | Vai trò |
|---|---|---|
| dim_annotators | Một người; annotator_id | Bộ lọc người gán nhãn |
| dim_reviewers | Bản tham chiếu danh mục người; reviewer_id | Bộ lọc reviewer độc lập |
| dim_tasks_batches | Một task trong MVP; task_id duy nhất | batch_id để nhóm nhiều task; total_frames_target ở mức task |
| dim_classes_labels | Một label; label_id | Nhãn và nhóm nhãn |
| dim_date | Một ngày; date_key | Lịch liên tục, tạo trong Power BI |
| dim_jobs | Một annotation job; job_id | Tạo trong Power Query từ danh mục job, mang task_id và annotator_id |
| fact_job_sessions | Một dòng tổng hợp/job; job_id duy nhất | Frames, objects, tổng giờ, trạng thái cuối, ngày hoàn thành |
| fact_annotations | Một shape hoặc keyframe được vẽ; annotation_id duy nhất toàn bộ nguồn | Hình học và phân bố; không tính là unique object xuyên frame |
| fact_qa_reviews | Một lượt review/job; review_id | FTPR theo lần đầu và tỷ lệ rejected theo lượt |
| fact_qa_defects | Một lỗi được ghi nhận; defect_id | Loại lỗi và severity |
| fact_ground_truth_eval | Một lần đánh giá/job; eval_id | IoU/F1; chọn lần mới nhất/job cho KPI MVP |
| fact_edge_cases | Một GitHub Issue; case_id (repo + issue number) | Ca khó, câu hỏi, blocker và URL đã xác minh |

Quan hệ đề xuất: dim_tasks_batches và dim_annotators → dim_jobs → các fact theo job_id. dim_classes_labels → fact_annotations và fact_qa_defects. dim_reviewers → fact_qa_reviews. Bổ sung job_id cho fact_qa_defects qua merge review_id trong Power Query để có một đường lọc theo job; không tạo thêm quan hệ active reviews → defects.

Tất cả quan hệ lọc một chiều từ danh mục xuống fact. Quan hệ dim_jobs → fact_job_sessions có thể là 1:1 và cần kiểm tra hướng lọc trong Desktop; tránh tạo đường active khác từ task/annotator thẳng tới fact khi đã qua dim_jobs.

Ngày phải có nhãn rõ: ngày hoàn thành job và ngày review là hai vai trò khác nhau. MVP dùng dim_date cho ngày hoàn thành ở trang sản lượng; trang QA dùng lịch review riêng khi cần phân tích theo reviewed_at. Không suy ra ngày hoàn thành từ updated_date mà không ghi rõ là ngày thay thế.

Nếu label_id chỉ duy nhất trong từng task, thay bằng label_key ghép task_id + label_id ở model. Tương tự annotation_id cần gồm job và loại bản ghi/keyframe để tránh trùng ID.

## 4. Những điểm cần chốt trước khi nối ETL

| Vấn đề trong repo | Đề xuất để Minh xem xét |
|---|---|
| Tài liệu cũ 3/4 CSV, sprint mới 7 CSV | Dùng 7 CSV chi tiết của sprint làm lõi; thêm GT và edge_cases để đủ 5 trang; bảng lịch và dim_jobs tạo trong Power Query/Power BI |
| dim_tasks_batches thiếu total_frames_target trong dictionary | Bổ sung mục tiêu ở mức task, không lặp mục tiêu batch trên từng task |
| fact_job_sessions tên là sessions nhưng job_id là PK | MVP một dòng/job; lịch sử ca làm cần bảng grain session riêng |
| status, stage, state dùng chưa thống nhất | Lưu stage/state nguồn; quy tắc completed cần được xác nhận, không coi mọi validation là đã nghiệm thu |
| Frame giữa các job có thể chồng lấn | Chỉ cộng total_frames nếu job annotation có phạm vi không trùng; nếu trùng cần đếm frame duy nhất theo task |
| Thiếu active time | Giữ null; không gán 0 và không xếp inactive chỉ từ thiếu log |
| Người gán nhãn và reviewer dùng chung danh mục | Tách vai trò bằng dim_reviewers để tránh đường lọc nhập nhằng |
| Thiếu GT và ca khó trong bộ 7 CSV | Hai bảng bổ sung có thể rỗng nhưng phải giữ schema; thiếu nguồn hiển thị rõ |
| Nhóm nhân sự có khoảng hở và xử lý thiếu dữ liệu chưa hợp lý | Chờ Minh chốt ưu tiên Onboarding/Inactive và nhóm rủi ro; không gán nhãn chất lượng đạt khi thiếu review |

## 5. Quy tắc measures cần thống nhất

- Tiến độ toàn task: completed frames / tổng mục tiêu task. Khi lọc ngày, KPI phải nói rõ sản lượng trong kỳ hay tiến độ tích lũy tới ngày đã chọn.
- Vận tốc: mặc định đặc tả hiện tại là frames của job completed / giờ của mọi job trong phạm vi; giữ tên và định nghĩa rõ để đối chiếu Python. Không lấy trung bình đơn giản vận tốc từng người làm vận tốc toàn đội.
- FTPR: accepted ở review_iteration = 1 / tổng lượt review_iteration = 1. Một job chỉ có một lượt đầu hợp lệ.
- Rejection Rate: số lượt rejected / tổng lượt review; không đồng nghĩa tỷ lệ job phải làm lại.
- Thiếu nguồn hoặc mẫu số không hợp lệ: BLANK; số 0 chỉ khi nguồn đầy đủ và thực tế không phát sinh.
- Tỷ lệ FTPR, rejection, progress, Small dùng 0–1 và format %. frame_area_pct nguồn đang là 0–100; chia 100 trước khi format % hoặc dùng định dạng số kèm ký hiệu %, không format % trực tiếp.
- IoU/F1: MVP trung bình số học của kết quả mới nhất theo job; không tự tuyên bố đây là điểm gộp toàn dataset.
- Object Created trong nguồn track: số bản ghi được vẽ (shape và keyframe không outside), không phải số đối tượng duy nhất hay số frame completed.
- Benchmark toàn đội bỏ filter annotator, giữ task và thời gian. Count At Risk cần định nghĩa khớp cả FTPR, rejection và F1 với nhóm nhân sự, thay vì chỉ rejection như measure mẫu hiện tại.

## 6. Bố cục năm trang

Canvas đề xuất 16:9. Cùng vị trí tiêu đề, thời điểm snapshot và bộ lọc; màu đỏ dành cho rủi ro, vàng cho chờ xử lý, xanh cho đạt chuẩn. Mọi số liệu fixture hiển thị nhãn DEMO.

| Trang | Câu hỏi quản trị | Visual chính | Điểm nối sang trang khác |
|---|---|---|---|
| Executive 360 | Đã xong bao nhiêu, batch nào chậm? | 4 KPI: completed frames, progress, frames/h, FTPR; trạng thái theo batch; sản lượng theo ngày | Drill-through task sang QA |
| QA Deep-Dive | Sai ở đâu, lỗi nào cần sửa? | FTPR, rejection, lỗi/100 frames, IoU/F1; loại lỗi; bảng reviews | Drill-through job và URL CVAT |
| Annotator Matrix | Ai cần hỗ trợ và hỗ trợ gì? | Scatter vận tốc vs FTPR; bảng hiệu suất; trạng thái đủ/thiếu nguồn | Chi tiết job theo annotator |
| Data Geometry | Class có lệch, vật thể nhỏ có nhiều? | Số bản ghi vẽ, diện tích TB, Small%; bar theo class và COCO scale | Bộ lọc class/task |
| Edge-Case Explorer | Mentor cần giải quyết gì trước? | Open cases, blockers; bảng issue; mô tả và đề xuất khi chọn | URL GitHub/CVAT đã xác minh |

Ưu tiên visual tích hợp sẵn; thêm histogram bằng bin và bar. Các chỉ số chưa có nguồn hiển thị “Chưa đủ dữ liệu” thay vì giả lập thành dữ liệu thật.

## 7. Nghiệm thu khi ghép luồng

- So sánh 20 measures với Python trên cùng snapshot và bộ lọc; chốt sai số cho số thập phân trước khi nghiệm thu.
- Kiểm tra khóa trùng, FK mồ côi, nhiều reviews/job và job có nhiều annotations không làm tăng completed frames.
- Kiểm tra không có review, giờ làm null/0, GT thiếu, job chưa giao người, issue chưa xác minh, track có outside marker.
- Kiểm tra filter annotator không biến thành filter reviewer; filter task đến đủ fact; ngày review không bị hiểu là ngày hoàn thành.
- Chọn fixture hoặc ETL qua tham số thư mục nguồn; dữ liệu mới giữ schema thì Refresh cập nhật được visual.
- Refresh Power BI Desktop và lịch refresh Power BI Service là hai bước khác nhau. Chọn nguồn lưu trữ và cơ chế refresh Service khi nhóm tích hợp triển khai.

## 8. Tài liệu Microsoft tham khảo

- Star schema và role-playing dimensions: https://learn.microsoft.com/en-us/power-bi/guidance/star-schema
- DIVIDE và xử lý BLANK: https://learn.microsoft.com/en-us/dax/best-practices/dax-divide-function-operator

Chưa tạo PBIX hoặc chạy kiểm chứng DAX trong Power BI Desktop ở bước này. Sản phẩm hiện tại là bản thiết kế và kế hoạch làm việc để bắt đầu model.
