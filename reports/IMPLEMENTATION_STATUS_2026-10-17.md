# Hoàn thiện luồng báo cáo Power BI — 17/10/2026

## Đã thực hiện và kiểm chứng

- Entry point src/main.py dùng chung cho online/offline, lưu bản chạy riêng, tạo Markdown và publish bộ bảng phục vụ Power BI.
- Warehouse mới data/annotation_reporting.db, có raw audit, entities và Gold theo snapshot; pbi_* views chỉ lấy snapshot đang publish. Replay không nhân đôi; dữ liệu lịch sử không cộng vào KPI hiện tại.
- Bỏ loader nhập số KPI cố định. Loader nhận snapshot bất kỳ; không trộn fixture với nguồn thật.
- Hợp đồng canonical khớp tên cột trong CSV, Power Query, DAX và semantic model. Khóa label gồm task; shape/track keys gồm job.
- Dữ liệu thiếu giờ làm, review, GT hoặc kích thước ảnh giữ null/BLANK. Ngày nộp không suy từ updated_date. Source lỗi/annotations thiếu không thay serving snapshot.
- Project native powerbi/project/AnnotationReporter.pbip: 14 bảng, 31 measures, 5 trang, 43 visuals; không thay thế bằng dashboard HTML.
- Đã lưu bản powerbi/AnnotationReporter.pbix bằng Power BI Desktop. Đã quan sát cả 5 trang và tương tác chọn Edge Case (4 ca mở, 1 blocker).
- Bản giao diện tiếp theo: powerbi/AnnotationReporter_Desktop.pbix, lưu trực tiếp bằng Desktop, mã nguồn tại powerbi/project_desktop. Tiêu đề, nhãn cột/biểu đồ và hướng dẫn KPI đã chuyển sang tiếng Việt; chữ lớn hơn. Đã quan sát đủ 5 trang sau Refresh: Tổng quan 1.000 / 66,7% / 26,7 / 60%; Chất lượng 28,6% / 0,40 / 0,878 / 0,896; Nhân sự 5 người / 2 người có chỉ số QA cần chú ý; Hình học 285 / 5.696,1 px² / 0,27% / 35,1%; Ca khó 4 / 1. Đây là quan sát UI trên fixture, không phải lần chạy lại toàn bộ suite hay DAX reconciliation.
- RUN_LOCAL.ps1 phục vụ Desktop; RUN_DEMO.ps1 giữ thiết kế hiện có, chỉ rebuild PBIP khi yêu cầu rõ.
- RUN_LOCAL.ps1 -CheckOnly xuất data/desktop_readiness.json, chỉ lưu trạng thái cấu hình, không lưu secrets và không gọi API. Chế độ live chặn trước khi gửi request nếu thiếu host/task/token/repo. Kết quả local ngày 17/10: PBIX và CSV bundle có sẵn, đang là DEMO, CVAT_TOKEN chưa cấu hình; quyền API thật chưa được xác nhận.
- Runner có tổng hợp team_reports.json với mã nguồn dẫn chứng, offline mặc định; Gemini là tùy chọn chọn rõ, lỗi dùng offline. Tạo notification_preview.txt mặc định; module gửi Telegram/Discord chỉ chạy khi chọn rõ kênh.
- Extractor thu thập media metadata và quality report/data mới nhất theo task/job, ghi trạng thái lỗi nguồn tùy chọn. Tỷ lệ diện tích chỉ dùng metadata có bằng chứng; link frame ngoài phạm vi job bị đánh dấu invalid_frame.
- Fixture riêng: 5 người, 15 jobs, 285 bản ghi vẽ, 14 review rounds, 4 defects, 10 GT evals, 4 issues; nhãn DEMO luôn hiển thị.
- Workflow tại đúng .github/workflows, chạy tests và xuất artifacts; offline mặc định, live cần cấu hình vars/secrets.

## Bằng chứng

- Hoàn thiện launcher START_DEMO.cmd và src/desktop_demo.py: tạo dữ liệu → xuất 14 bảng + Mentor draft + summary/notification preview → mở report nếu chưa được sử dụng. Root launcher gọi Python trực tiếp, không thay execution policy. File PBIX đang mở được nhận diện qua sharing probe để tránh bản sao không lưu được.
- Transform 2026-10-17.3: snapshot ổn định S7b165b7d6fb96d18b2609d11; đã chạy lại demo nhiều lượt không đổi mã hoặc ghi đè CSV. source_snapshot chứa mã snapshot, run folder nằm ở receipt. Có khóa writer, staging và xử lý rollback serving state khi pointer switch lỗi thông thường; chưa chạy fault injection cho mọi nhánh lỗi.
- Lượt end-to-end cuối: START_DEMO.cmd exit 0; Refresh và Save thành công trong cửa sổ PBIX gốc. check_dax.ps1 xác nhận loaded_snapshot_id đúng current.json và 20/20 KPI khớp Python, tolerance 1e-9. Không chạy lại toàn bộ unit suite trong lượt này.

- 86 tests pass, gồm replay, publish thất bại, partial annotations, null vs 0, GT mới nhất, frame overlap, giữ nguyên snapshot nguồn, tham chiếu DAX và đường lọc model.
- Lượt bổ sung trước các chỉnh sửa cuối phiên: 36 bài của summary/notifier/pipeline pass, gồm 19 bài mới cho hai module summary/notifier. Chưa chạy lại toàn bộ suite sau các chỉnh sửa cuối phiên; không gộp các lượt chạy thành tuyên bố toàn bộ suite đã pass.
- Chạy RUN_DEMO.ps1 sau các chỉnh sửa cuối phiên thành công: snapshot Sac7a9bd3585b47cb2a7c2f20, đủ 14 bảng, tổng hợp 3 báo cáo nhóm, notification ở trạng thái preview_only. Không gọi API Gemini hoặc gửi tin.
- 54 artifacts JSON qua schema Microsoft.
- Engine Power BI Desktop được truy vấn trực tiếp qua Microsoft ADOMD: 20/20 KPI khớp Python với tolerance tuyệt đối 1e-9, xem POWERBI_DAX_RECONCILIATION.json.
- KPI demo: 1.000/1.500 completed frames (proxy), 37,5 giờ, 26,6667 frames/h, FTPR 60%, rejection 28,5714%, mIoU 0,878, F1 0,896, 2 nhân sự có chỉ số rủi ro.

## Còn phụ thuộc cấu hình/dữ liệu của nhóm

Người dùng đã chọn tiếp tục bằng dữ liệu giả lập local. CVAT_TOKEN không còn là điều kiện chặn cho giai đoạn này; các mục nguồn thật dưới đây dành cho giai đoạn ghép với phần tích hợp của nhóm. RUN_DEMO đã chạy lại với metadata kích thước từng frame, snapshot S2c111c72af2d5c3756ce1450; xem powerbi/DEMO_SCENARIO.md.

1. CVAT_TOKEN trong .env hiện chưa có giá trị hợp lệ; chưa chạy nghiệm thu API thật. Không gửi token qua chat.
2. Ingestion chưa lấy đầy đủ events/analytics và review history. Đã có raw quality report/data, nhưng mapping sang GT KPI cần nguồn thật để xác nhận. operations.json là hợp đồng bổ sung từ nguồn đã xác nhận, không tự phát minh số liệu thiếu.
3. Power BI Service nằm ngoài đích vận hành Desktop đã thống nhất; chưa cấu hình gateway/credentials/refresh.
4. Workflow mới chưa commit/push hoặc chạy trên GitHub trong phiên này. Gemini và Telegram/Discord mới có mã nguồn và mock; chưa nghiệm thu API/gửi tin thật.
5. Tiếp tục UAT bộ lọc, ca khó và URL trên dữ liệu thật; kiểm tra phạm vi frame không thay thế kiểm tra nội dung ảnh.

## Cách chạy

Từ gốc repo: .\powerbi\RUN_DEMO.ps1. Mở powerbi/AnnotationReporter.pbix trong Power BI Desktop, Refresh và Save. Với nguồn nhóm dùng .\powerbi\RUN_LOCAL.ps1; xem powerbi/README.md. Không rebuild project khi đang chỉnh visual trong Desktop.

Đây là bản end-to-end local/offline đã chạy với Power BI thật. Chưa tuyên bố hệ thống vận hành cloud/live hoàn chỉnh khi các phụ thuộc trên chưa được nghiệm thu.
