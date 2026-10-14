# CVAT: tham chiếu phần tích hợp đang chạy

[Cài đặt và chạy](README.md) · [Schema output](DATA_CONTRACT.md) · [Việc cần bổ sung](HANDOFF.md)

## Xác thực và phạm vi

Client hiện dùng PAT với `Authorization: Bearer <token>`, không dùng username/password. Token đọc từ `.env`; không lưu header/token vào output. `CVAT_ORG=` chọn workspace cá nhân, slug chọn organization. Tài khoản cần quyền đọc task/job.

## Endpoint đã tích hợp

| GET | Dữ liệu |
|---|---|
| /api/tasks/{id} | Task |
| /api/jobs?task_id=... | Jobs trong task |
| /api/labels?task_id=... | Danh mục labels |
| /api/issues?task_id=... | Issues |
| /api/comments?issue_id=... | Comments từng issue |
| /api/jobs/{id}/annotations/ | Payload annotations theo job |
| /api/jobs/{id} | Xác minh job chưa có trong snapshot |

Danh sách được lấy qua các trang; annotations là một object theo job. Client đặt timeout, retry GET có giới hạn cho 429 và một số lỗi 5xx; không tự biến request lỗi thành danh sách rỗng.

## Link và số liệu

Link job được sinh từ ID đã verified theo mẫu `/tasks/{task_id}/jobs/{job_id}`. Luồng có thể đọc frame từ body GitHub và thêm ?frame, nhưng chưa xác minh frame hợp lệ. Shapes/tracks/tags có raw và thống kê; số bản ghi không phải frame hoàn thành. Save trên CVAT trước khi lấy snapshot.

Đã thử đọc metadata danh sách Quality Reports, chưa tải report/data/conflicts hoặc bảo đảm có điểm hợp lệ. Analytics/events và lịch sử review chưa tích hợp; xem [HANDOFF](HANDOFF.md).

## Đọc lỗi

Xem manifest và annotations.failed_jobs. HTTP 401/403 cần kiểm tra token, quyền và phạm vi; 406 cần kiểm tra định dạng phản hồi được yêu cầu; 429/5xx có thể được retry. Không kết luận nguyên nhân chỉ từ một mã lỗi; giữ endpoint/mã HTTP để đối chiếu.

Nguồn tham chiếu: [PAT](https://docs.cvat.ai/docs/api_sdk/access_tokens/), [Jobs API](https://docs.cvat.ai/docs/api_sdk/sdk/reference/apis/jobs-api/), [Issues API](https://docs.cvat.ai/docs/api_sdk/sdk/reference/apis/issues-api/), [Comments API](https://docs.cvat.ai/docs/api_sdk/sdk/reference/apis/comments-api/).
