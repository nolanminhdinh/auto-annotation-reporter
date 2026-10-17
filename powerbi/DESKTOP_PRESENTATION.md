# Hướng dẫn trình bày báo cáo Desktop

## Trước khi mở

1. Từ gốc repo chạy `.\powerbi\RUN_DEMO.ps1` để tạo dữ liệu giả lập mới.
2. Mở bản giao diện tiếng Việt: `project_desktop/AnnotationReporter.pbip`; chọn Refresh.
3. Khi đã nạp xong, thu gọn Filters, Visualizations, Data để dành chỗ cho biểu đồ.
4. Nhãn DEMO phải hiện; các link example.org chỉ minh họa. Đơn vị frames là số frame thuộc job completed, chưa khẳng định đã qua QA.

## Trình bày trong khoảng 5 phút

| Trang | Nội dung cần giải thích | Tương tác |
|---|---|---|
| 01 Tổng quan | 1.000/1.500 frames, 66,7% tiến độ, 26,7 frames/giờ, FTPR 60%. Dòng dưới cho biết độ đầy đủ nguồn dữ liệu. | Chọn một người để xem KPI thay đổi; xóa chọn để trở về toàn nhóm. |
| 02 Chất lượng | Rejection tính trên mọi lượt review; FTPR chỉ tính lượt đầu. mIoU/F1 dùng đánh giá mới nhất mỗi job. | Chọn loại lỗi hoặc lớp đối tượng để xem phần liên quan. |
| 03 Nhân sự | Đối chiếu vận tốc và FTPR; phân khúc là quy tắc minh họa từ dữ liệu đang lọc. | Chọn một điểm hoặc người trong bảng. Không đánh giá năng lực thật từ fixture. |
| 04 Hình học | Bản ghi hình vẽ không nội suy track; diện tích theo px² và % frame. Phân loại Small theo ngưỡng COCO. | Chọn lớp hoặc nhóm kích thước. |
| 05 Ca khó | 4 ca mở, 1 blocker. Chọn đúng một dòng để đọc mô tả bên dưới. | Bấm lại dòng đang chọn để bỏ chọn; URL DEMO không mở frame thật. |

## Cách đọc dữ liệu thiếu

- KPI trống/BLANK: chưa đủ nguồn hoặc không có mẫu số trong bộ lọc.
- Giá trị 0: có dữ liệu để tính và kết quả là 0; ví dụ FTPR của người có mọi lượt đầu bị từ chối.
- Vận tốc cần đủ giờ làm cho mọi job đang lọc. Không loại job thiếu giờ khỏi mẫu số để tăng vận tốc.
- Trang tổng quan giữ mục tiêu của task làm mẫu số khi lọc người: tiến độ khi đó là đóng góp của người vào mục tiêu task.
- Các trang phân tích dùng các fact khác nhau; chọn lớp không mặc định lọc được giờ làm hoặc review không có nhãn lớp. Chọn người/task là bộ lọc dùng chung trong từng trang; chưa đồng bộ slicer giữa các trang.

## Khi ghép với nguồn thật

Giữ tên bảng/cột canonical và quan hệ model. Chạy pipeline nguồn thật, kiểm tra publication.json, rồi Refresh trong Desktop. Không sửa trực tiếp số KPI trên visual. Ghi rõ các KPI thiếu, thời điểm snapshot và phạm vi nguồn đã xác nhận.
