# Sửa dữ liệu trống trong Power BI — 18/10/2026

## Đã sửa và kiểm chứng

Report: `powerbi/AnnotationReporter_Auto.pbix`, đã lưu bằng Desktop.
Nguồn: CVAT Cloud task 2679456 trong Organization `synthetic-e2e`.
Đây là bộ ảnh kiểm thử giả lập đã nạp lên CVAT; số liệu đọc từ API thật.
Không dùng giờ làm, lịch sử review hoặc điểm GT mô phỏng bổ sung.

- Ánh xạ các báo cáo QA cấp job thuộc đúng báo cáo task mới nhất, không cộng đúp task/child reports.
- Tính precision/recall/F1 micro từ confusion matrix với đúng trục dự đoán/GT;
  chỉ gộp requirement cơ sở không chồng lấn. Giữ mIoU hình học là null khi nguồn không cung cấp.
- Nạp 21 conflicts tự động vào bảng lỗi, có job/frame/nhãn và link CVAT;
  `review_id=null`, không tạo reviewer hoặc lượt review giả.
- Nạp 5 CVAT issues đang mở cùng comments vào bảng ca khó. Issue đã giải quyết bị loại;
  tham chiếu ngoài job/frame bị chặn link; định danh riêng không trùng GitHub issue.
- KPI hiện có: 20 frames hoàn thành theo trạng thái job, 540 shapes,
  21 lỗi QA tự động, 3,5 lỗi/job được QA, F1 trung bình theo job **0,750**,
  5 ca khó mở. F1 0,750 là trung bình sáu F1 cấp job, không phải F1 micro toàn task.
- Hai biểu đồ lỗi trên trang Chất lượng và bảng ca khó đã có dữ liệu trong Desktop.
- Đã cập nhật ba measures trong report đang mở và nguồn TMDL/DAX; giữ bố cục.
- Launcher được cấu hình dùng task mới, Organization mới và bỏ operations/team-reports bổ sung cũ.
- Snapshot phục vụ: `Sce75c5f945ca3d38afc91e12`.

## Các ô vẫn trống đúng theo nguồn

| Chỉ số | Nguyên nhân |
|---|---|
| Giờ làm, vận tốc, AHT | Chưa có dữ liệu active time đáng tin cậy |
| FTPR, rejection, lịch sử review | Chưa có các lượt review thực và quyết định theo vòng |
| mIoU | Báo cáo QA hiện có confusion matrix, không có spatial IoU; không đổi classification Jaccard thành mIoU |
| Mật độ lỗi/100 frames hoàn thành | Conflicts lấy trên mẫu GT gồm các jobs chưa hoàn thành; không chia cho số frames hoàn thành khác phạm vi |
| Sản lượng theo ngày hoàn thành | Không dùng ngày cập nhật job làm ngày hoàn thành |

Đã cập nhật hướng dẫn nguồn dữ liệu trên trang Tổng quan. Không thay null thành 0.
Giới hạn ba vai trò vẫn còn: reviewer chưa tham gia được vì quota thành viên CVAT.

## Bằng chứng

- Toàn bộ **150 tests pass** sau các sửa cuối, gồm mapping QA, scoping,
  duplicate reports/conflicts, zero F1, dữ liệu thiếu, trộn review/QA và pipeline.
- Engine Power BI Desktop: **20/20 KPI khớp** Python, tolerance 1e-9,
  kể cả các giá trị null có chủ ý; không có slicer trong truy vấn đối chiếu.
- `POWERBI_QA_MAPPING_DAX_RECONCILIATION_2026-10-18.json`.
- `POWERBI_QA_MAPPING_ACCEPTANCE_2026-10-18.json`: hash PBIX đã lưu,
  cấu hình refresh 10 giây của năm trang; quan sát trực tiếp Tổng quan/Chất lượng/Ca khó.
- Ảnh local: `data/cvat_realistic_seed/powerbi_quality_fixed.jpg`, `powerbi_cases_fixed.jpg`.
- Bản sao trước sửa: `powerbi/AnnotationReporter_Auto_20261018_qa_backup.pbix` (gitignored).

Quy tắc đọc confusion matrix dựa trên [CVAT Automated QA](https://docs.cvat.ai/docs/qa-analytics/auto-qa/).
