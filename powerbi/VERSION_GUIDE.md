# 🗺️ HƯỚNG DẪN ĐIỀU HƯỚNG CÁC PHIÊN BẢN BÁO CÁO POWER BI

Tài liệu này tổng hợp toàn bộ cây phiên bản báo cáo Power BI của dự án `auto-annotation-reporter`, sắp xếp theo thứ tự tiến hóa từ prototype đến phiên bản chính thức để sử dụng.

---

## 📊 BẢNG TRA CỨU NHANH CÁC PHIÊN BẢN (VERSION PROGRESSION)

| Phiên Bản | Thời Điểm | Tên File PBIX / Thư Mục Dự Án | Chế Độ Dữ Liệu | Ngôn Ngữ | Trạng Thái / Mục Đích Sử Dụng |
| :---: | :---: | :---| :---: | :---: | :---|
| **v1.0** | 15/10/2026 | [`01_archive_prototype_v1/`](01_archive_prototype_v1/)<br>• `Dashboard.pbix` | File CSV tĩnh | Tiếng Anh | 🗄️ **Lưu trữ lịch sử**: Bản nháp thử nghiệm giao diện và web viewer đầu tiên. |
| **v2.0** | 16/10/2026 | [`AnnotationReporter.pbix`](AnnotationReporter.pbix)<br>• [`project/`](project/) | **Import Mode**<br>(14 bảng CSV) | Tiếng Anh | 📐 **Bản đối chiếu baseline**: Bản mã nguồn PBIP chuẩn hóa đầu tiên theo mô hình Kimball Star Schema. |
| **v3.0** | 17/10/2026 | [`AnnotationReporter_Desktop.pbix`](AnnotationReporter_Desktop.pbix)<br>• [`project_desktop/`](project_desktop/) | **Import Mode**<br>(14 bảng CSV) | **Tiếng Việt** | 🛡️ **Bản dự phòng khẩn cấp**: Đã bản địa hóa tiếng Việt toàn bộ biểu đồ; dùng cho máy không chạy được Docker (phải bấm Refresh thủ công). |
| **v4.0** | 18/10/2026 | ⭐ **[`AnnotationReporter_Auto.pbix`](AnnotationReporter_Auto.pbix)**<br>• [`project_auto/`](project_auto/) | **DirectQuery**<br>(PostgreSQL Docker) | **Tiếng Việt** | 🚀 **BẢN CHÍNH THỨC SỬ DỤNG**: Tự động Refresh 10s khi database có dữ liệu mới, không cần bấm Refresh hay Save. |

---

## 🎯 HƯỚNG DẪN CHI TIẾT TỪNG PHIÊN BẢN

### 1. Phiên bản v4.0 — BẢN CHÍNH THỨC (Recommended for Demo & Operation)
* **File khởi động**: [`powerbi/AnnotationReporter_Auto.pbix`](AnnotationReporter_Auto.pbix)
* **Thư mục mã nguồn PBIP**: [`powerbi/project_auto/`](project_auto/)
* **Đặc điểm nổi bật**:
  - Kết nối qua **PostgreSQL DirectQuery** vào container Docker `annotation-reporter-db` (cổng `127.0.0.1:55432`).
  - Cấu hình **Automatic Page Refresh: 10 giây** trên toàn bộ 5 trang.
  - Khi pipeline chạy cập nhật dữ liệu (`START_AUTO.cmd`), số liệu trên visual **tự động thay đổi mà không cần người dùng thao tác bấm nút Refresh hay Save**.
  - PBIX giữ nguyên kích thước dung lượng (~91 KB) vì không lưu data nhị phân trong file.
* **Cách kích hoạt**:
  1. Chạy [`START_AUTO.cmd`](../START_AUTO.cmd) tại thư mục gốc repo.
  2. Mở file `AnnotationReporter_Auto.pbix`.

---

### 2. Phiên bản v3.0 — Bản Dự Phòng Ngoại Tuyến (Offline Desktop Fallback)
* **File khởi động**: [`powerbi/AnnotationReporter_Desktop.pbix`](AnnotationReporter_Desktop.pbix)
* **Thư mục mã nguồn PBIP**: [`powerbi/project_desktop/`](project_desktop/)
* **Đặc điểm nổi bật**:
  - Giao diện 100% Tiếng Việt, font chữ lớn, tối ưu trình chiếu cho buổi họp Mentor.
  - Chạy theo cơ chế **Import Mode** nạp dữ liệu từ các file CSV trong `data/processed/snapshots/...`.
  - Không yêu cầu cài đặt Docker.
  - **Nhược điểm**: Mỗi khi chạy cập nhật dữ liệu, người dùng phải tự bấm nút **Refresh** trên thanh công cụ Power BI Desktop rồi bấm **Save**.
* **Cách kích hoạt**:
  1. Chạy [`START_DEMO.cmd`](../START_DEMO.cmd) tại thư mục gốc repo.
  2. Mở `AnnotationReporter_Desktop.pbix` và bấm **Refresh**.

---

### 3. Phiên bản v2.0 — Bản Đối Chiếu Gốc Tiếng Anh (English Baseline)
* **File khởi động**: [`powerbi/AnnotationReporter.pbix`](AnnotationReporter.pbix)
* **Thư mục mã nguồn PBIP**: [`powerbi/project/`](project/)
* **Đặc điểm nổi bật**:
  - Là bản gốc chuẩn hóa 5 trang, 43 visual, 31 measures được sinh tự động bằng `build_project.py`.
  - Toàn bộ tiêu đề bằng tiếng Anh.
  - Được giữ lại làm bằng chứng kiểm thử tự động cho test suite (`tests/test_powerbi_project.py`).

---

### 4. Phiên bản v1.0 — Lưu Trữ Nguyên Mẫu (Archive Prototypes)
* **Vị trí**: Nằm trong thư mục riêng [`powerbi/01_archive_prototype_v1/`](01_archive_prototype_v1/)
* **Bao gồm**: `Dashboard.pbix`, `Dashboard_Configured.pbix`, `Dashboard_backup.pbix`, web viewer `Dashboard.html`, các file CSV nháp và script sinh dữ liệu cũ.
* Toàn bộ đã được đóng gói gọn gàng để tránh làm rối mắt người dùng khi vào thư mục `powerbi/`.

---

## 🛠️ THƯ MỤC BACKUPS
* Thư mục [`powerbi/backups/`](backups/): Lưu file `AnnotationReporter_Auto_backup.pbix` — bản sao lưu trạng thái PBIX an toàn ngay sau khi bạn đăng nhập xác thực PostgreSQL lần đầu tiên.
