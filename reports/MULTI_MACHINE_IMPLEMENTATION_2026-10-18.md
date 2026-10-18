# Bàn giao Desktop trên nhiều máy — 18/10/2026

## Đã triển khai

- START_AUTO.cmd tìm Python launcher/PATH và gọi bootstrap bằng đường dẫn repo có quote; không phụ thuộc tên tài khoản hay thư mục hiện hành của terminal.
- SETUP_AUTO.cmd chuẩn bị runtime riêng: tạo .venv, cài requirements-desktop.txt với phiên bản trực tiếp và transitive cố định, tạo cấu hình local và .env nếu chưa có. Không ghi đè file đã có; không tự cài phần mềm hệ thống.
- config/desktop.example.json là mẫu không chứa secrets; desktop.local.json được gitignore. CLI ghi đè từng lần; hỗ trợ demo/offline/live, cổng, refresh, snapshot, task, repo, operations và team reports.
- Cổng được truyền nhất quán vào Compose, pg8000, credential hướng dẫn kết nối và M query của project được tạo riêng cho cấu hình mới. Database chỉ bind loopback, một reporting instance trên mỗi máy.
- Source live có preflight cấu hình trước khi chạy Docker; không tự fallback sang demo. Nguồn thiếu nghiệp vụ không được bổ sung KPI giả.
- Doctor đọc Docker engine/Compose, cổng, cấu hình nguồn và liên kết PBIX; không publish hay bật Docker. Bootstrap có thể chuẩn bị runtime trước khi gọi doctor.
- Có lệnh ghi nhận người dùng xác nhận Desktop sau khi đã quan sát visual đổi số liệu; kiểm tra 5 trang Page refresh trong PBIX và snapshot phục vụ, không gọi đó là đối chiếu DAX tự động.
- Giữ mật khẩu runtime hiện có, không ghi vào project hoặc cấu hình public. Không thay container cùng tên của dự án khác. Dừng và hướng dẫn khôi phục nếu phát hiện database cũ nhưng checkout thiếu credential.
- README và powerbi/MULTI_MACHINE_SETUP.md là điểm vào cho thành viên mới.

## Các lần vận hành thực tế trên máy Minh

- Bootstrap --setup-only hoàn tất với Python 3.12.14, các thư viện pinned đã có; tạo desktop.local.json ở chế độ demo và giữ .env cũ.
- Chạy src/auto_desktop.py --mode demo: đủ bốn bước, snapshot S8d8a6c583f93e38250fcc5fc, reader kiểm tra đủ 14 serving views.
- Chạy đúng START_AUTO.cmd --doctor: Docker CLI/engine/Compose, cấu hình nguồn, liên kết PBIX và cổng đều trả true.
- Không chạy bộ unit tests trong lượt triển khai này. Kết quả DAX/visual trước thay đổi được giữ ở POWERBI_AUTO_ACCEPTANCE.json, không coi đó là nghiệm thu trên máy khác.

## Giới hạn nghiệm thu

Chưa có máy sạch thứ hai để xác nhận toàn bộ setup và visual; chưa gọi CVAT thật, Gemini hoặc gửi bot trong lượt này. Python/Docker/Power BI vẫn cần cài sẵn, đăng nhập PostgreSQL thực hiện một lần trên mỗi máy. Không hỗ trợ Power BI Desktop trên macOS/Linux trong bộ launcher CMD này. Database giữa các máy chưa đồng bộ dùng chung. Không cài scheduler ingestion; người dùng kích hoạt launcher, Page refresh chỉ truy vấn dữ liệu đã publish.

Máy thứ hai cần thực hiện quy trình trong MULTI_MACHINE_SETUP.md và ghi lại phiên bản cùng kết quả quan sát trước khi đánh dấu nghiệm thu. Các thay đổi lượt này chưa commit/push.
