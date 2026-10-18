# Kiểm tra module 1 — CVAT API ingestion

**Cập nhật sau review:** đã nghiệm thu API thật trên CVAT Cloud bằng task DEMO 2679097. Task/jobs/labels/annotations/media đạt; đọc lại đúng 3 shapes đã lưu từ UI. Quality list thành công nhưng chưa có report. Chi tiết và phạm vi giới hạn: [CVAT_LIVE_ACCEPTANCE_2026-10-18.md](CVAT_LIVE_ACCEPTANCE_2026-10-18.md). Các đoạn mô tả kiểm thử offline bên dưới ghi lại giai đoạn review trước lượt live.

## Phạm vi

Đọc BaseClient, CVATExtractor, runner sync, hợp đồng dữ liệu và đường sử dụng trong normalizer/canonical reporting. Đối chiếu tài liệu CVAT chính thức, dùng kiểm thử offline có mock; không đăng nhập, không gọi task thật, không thay dữ liệu CVAT hoặc credentials.

## Phát hiện và sửa

| Mức | Vấn đề | Xử lý |
|---|---|---|
| Cao | Quality list dùng task_id nhưng thiếu target theo API hiện tại; lỗi bị coi như không có report | Gọi riêng target=task/job, ghi trạng thái/error_type/http_status theo từng nguồn; giữ dữ liệu lấy được khi một phần lỗi |
| Cao | Job report có task_id=null có thể bị loại nhầm | Xác minh job_id thuộc danh sách annotation jobs đã lấy; task report phải đúng task, không nhận project report |
| Cao | Bảo vệ URL chỉ kiểm tra netloc, vẫn chấp nhận HTTPS → HTTP cùng host | Giữ nguyên scheme/origin, từ chối credentials nhúng và fragment; tiếp tục cấm HTTP redirect |
| Trung bình | next dạng ?page=2 bị nối vào gốc host; org có thể lặp ở query | Nối relative next theo resource hiện tại, giữ hỗ trợ api/...; không thêm org khi URL đã có |
| Trung bình | Phân trang có thể chạy dài với URL mới liên tục, payload items không được kiểm tra | max_pages=10000, nhận diện vòng lặp theo URL/query chuẩn hóa và kiểm tra từng item/next |
| Cao | Task/jobs chưa kiểm tra scope/ID trùng; annotations thiếu arrays có thể coi là rỗng hợp lệ | Kiểm tra task identity, job task_id/ID trùng, tags/shapes/tracks và track shape objects |
| Trung bình | Issues lỗi làm mất cả snapshot core; comments/media lỗi thiếu chẩn đoán | Issues/comments/media ghi explicit availability. Core task/jobs/labels vẫn bắt buộc; canonical publication vẫn chặn annotations thiếu |
| Trung bình | Metadata QA được báo available dù không có điểm; toán tử or làm mất điểm 0 | Chỉ available khi trường điểm được hỗ trợ có giá trị; giữ 0. Không tự ánh xạ summary mới thành điểm cũ |
| Trung bình | Manifest/report không phản ánh đủ lỗi tùy chọn | Sao chép availability vào manifest; normalizer đưa cảnh báo vào báo cáo |
| Thấp | Session chưa đóng sau các request/verification live | Thêm close và đóng hai session sau bước liên kết trong finally |

Tăng TRANSFORM_VERSION thành 2026-10-18.1 vì nội dung warnings phục vụ báo cáo thay đổi; replay sau nâng cấp có identity mới, tránh ghi đè bundle bất biến cũ.

## Kiểm chứng

- Bộ tập trung BaseClient/CVAT/GitHub/normalizer: 34/34 qua ở lần đầu, trước khi thêm regression cảnh báo cuối cùng.
- Chạy hồi quy toàn tests: 135 tests qua sau các sửa cuối cùng. Kiểm thử dùng dữ liệu tạm/mock; không phải bằng chứng API thật hoặc visual Desktop.
- Lần chạy toàn suite trong sandbox thất bại vì Windows không cho dọn thư mục tempfile (WinError 5). Đã chạy lại với quyền phù hợp; không sửa ACL hoặc tắt bảo vệ.

## Giới hạn còn cần xử lý trước nghiệm thu live

1. **Giờ làm việc:** extractor chưa lấy Analytics/event logs. Canonical cần operations.job_times; không dùng updated_date làm giờ làm hoặc ngày hoàn thành.
2. **GT/QA:** đã tải Quality Reports raw, chưa ánh xạ summary/chi tiết theo phiên bản CVAT thành ground_truth_evals. FTPR/rejection cần lịch sử review thực; không suy ra từ điểm Quality Report.
3. **Theo phiên bản:** server cũ có thể khác PAT/quality endpoints hoặc không có quyền/license. Cần nghiệm thu trên đúng deployment; lỗi 401/403/404 phải xử lý theo quyền và phiên bản, không đổi thành zero.
4. **Tính nhất quán:** snapshot gồm nhiều GET tuần tự, không phải transaction CVAT. Task đang sửa có thể thay đổi trong quá trình lấy. Chưa có cơ chế phát hiện mọi thay đổi hoặc snapshot phía server.
5. **Quy mô:** annotations và các list hiện được giữ trong RAM, lấy tuần tự từng job. Chưa có incremental ingestion/checkpoint; retry chỉ áp dụng GET, ba lần cho 429/5xx, timeout mỗi request 10/60 giây, không có deadline tổng cho toàn task.
6. **Track:** đếm shape/keyframe, không nội suy thành toàn bộ frame hay đếm object duy nhất. Canonical từ chối overlap thay vì cộng đúp frame; cần đặc tả riêng nếu dùng task có overlap/consensus.
7. **Media:** metadata không đủ để ánh xạ kích thước frame sẽ để thiếu tỷ lệ diện tích; chưa hỗ trợ đầy đủ skeleton/3D và các kiểu không đo được.

## Nguồn chính thức

- PAT Bearer: https://docs.cvat.ai/docs/api_sdk/access_tokens/
- Quality API, target filter và report data: https://docs.cvat.ai/docs/api_sdk/sdk/reference/apis/quality-api/
- QualityReport với task_id nullable: https://docs.cvat.ai/docs/api_sdk/sdk/reference/models/quality-report/
- JobRead, stage/state/frame_count: https://docs.cvat.ai/docs/api_sdk/sdk/reference/models/job-read/

Chưa commit/push các sửa trong lượt kiểm tra module này.
