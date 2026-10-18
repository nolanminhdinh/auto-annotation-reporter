# Dashboard mô phỏng đầy đủ — 18/10/2026

Đã tạo kịch bản local từ snapshot bộ ảnh CVAT kiểm thử hiện có, bổ sung đủ dữ liệu
cho 20 KPI và lưu `powerbi/AnnotationReporter_Auto.pbix` ở trang Tổng quan.
Không ghi thêm dữ liệu hoặc thay phân công trên CVAT/GitHub.

## Bộ dữ liệu

| Hạng mục | Số lượng |
|---|---:|
| Frame mục tiêu | 120 |
| Jobs | 6, trong đó 4 hoàn thành và 2 đang xử lý/chờ nghiệm thu |
| Người gán nhãn mô phỏng | 6 |
| Reviewer mô phỏng | 2 |
| Giờ làm mô phỏng | 6 |
| Shapes | 660 |
| Vòng review mô phỏng | 8 |
| Lỗi mô phỏng | 9, đủ 4 nhóm taxonomy và các mức độ |
| Kết quả GT mô phỏng | 6, có mIoU, precision, recall và F1 |
| Ngày hoàn thành có sản lượng | 4 |
| Ca khó/câu hỏi mở | 8, gồm 1 blocker mô phỏng |
| Báo cáo tổ mô phỏng | 3 |

Một số ảnh, nhãn, hình vẽ và issues gốc được kế thừa từ bộ CVAT kiểm thử.
Nhân sự, trạng thái workflow, giờ làm, review, lỗi, điểm GT, ngày hoàn thành và
các tình huống bổ sung là dữ liệu dựng cho dashboard, không phải hành vi người thật.
Job ban đầu chưa vẽ được bổ sung hình vẽ trong snapshot local từ geometry tham chiếu.
Các link CVAT chỉ mở bộ ảnh gốc; trạng thái trên server không được đổi theo snapshot local.

## Số liệu hiện trên dashboard

- Hoàn thành 80/120 frames theo proxy trạng thái job: **66,7%**.
- Vận tốc **13,33 frames/giờ**, AHT **4,5 phút/frame**.
- FTPR **50%**, rejection **37,5%**.
- **9 lỗi**, mật độ **11,25 lỗi/100 frames hoàn thành**.
  Tử số lỗi trong kịch bản này chỉ thuộc bốn jobs đã hoàn thành.
- mIoU mô phỏng **0,828333**; F1 mô phỏng trung bình theo job **0,860056**.
- Nhân sự: **6 người**, **3 người có chỉ số QA cần chú ý** trong mô phỏng.
- **8 ca mở**, **1 blocker**.

F1 được tính nhất quán từ precision/recall mô phỏng; mIoU là giá trị mô phỏng có chủ ý,
không phải kết quả đo hình học thật. Không suy diễn đánh giá năng lực người dùng CVAT.

## Vận hành và nhận diện

- Cả năm trang có banner **MÔ PHỎNG ĐẦY ĐỦ / KHÔNG PHẢI KẾT QUẢ VẬN HÀNH THẬT**.
- Snapshot local tại `data/dashboard_simulation_full/` (gitignored).
- Launcher `START_AUTO.cmd` hiện chạy offline từ snapshot này; không cần gọi CVAT để xem mô phỏng.
- Bản cấu hình live trước chuyển chế độ được lưu ở
  `data/dashboard_simulation_full/desktop_live_config_backup.json`.
- Có thể khôi phục nội dung bản cấu hình đó vào `config/desktop.local.json` khi quay lại nguồn live.
  Khi dùng lại nguồn live, một số KPI sẽ trống nếu nguồn thật vẫn thiếu giờ làm/review/mIoU.
- Script tạo dữ liệu: `tools/create_full_dashboard_simulation.py`.
- Pipeline chặn operations được đánh dấu mô phỏng nếu manifest chưa đánh dấu fixture.

## Kiểm chứng

- **152 tests pass** sau các sửa cuối, gồm kiểm tra nhãn/provenance mô phỏng.
- Engine Power BI Desktop: **20/20 KPI khớp Python**, không còn giá trị null trong 20 KPI;
  tolerance tuyệt đối 1e-9; truy vấn đối chiếu không có slicer.
- Đã mở kiểm tra đủ năm trang: Tổng quan, Chất lượng, Nhân sự, Hình học, Ca khó;
  có số liệu ở các thẻ KPI, biểu đồ theo ngày, lịch sử review và bảng nhân sự/ca khó.
- Đã Save trong Desktop; cấu hình refresh 10 giây của năm trang được kiểm tra trong PBIX đã lưu.
- Snapshot phục vụ: `S95ff943e25c3b0b256b6de00`.
- Bằng chứng: `POWERBI_FULL_SIMULATION_DAX_RECONCILIATION_2026-10-18.json`,
  `POWERBI_FULL_SIMULATION_ACCEPTANCE_2026-10-18.json`.
- Ảnh từng trang nằm trong `data/dashboard_simulation_full/powerbi_*.jpg`.
- Bản sao PBIX trước đổi banner: `powerbi/AnnotationReporter_Auto_before_simulation_backup.pbix`.

Các dòng tổng của bảng nhân sự có thể để trống phân nhóm vì không đại diện một người;
đây không phải KPI thiếu dữ liệu.
