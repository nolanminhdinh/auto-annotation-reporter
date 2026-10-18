# 📦 Lưu Trữ Phiên Bản 1 (v1.0 - Prototype Ban Đầu 15/10/2026)

Thư mục này lưu trữ toàn bộ các file thử nghiệm nháp và mã nguồn nguyên mẫu (prototype) ban đầu của dự án gán nhãn:

## Các thành phần lưu trữ:
1. **Các file Power BI nguyên mẫu**:
   - `Dashboard.pbix`: File Power BI thử nghiệm đầu tiên dựng giao diện biểu đồ.
   - `Dashboard_Configured.pbix`: File PBIX đã qua thử nghiệm cấu hình trang.
   - `Dashboard_backup.pbix`: File sao lưu phòng rủi ro trước khi can thiệp mã nhị phân.
2. **Giao diện HTML độc lập**:
   - `Dashboard.html` & `index.html`: Giao diện web tĩnh mở nhanh biểu đồ bằng trình duyệt (sử dụng thư viện Chart.js).
3. **Mã nguồn sinh dữ liệu và cấu hình cũ**:
   - `generate_powerbi_data.py`: Script sinh 16 file CSV mẫu ban đầu.
   - `configure_pbix_pages.py`: Script thử nghiệm sửa JSON trang trong PBIX.
   - `powerbi_direct_db_connector.py`: Script thử nghiệm kết nối database trực tiếp ban đầu.
   - `sqliteodbc_w64.exe`: Trình cài đặt driver SQLite ODBC cho Windows 64-bit.
   - `data/`: 16 file CSV dữ liệu mẫu tĩnh ban đầu.

---
> ⚠️ **Lưu ý**: Các file trong thư mục này chỉ mang tính chất lưu trữ lịch sử phát triển. Không sử dụng cho buổi demo chính thức. Hãy sử dụng file chính thức tại thư mục cha: [`powerbi/AnnotationReporter_Auto.pbix`](../AnnotationReporter_Auto.pbix).
