# Luồng tự động với Power BI Desktop DirectQuery

## Kiến trúc

Đã hoàn tất thiết lập trên máy Minh ngày 18/10/2026: lưu `AnnotationReporter_Auto.pbix`, 14 bảng DirectQuery, 5 trang tự cập nhật mỗi 10 giây. Đã quan sát Tổng quan đổi 1.000 → 1.100 → 1.000 frames mà không Refresh/Save khi dữ liệu đổi; PBIX giữ nguyên thời gian sửa. Cả hai snapshot khớp 20/20 KPI với engine Desktop (reports/POWERBI_AUTO_DAX_RECONCILIATION*.json).

`START_AUTO.cmd` → Docker reporting database → dữ liệu giả lập → pipeline canonical + báo cáo Mentor/Agent → PostgreSQL serving views → Power BI DirectQuery → tự cập nhật trang đang xem.

SQLite vẫn lưu audit/history của pipeline. PostgreSQL là tầng phục vụ DirectQuery riêng, có snapshot và serving pointer; không dùng database CVAT. Docker Compose chỉ quản lý container `annotation-reporter-db`, bind `127.0.0.1:55432`, không mở database ra mạng LAN.

## Thiết lập một lần

1. Windows có Python 3.10+, Docker Desktop đang chạy và Power BI Desktop đã cài. Tạo `.venv` nếu máy chưa có.
2. Chạy `START_AUTO.cmd`. Lần đầu cài driver từ requirements-auto.txt nếu thiếu, tạo credentials ngẫu nhiên trong `data/directquery` và khởi tạo PostgreSQL.
3. Power BI mở `project_auto/AnnotationReporter.pbip`. Khi yêu cầu đăng nhập, dùng thông tin trong `data/directquery/powerbi_connection.json`. Tài khoản `annotation_reader` chỉ được SELECT các serving views; mật khẩu không được ghi vào PBIP hoặc Git.
4. Project được tạo sẵn Automatic page refresh 10 giây cho cả 5 trang. Hoàn tất kết nối trong Desktop, kiểm tra Page refresh đang On; lưu một lần thành `powerbi/AnnotationReporter_Auto.pbix`.
5. Chỉ đánh dấu `data/directquery/desktop_ready.json` sau khi đã quan sát dữ liệu thay đổi trên visual mà không bấm Refresh. File này là bằng chứng thiết lập trên máy hiện tại, không dùng chung giữa các máy.

Trạng thái hiện tại được ghi trong data/directquery/latest.json. Có database mới chưa đồng nghĩa các trang đã tự cập nhật; nếu chưa có desktop_ready.json, launcher vẫn thông báo thiết lập đang chờ.

## Các lần chạy tiếp theo

Bấm `START_AUTO.cmd`. Pipeline cập nhật PostgreSQL trong transaction. Báo cáo đã cấu hình DirectQuery đọc phiên bản mới; không cần import Refresh và không cần Save lại PBIX chỉ vì số liệu thay đổi. Save vẫn cần nếu thay thiết kế hoặc measures.

Nếu báo cáo đang mở, launcher không mở bản sao khi PBIX bị khóa. Nếu chưa mở, launcher mở bản Auto. Trang đang xem mới tự refresh; trang khác truy vấn khi chuyển sang xem. Docker/database cần tiếp tục chạy trong lúc xem báo cáo.

Có thể thay đổi tình huống giả lập bằng CLI:

```powershell
.\.venv\Scripts\python.exe -X utf8 -B src/auto_desktop.py --completed-jobs 11
```

Tham số chấp nhận 0–15 jobs hoàn thành; mặc định 10. Đây là dữ liệu tổng hợp, không phải kết quả công việc thực tế của thành viên. Tài liệu và Power BI phải giữ nhãn DEMO.

## Phạm vi

- Tự động hiện tại dành cho dữ liệu giả lập local, không gửi bot và không gọi Gemini thật.
- Lệnh chạy khi được khởi động, chưa tự tạo lịch chạy nền. Docker có restart policy cho container, nhưng vẫn cần Docker Desktop hoạt động.
- Credentials chỉ có trong các file runtime đã gitignore. Không commit hoặc chia sẻ thư mục data/directquery.
- Không xóa Docker volume để sửa lỗi đăng nhập: volume chứa dữ liệu và role đã tạo. Giữ connection.json/postgres.env đồng bộ với container.
- Bản Import cũ (`AnnotationReporter_Desktop.pbix`) vẫn có quy trình Refresh/Save cũ; bản tự cập nhật là `AnnotationReporter_Auto.pbix`.

Nguồn kỹ thuật: [PostgreSQL connector](https://learn.microsoft.com/en-us/power-query/connectors/postgresql), [Automatic page refresh](https://learn.microsoft.com/en-us/power-bi/create-reports/desktop-automatic-page-refresh).
