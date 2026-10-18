# Vận hành end-to-end trên máy local

Phạm vi hiện tại: dữ liệu giả lập → báo cáo Mentor + SQLite + CSV → Power BI Desktop. Không cần máy chủ CVAT, API key Gemini, Telegram hoặc Power BI Service.

## Dùng hằng ngày

1. Bấm đúp **START_DEMO.cmd** ở gốc repo. Lệnh tạo fixture, chạy pipeline, xuất báo cáo và mở PBIX nếu file chưa được sử dụng. Khi file đang mở hoặc chỉ đọc, launcher giữ cửa sổ hiện có và in thông báo, tránh mở bản sao gây lỗi Save.
2. Trong Power BI Desktop chọn **Refresh** và chờ hoàn tất.
3. Bấm **Ctrl+S**. Nếu báo file đang được sử dụng, chỉ giữ cửa sổ gốc đã mở file để Refresh/Save; đóng bản sao không chứa chỉnh sửa cần giữ.

Khi chỉ muốn xuất dữ liệu mà không mở ứng dụng, dùng:

```powershell
.\.venv\Scripts\python.exe -X utf8 -B src/desktop_demo.py
```

Hoặc `.\powerbi\RUN_DEMO.ps1` trong PowerShell cho phép chạy script local. START_DEMO.cmd gọi Python trực tiếp, không phụ thuộc execution policy của Windows PowerShell và không thay đổi chính sách máy.

## Cài trên máy mới

Máy cần Windows, Python 3.10+ và Power BI Desktop hỗ trợ PBIP/PBIR. Từ gốc repo:

```text
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-runtime.txt
.venv\Scripts\python.exe -X utf8 -B powerbi/build_project.py --output powerbi/project_desktop
```

Sau đó START_DEMO.cmd. Khi chuyển máy, mở PBIP vừa tạo để SourceFolder trỏ đúng vị trí dữ liệu; PBIX sao chép từ máy khác có thể giữ đường dẫn cũ. Nếu đã sửa thiết kế, chỉ đổi tham số SourceFolder trong Power Query; lệnh build sẽ tái tạo thiết kế từ template.

## Tìm kết quả mới nhất

- `data/runs/latest.json`: mã snapshot, đường dẫn thư mục chạy, báo cáo Mentor, trạng thái thông báo và bước Desktop còn chờ.
- `data/runs/<timestamp>/run_status.json`: trạng thái riêng của lượt chạy, gồm lỗi trước/sau publication.
- `MENTOR_REPORT_DRAFT.md`, `team_summary.json`, `notification_preview.txt`, `notification_receipt.json`: trong thư mục chạy.
- `data/processed/current.json`: bộ CSV mà Power BI sẽ đọc khi Refresh.
- `data/processed/snapshots/<snapshot_id>/bundle.json`: SHA-256 các CSV của phiên bản mới.
- `powerbi/AnnotationReporter_Desktop.pbix`: bản báo cáo đã đóng gói.

`data_and_reports_ready` xác nhận phần dữ liệu và báo cáo đã xuất xong, chưa xác nhận Desktop đã Refresh/Save. Mỗi lượt pipeline mới đặt `desktop_status=refresh_and_save_required`. Việc mở được cửa sổ không đồng nghĩa dữ liệu trong model đã cập nhật.

## Độ bền publication

- Khóa hệ điều hành ngăn writer chạy đồng thời trên cùng database/output và ngăn hai launcher demo sửa fixture cùng lúc. Khóa tự nhả khi tiến trình kết thúc.
- Ghi đủ CSV vào thư mục staging rồi mới đưa thành bundle. Bundle đã phục vụ không bị ghi đè khi replay cùng nội dung.
- Snapshot dùng mã ổn định; đường dẫn thư mục mỗi lần chạy nằm ở receipt. Replay cùng dữ liệu không nhân đôi facts hoặc thay CSV đang được đọc.
- Nếu bundle tồn tại nhưng nội dung bị sửa/thiếu, dừng publication để xử lý thay vì dùng số liệu không nhất quán.
- CSV phải chuẩn bị xong trước khi đổi serving state. Nếu đổi current.json lỗi thông thường, phục hồi serving state SQLite trước đó.
- SQLite và filesystem không có transaction chung. Mất điện/dừng cưỡng bức giữa hai lần chuyển vẫn cần chạy lại pipeline để đồng bộ, rồi mới Refresh. Thư mục `.partial-*` không bao giờ là bundle đang phục vụ.
- Không Refresh đồng thời với lúc pipeline thay current.json. Chờ lệnh kết thúc thành công.

## Xác nhận Desktop đọc đúng bản mới

`powerbi/check_dax.ps1` đọc mã snapshot đã import trong model và so với current.json trước khi đối chiếu 20 KPI. Nếu chọn nhầm engine hoặc chưa Refresh, lệnh dừng. Cần Microsoft ADOMD client và PowerShell có quyền kết nối localhost; xem README.md. Kết quả ở `reports/POWERBI_DAX_RECONCILIATION.json`.

## Mức tự động hóa

Tự động: tạo dữ liệu giả lập, xử lý, publication, Markdown, tổng hợp offline và thông báo xem trước. Desktop còn Refresh và Save trong giao diện. Microsoft ghi rõ processing commands gửi tới model đang chạy trong Desktop không được hỗ trợ; không dùng đường đó để thay bước Refresh. Nguồn: https://learn.microsoft.com/en-us/power-bi/transform-model/desktop-external-tools#data-modeling-operations

Không tuyên bố vận hành tự động cloud/live: CVAT thật, Gemini/gửi bot thật, lịch GitHub và Power BI Service chưa được nghiệm thu trong phạm vi demo này.
