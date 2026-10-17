# Kịch bản dữ liệu giả lập cho Power BI Desktop

Đích hiện tại: hoàn thiện báo cáo trên máy local bằng dữ liệu tổng hợp. Không cần CVAT_TOKEN, máy chủ CVAT của nhóm hoặc gọi API ngoài.

## Bộ dữ liệu

- Task 700: 1.500 frames, 15 annotation jobs có phạm vi frame riêng biệt.
- 5 người giả lập gắn nhãn demo: Minh, Tú, Duy, Tuân, Ngọc. Các chỉ số không phản ánh năng lực hoặc công việc thực tế của thành viên.
- 10 jobs hoàn thành, 5 jobs đang làm; 285 hình chữ nhật thuộc 4 lớp: car, motorbike, pedestrian, truck.
- Metadata kích thước 1.920 × 1.080 cho từng frame; geometry đọc từ snapshot, không cần nhập kích thước thủ công.
- 37,5 giờ làm; 14 lượt review, 4 defects, 10 kết quả GT tổng hợp.
- 4 ca khó/câu hỏi mở, có 1 blocker; 3 phản ánh nhóm cho bản thảo Mentor.
- Link example.org là link minh họa, không mở được ảnh/frame CVAT thật.

## Chạy và trình bày

```powershell
.\powerbi\RUN_DEMO.ps1
```

Mở powerbi/AnnotationReporter_Desktop.pbix trong Desktop, chọn Refresh rồi Save. Nhãn DEMO / DỮ LIỆU GIẢ LẬP phải hiển thị. Xem thêm DESKTOP_PRESENTATION.md để trình bày cả 5 trang.

1. Executive: 1.000 frames hoàn thành theo trạng thái job / 1.500 mục tiêu, tiến độ 66,67%, vận tốc 26,67 frames/giờ.
2. QA: FTPR 60%, rejection 28,57%, mIoU 0,878, F1 0,896; lượt review lại đã được tính vào rejection denominator.
3. Annotator: chọn từng người để xem sản lượng, tốc độ và phân khúc; mọi số liệu là tình huống giả lập.
4. Geometry: xem phân bố lớp và kích thước object từ tọa độ hình vẽ.
5. Edge Cases: chọn dòng để đọc mô tả; bỏ chọn để quay lại 4 ca mở / 1 blocker.

Đầu ra mỗi lần chạy nằm trong data/runs/<timestamp>: raw JSON, publication.json, MENTOR_REPORT_DRAFT.md, team_summary.json và notification_preview.txt. Không gửi Telegram/Discord hoặc gọi Gemini khi chạy script demo.

Khi ghép với phần tích hợp của nhóm, giữ nguyên hợp đồng CSV/Power Query; chỉ thay snapshot đầu vào bằng nguồn thật và bổ sung operations.json đã xác nhận. Không dùng fixture này làm số liệu nghiệm thu thực tế.
