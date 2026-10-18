# Dùng báo cáo trên nhiều máy Windows

## Phạm vi hỗ trợ

Mỗi máy chạy một bản local: Python ETL → SQLite audit → PostgreSQL trong Docker → Power BI Desktop DirectQuery. Không cần sửa đường dẫn theo tên tài khoản Windows. Mỗi máy có mật khẩu và dữ liệu riêng; các máy không tự đồng bộ database với nhau.

Luồng demo đã được nghiệm thu trên máy Minh. Bộ setup mới đã chạy trên cùng máy; chưa có bằng chứng nghiệm thu trên máy sạch thứ hai. Chế độ live có đường chạy chung nhưng cần dữ liệu và quyền truy cập thật để nghiệm thu. Không coi cấu hình thành công là đã xác nhận visual hoặc DAX.

## 1. Chuẩn bị một lần

- Máy Windows có Python 3.10+, Power BI Desktop hỗ trợ định dạng PBIP/PBIR của repo và Docker Desktop có engine chạy.
- Python phải có lệnh `py` hoặc `python` trong PATH. Cần Internet lần đầu để cài thư viện và tải image PostgreSQL.
- Clone repo vào thư mục người dùng có quyền ghi; đường dẫn có dấu cách được hỗ trợ. Không sao chép `.venv` từ máy khác.

Chạy **START_AUTO.cmd**. Nó tự tạo `.venv`, cài các phiên bản trong `requirements-desktop.txt`, tạo `config/desktop.local.json` và `.env` nếu chưa có, khởi động database riêng rồi chạy demo và mở Power BI. File cấu hình đã có được giữ nguyên.

Nếu chỉ muốn chuẩn bị Python trước, chạy **SETUP_AUTO.cmd**; lệnh này chưa khởi động database và chưa publish báo cáo. Không tự cài Python, Docker hoặc Power BI.

## 2. Kết nối Power BI lần đầu

1. Khi Power BI hỏi thông tin PostgreSQL, nhập tài khoản trong `data/directquery/powerbi_connection.json` ngay trên máy đó. Không đưa file này lên Git hoặc gửi qua chat.
2. Mở đủ 5 trang để kiểm tra visual. Project đã đặt Page refresh On, mặc định 10 giây. Nếu mở PBIP, Save As `AnnotationReporter_Auto.pbix` trong **cùng thư mục chứa PBIP**.
3. Để trang Tổng quan mở. Trong terminal tại repo, chạy:

   ```powershell
   .\START_AUTO.cmd --mode demo --completed-jobs 11
   ```

4. Đợi chu kỳ refresh; số frames cần tự đổi từ 1.000 sang 1.100, tiến độ 66,7% sang 73,3%. Không bấm Refresh/Save trong lúc quan sát. Sau đó chạy `START_AUTO.cmd --mode demo --completed-jobs 10` để về mặc định và quan sát 1.000 trở lại.
5. Sau khi chính bạn đã thấy dữ liệu tự đổi, chạy:

   ```powershell
   .\START_AUTO.cmd --confirm-desktop
   ```

Lệnh cuối ghi nhận **xác nhận của người dùng**, kiểm tra settings refresh trong PBIX và snapshot PostgreSQL. Nó không tự quan sát visual và không thay thế đối chiếu DAX. Marker chỉ dùng local và gắn SHA256 của đúng PBIX; khi sửa thiết kế, cần lưu và xác nhận lại. Muốn đối chiếu 20 KPI bằng engine Desktop, dùng `powerbi/check_dax.ps1` với Microsoft ADOMD client theo hướng dẫn trong script; client này không được bộ setup tự tải/cài.

## 3. Cấu hình riêng từng máy

File mẫu: `config/desktop.example.json`. File sử dụng: **config/desktop.local.json** (gitignore). Không điền mật khẩu/token vào JSON này. Đường dẫn tương đối được tính từ thư mục gốc repo; ưu tiên cách này khi chia sẻ cấu trúc với nhóm.

| Trường | Ý nghĩa |
|---|---|
| `mode` | `demo` (mặc định), `offline` hoặc `live` |
| `port` | Cổng PostgreSQL local, mặc định 55432; phạm vi 1024–65535 |
| `refresh_seconds` | Chu kỳ trang đang xem, mặc định 10; phạm vi 1–3600 |
| `completed_jobs` | Tình huống demo 0–15, mặc định 10 |
| `snapshot` | Thư mục snapshot cho offline, có manifest.json và cvat.json |
| `task_id`, `repo` | CVAT task và GitHub OWNER/REPO cho live; null thì lấy .env |
| `operations` | File bổ sung giờ làm, review, defects và GT theo contract canonical |
| `team_reports` | File phản ánh từ nhóm để tổng hợp trong báo cáo |

CLI ghi đè JSON cho **lần chạy hiện tại**; JSON ghi đè giá trị mặc định. Ví dụ:

```powershell
.\START_AUTO.cmd --mode offline --snapshot "data/raw/snapshot_nhom" --operations "data/input/operations.json"
.\START_AUTO.cmd --port 55433 --refresh-seconds 15
```

Khi đổi cổng/chu kỳ, launcher tạo project riêng tại `data/directquery/reports/p<CỔNG>-r<GIÂY>/`, đồng bộ M query với cổng database, giữ bản thiết kế đang có. Save As `AnnotationReporter_Auto.pbix` trong thư mục project mới. Đóng bản báo cáo dùng cổng cũ trước khi đổi cấu hình. Để lần sau dùng cùng cấu hình, sửa JSON; nếu chỉ dùng CLI thì phải truyền lại các cờ đó khi chạy/xác nhận.

Tại cấu hình mặc định, dùng PBIX Auto đã có trong `powerbi/`. Không dùng bản Import `AnnotationReporter_Desktop.pbix` cho quy trình tự cập nhật này.

## 4. Dùng dữ liệu thật

Điền `CVAT_HOST`, `CVAT_TOKEN`, `CVAT_TASK_ID`, `GITHUB_REPO` và `GITHUB_TOKEN` khi repo cần xác thực vào `.env` trên từng máy. Tài khoản phải truy cập được CVAT (bao gồm VPN/LAN nếu có). Sau đó chọn `mode: live` hoặc:

```powershell
.\START_AUTO.cmd --mode live --task-id 217 --repo OWNER/REPO --operations "data/input/operations.json" --team-reports "data/input/team_reports.json"
```

Luồng chung là lấy API thật → canonical report/Agent → PostgreSQL → DirectQuery. Nếu nguồn không lấy được, launcher dừng; không chuyển âm thầm sang demo. Demo chỉ dùng khi chọn demo. Nguồn thiếu giờ làm/review/GT thì KPI tương ứng vẫn thiếu, không tự gán số giả. Xem contract trong `src/reporting_pipeline.py` và ví dụ cấu trúc `sample_data/powerbi_demo/operations.json`; các giá trị trong ví dụ là giả lập, không dùng làm kết quả thật.

Launcher giữ tổng hợp offline và thông báo preview; không tự gọi Gemini hoặc gửi Telegram/Discord. Không có lịch ingestion chạy nền được cài bởi setup. Page refresh chỉ đọc dữ liệu đã publish; nó không tự lấy API CVAT mới.

## 5. Chẩn đoán và khôi phục

```powershell
.\START_AUTO.cmd --doctor
```

Bootstrap chuẩn bị runtime nếu cần trước khi chạy doctor. Doctor không publish dữ liệu hay khởi động Docker; đọc engine, Compose, cổng, cấu hình nguồn và liên kết file PBIX trên Windows. Liên kết file có tồn tại chưa chứng minh phiên bản Power BI tương thích hoặc đăng nhập đã thành công.

| Hiện tượng | Cách xử lý |
|---|---|
| Không tìm thấy Python | Cài Python 3.10+ với launcher/PATH, mở lại terminal hoặc chạy lại CMD |
| Cài thư viện/image lỗi | Kiểm tra Internet/proxy, chạy SETUP_AUTO rồi START_AUTO lại |
| Docker chưa chạy | Mở Docker Desktop, chờ engine sẵn sàng; doctor không tự bật engine |
| Cổng bị chiếm | Đổi `port` trong JSON; launcher sẽ tạo project tương ứng |
| Container cùng tên thuộc dự án khác | Giải quyết tên bị trùng; launcher không thay container đó |
| Một clone khác trên cùng máy đã có database | Dùng checkout ban đầu; một reporting instance được hỗ trợ trên mỗi máy. Không tạo mật khẩu mới cho volume cũ |
| Mất credentials nhưng volume còn | Khôi phục `data/directquery/connection.json` từ bản sao lưu riêng của máy; không xóa volume để sửa lỗi |
| Visual còn số cũ | Kiểm tra đúng PBIX/endpoint, Page refresh On, Docker đang chạy; trang đang xem mới tự cập nhật |
| Báo thiết lập chờ sau khi sửa thiết kế | Lưu PBIX, quan sát dữ liệu tự đổi rồi xác nhận lại |

Lỗi gần nhất: `data/directquery/last_failure.json`; chi tiết lệnh subprocess thất bại: `last_process_error.log` trong cùng thư mục. Cấu hình Docker bind 127.0.0.1; chưa hỗ trợ dùng chung PostgreSQL qua mạng. Không commit `.env`, `.venv`, `config/desktop.local.json` hoặc `data/directquery`.

## Bàn giao sang máy thứ hai

Clone mới → START_AUTO → đăng nhập PostgreSQL → quan sát 1.000/1.100/1.000 → xác nhận local. Ghi lại phiên bản Python/Docker/Power BI và kết quả vào biên bản của máy đó. Chỉ tuyên bố nghiệm thu trên máy thứ hai sau khi đã thực hiện các bước này; kết quả trên máy Minh không thay thế được.
