# GitHub: nguồn Issues cho bản nháp mentor

[Cài đặt và chạy](README.md) · [Schema output](DATA_CONTRACT.md) · [Bàn giao](HANDOFF.md)

## Phạm vi đã tích hợp

| GET /repos/{owner}/{repo}/... | Output |
|---|---|
| issues?state=all | Issues mở/đóng; loại PR |
| labels | Labels trong repo |
| issues/{number}/comments | Comments từng issue |

Repo public đọc được không cần token; private cần token có quyền đọc repo/issues. Client theo pagination Link để lấy đủ danh sách. Luồng chưa tạo/sửa issue, tự mở PR, gửi thông báo hoặc lấy commits.

## Chọn dữ liệu vào báo cáo

| Điều kiện | Kết quả |
|---|---|
| open + ca-kho | Ca khó |
| open + mentor-question | Câu hỏi mở |
| Có cả hai labels | Cả hai mục |
| title bắt đầu [API test] hoặc label api-test | Loại khỏi bản nháp |
| Tham chiếu task khác khi đọc được ID | Loại khỏi bản nháp |
| closed | Giữ raw, không đưa vào mục mở |

blocker/guideline-update được gom thành hai nhóm bổ sung trong JSON chuẩn hóa. Script lấy toàn bộ issues rồi lọc local, không dùng query nhiều labels dễ nhầm điều kiện AND/OR.

## Tham chiếu CVAT

```text
CVAT task ID: 2592622
CVAT job ID: 4475446
```

Mỗi loại ID là số nguyên dương, xuất hiện một lần. Verified chỉ xác minh job thuộc task. Câu hỏi chung có thể không có ID và được giữ kèm cảnh báo. Đã đọc frame nếu có và thêm vào link; chưa xác minh phạm vi frame/object, chưa tổng hợp comments vào description.

Mẫu nhập và hướng dẫn triển khai nằm ở [tracker-repo](../../tracker-repo/README.md). Issue title/labels không tự trở thành điểm chấm hoặc kết quả review; closed_at không phải ngày nộp job.

Workflow trong tài liệu DevOps là thiết kế, chưa tích hợp luồng CLI hiện tại. Nguồn tham chiếu: [Issues API](https://docs.github.com/en/rest/issues/issues), [Pagination](https://docs.github.com/en/rest/using-the-rest-api/using-pagination-in-the-rest-api).
