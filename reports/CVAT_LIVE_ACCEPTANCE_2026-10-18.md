# Nghiệm thu live module CVAT — 18/10/2026

## Kết luận

**Đạt phần ingestion chính, có giới hạn (`passed_with_limitations`).** PAT trong .env đã xác thực được với CVAT Cloud. Bộ ảnh và annotations là dữ liệu giả lập do người dùng cho phép tạo; các request nghiệm thu được gửi tới dịch vụ thật bằng extractor của dự án.

- Task: [2679097 — DEMO - API live acceptance](https://app.cvat.ai/tasks/2679097).
- Job: [4599943](https://app.cvat.ai/tasks/2679097/jobs/4599943).
- Lần đọc sau Save: 18/10/2026, khoảng 15:18 UTC+7.
- Bằng chứng tổng hợp: `CVAT_LIVE_ACCEPTANCE_2026-10-18.json` cùng thư mục.
- Raw và receipt đầy đủ: `data/live_acceptance/cvat/20261018T081815375167Z/`, được gitignore vì raw có metadata tài khoản.

## Kết quả đối chiếu

| Nhóm | Kết quả |
|---|---|
| PAT Bearer | Đọc task và tài nguyên bằng PAT thành công; giao diện hiển thị quyền Read Only |
| Task | Đúng ID, đúng tên DEMO, size=3 |
| Jobs | 1 annotation job, frame_count=3; stage=annotation, state=new tại thời điểm lấy |
| Labels | 1 nhãn vehicle |
| Annotations trước khi vẽ | API trả thành công, 0 shapes/tracks/tags |
| Annotations sau khi vẽ và Save | API trả đúng 3 rectangle shapes, frame 0/1/2, mỗi frame một shape vehicle |
| Tọa độ | Hộp có diện tích dương, nằm trong ảnh; API lưu tọa độ có phần thập phân từ thao tác UI |
| Media metadata | 3 ảnh 640×360, đúng tên demo_frame_000/001/002.png |
| Issues | GET thành công, danh sách rỗng |
| Comments | Chưa gọi endpoint comments vì không có issue; chưa nghiệm thu trường hợp có dữ liệu |
| Quality list | Cả target=task và target=job đều thành công, mỗi danh sách có 0 reports |
| Quality report data | Chưa gọi vì không có report ID; không coi đó là lỗi 403 hoặc 0 điểm QA |

Sau khi lưu annotations trong giao diện, đã đọc lại bằng PAT để xác nhận dữ liệu được lưu trên server. Chưa chuyển trạng thái job sang completed; vẽ đủ ba hình không được coi là đã QA pass hoặc hoàn thành workflow.

## Lệnh chạy lại

```powershell
.\.venv\Scripts\python.exe -X utf8 -B tools/accept_cvat_live.py --task-id 2679097 --expected-frames 3 --expected-shapes 3
```

Tool chỉ GET và ghi bằng chứng local, không sửa CVAT, không publish warehouse hoặc Power BI. Mã thoát 0=đạt, 2=đạt có giới hạn, 1=thất bại. Đọc status và checks trong acceptance.json để phân biệt thiếu Quality Reports với lỗi lấy dữ liệu.

Đã cập nhật CVAT_TASK_ID trong .env sang task DEMO được nghiệm thu. Không đổi launcher từ demo sang live. PAT không ghi vào kết quả, Git hoặc log.

## Chưa nằm trong nghiệm thu này

- Pagination nhiều trang trên dataset lớn; retry thực tế khi server trả 429/5xx.
- Issues/comments có nội dung, report data có GT và mapping KPI QA.
- Analytics/giờ làm thực, historical reviews, consensus/overlap, track interpolation.
- Luồng GitHub → warehouse → PostgreSQL → Power BI với nguồn Cloud này.

Kết quả này xác nhận extractor hoạt động với task DEMO trên CVAT Cloud đang dùng. Không thay thế nghiệm thu dữ liệu nghiệp vụ thực hoặc toàn bộ end-to-end.
