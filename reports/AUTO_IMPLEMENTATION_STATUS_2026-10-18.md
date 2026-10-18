# Trạng thái tự động hóa Desktop — 18/10/2026

## Đã chạy được

- Sửa publication CSV để không cần rename cả thư mục trên Windows; marker bundle.json ghi sau các file, current.json vẫn chỉ đổi sau khi chuẩn bị xong bundle. Không thay đổi ACL hoặc chính sách Windows.
- Container riêng annotation-reporter-db dùng PostgreSQL 17 đang healthy, chỉ bind 127.0.0.1:55432. Không dùng hoặc sửa database CVAT.
- src/auto_desktop.py đã chạy hết 4 bước: tạo dữ liệu giả lập, pipeline canonical, báo cáo Mentor/đối chiếu Agent và publish vào PostgreSQL.
- Snapshot đã publish: S8d8a6c583f93e38250fcc5fc. Đã xác nhận bằng tài khoản annotation_reader: đúng snapshot, số dòng đủ 14 serving views; không có quyền INSERT vào gold hoặc CREATE trong schema public.
- Đã tạo project_auto/AnnotationReporter.pbip với 14 bảng DirectQuery, giữ bố cục 5 trang từ bản Desktop tiếng Việt. Có START_AUTO.cmd và requirements-auto.txt.
- Mật khẩu ngẫu nhiên chỉ nằm trong data/directquery, được gitignore; không ghi mật khẩu vào M/PBIP.

## Đã hoàn tất phần Power BI

1. Người dùng đã đăng nhập PostgreSQL thành công; Desktop hiển thị dữ liệu qua DirectQuery.
2. Bật Page refresh bằng điều khiển Desktop, lấy cấu hình được Desktop lưu và áp dụng 10 giây cho cả 5 trang. Đã lưu bản `powerbi/AnnotationReporter_Auto.pbix`; kiểm tra trực tiếp cả 5 page.json bên trong PBIX đều On/PT10S.
3. Chạy demo 11 jobs: quan sát Tổng quan tự đổi 1.000 → 1.100 frames, 66,7% → 73,3%, không Refresh/Save. Khớp 20/20 KPI bằng engine Desktop, cùng snapshot Se9c4113e89c265be1df0ea88.
4. Sau khi lưu bản Auto, publish lại mặc định 10 jobs: visual tự trở về 1.000 frames/66,7%, không Refresh/Save. PBIX giữ nguyên kích thước 92.217 bytes và thời gian sửa. Đối chiếu lại 20/20 KPI khớp snapshot S8d8a6c583f93e38250fcc5fc.
5. Đã mở đủ 5 trang Tổng quan, Chất lượng, Nhân sự, Hình học, Ca khó trong Desktop và không thấy visual lỗi. Chỉ số phân nhóm ở dòng tổng Nhân sự để trống theo chủ ý.
6. Ghi bằng chứng `reports/POWERBI_AUTO_ACCEPTANCE.json`, hai file `POWERBI_AUTO_DAX_RECONCILIATION*.json` và marker local `data/directquery/desktop_ready.json`. Launcher chỉ công nhận marker khi SHA256 khớp đúng PBIX đã nghiệm thu.

## Phạm vi vận hành

Luồng demo local đã chạy từ launcher → dữ liệu giả lập → báo cáo Mentor/Agent → PostgreSQL → visual tự cập nhật. Người dùng chạy START_AUTO.cmd để bắt đầu mỗi lần; chưa cài lịch ingestion chạy nền. Trang đang xem refresh mỗi 10 giây, các trang khác truy vấn khi mở. Docker/database cần hoạt động. Save chỉ cần khi sửa thiết kế hoặc measures.

Chưa nghiệm thu CVAT thật, Gemini thật, bot gửi ra ngoài hoặc Power BI Service/Gateway. Bản Import cũ vẫn theo quy trình Refresh/Save cũ. Không chạy bộ unit tests trong lượt này; bằng chứng trên là các lần vận hành pipeline và đối chiếu trực tiếp engine Desktop. Các thay đổi tự động hóa mới chưa commit/push trong lượt này.
