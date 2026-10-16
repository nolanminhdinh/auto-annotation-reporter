> Hồ sơ ngày 09/10/2026; không thay thế [hướng dẫn hiện tại](../README.md) và [schema](../DATA_CONTRACT.md).

# Báo cáo triển khai bước đầu: tích hợp API CVAT và GitHub

**Ngày báo cáo:** 09/10/2026 (giờ Việt Nam, UTC+7)<br>
**Phạm vi:** thu thập dữ liệu nguồn và kiểm tra liên kết giữa GitHub Issue với CVAT Task/Job.<br>
**Trạng thái:** đã chạy thành công trên CVAT Cloud và repo GitHub thử nghiệm.

## 1. Mục tiêu và bối cảnh

Project auto-annotation-reporter ban đầu chủ yếu có khung tài liệu, cấu hình mẫu
và định hướng báo cáo tiến độ/chất lượng gán nhãn. Nhóm chưa thống nhất nghiệp vụ
QA/QC, các chỉ số cần tính hoặc hình thức bàn giao cuối cùng.

Công việc trong đợt này là xây dựng bước thu thập dữ liệu có thể chạy thực tế:
đọc API CVAT, đọc API GitHub, kiểm tra tham chiếu task/job và lưu dữ liệu JSON
để nhóm có cơ sở thảo luận và phát triển phần xử lý tiếp theo.

## 2. Môi trường và dữ liệu thử

| Hạng mục | Thông tin đã xác nhận |
|---|---|
| Nền tảng gán nhãn | CVAT Cloud: https://app.cvat.ai |
| Workspace | Cá nhân, cấu hình `CVAT_ORG=` |
| Task | `2592622`, tên `clip_01`, 190 frame |
| Job | `4475446`, thuộc task `2592622` |
| Trạng thái job ở lần đọc thử | stage: `annotation`; state: `in progress`; chưa có assignee |
| Repo theo dõi | https://github.com/DuyWebdev/annotation-qa-tracker (public) |
| Issue thử | https://github.com/DuyWebdev/annotation-qa-tracker/issues/1 |

Repo tracker dùng để thử theo dõi các vấn đề liên quan gán nhãn bằng Issues.
Code tích hợp nằm trong project auto-annotation-reporter hiện tại.
Issue #1 là **issue thử API**, không phải lỗi annotation đã được QA/QC ghi nhận.

## 3. Công việc đã hoàn thành

1. Thiết lập môi trường Python `.venv` và dependencies tối thiểu cho ingestion.
2. Cấu hình CVAT Cloud trong `.env`, dùng Personal Access Token với Bearer authentication.
3. Gọi API đọc task và danh sách jobs; xác nhận dữ liệu trả về HTTP 200.
4. Lấy thông tin task, jobs, labels, issues và comments từ CVAT.
5. Đọc issues, labels và comments từ repo GitHub public, không cần GitHub token
   cho lần chạy thử này; loại bỏ PR khỏi kết quả issues.
6. Ghi task/job ID vào nội dung GitHub issue và tách các ID bằng chương trình.
7. Đối chiếu task ID ghi trong issue với task ID thực tế của job từ API CVAT.
8. Ghép việc thu thập hai nguồn và xác minh liên kết vào một lệnh chạy.
9. Lưu dữ liệu nguồn, kết quả liên kết và manifest theo từng lần chạy.

Đã xử lý lỗi cấu hình token mẫu và điều chỉnh header `Accept` của client sau
khi script gặp HTTP 406. Sau điều chỉnh, lần chạy thực tế lấy dữ liệu thành công.
Client có timeout, retry giới hạn cho GET và xử lý phân trang.

## 4. Luồng hoạt động hiện tại

```text
.env: cấu hình task/repo và token local
                 |
             src/sync.py
                 |
       +---------+---------+
       |                   |
   CVAT API            GitHub API
   task/jobs/          issues/labels/
   labels/issues/      comments
   comments                |
       |             đọc task/job ID
       +---------+---------+
                 |
      kiểm tra job thuộc task đã ghi
                 |
    lưu JSON + kết quả liên kết + manifest
```

Đây là luồng đọc dữ liệu từ hai hệ thống vào project local. Chương trình chưa
tạo issue, sửa annotation, thay đổi job hoặc đồng bộ hai chiều.

## 5. API đang sử dụng

| Nguồn | Endpoint GET | Mục đích |
|---|---|---|
| CVAT | `/api/tasks/{task_id}` | Đọc thông tin task |
| CVAT | `/api/jobs?task_id=...` | Lấy jobs thuộc task |
| CVAT | `/api/labels?task_id=...` | Lấy nhãn của task |
| CVAT | `/api/issues?task_id=...` | Lấy issues trên CVAT |
| CVAT | `/api/comments?issue_id=...` | Lấy comments cho từng issue |
| CVAT | `/api/jobs/{job_id}` | Kiểm tra job chưa có trong dữ liệu đã lấy |
| GitHub | `/repos/{owner}/{repo}/issues?state=all` | Lấy cả issues mở và đóng |
| GitHub | `/repos/{owner}/{repo}/labels` | Lấy labels trong repo |
| GitHub | `/repos/{owner}/{repo}/issues/{number}/comments` | Lấy comments cho từng issue |

Trong các bước học ban đầu, đã gọi thêm API đọc một GitHub issue cụ thể.
Script tổng hợp hiện lấy danh sách issues rồi sử dụng body đã nhận được.

## 6. Các file triển khai và cách chạy

| File | Vai trò |
|---|---|
| `src/collect.py` | Client và hàm thu thập dữ liệu; hỗ trợ chạy riêng từng nguồn |
| `src/verify_link.py` | Xác minh liên kết của một GitHub issue |
| `src/sync.py` | Thu thập hai nguồn và kiểm tra liên kết trong một lần chạy |
| `requirements-ingestion.txt` | Dependencies tối thiểu: requests, python-dotenv |
| `.env.example` | Cấu hình mẫu, không chứa token thật |
| `tests/test_collect.py` | Kiểm tra phân trang, loại PR, lỗi HTTP và bảo vệ token |
| `tests/test_verify_link.py` | Kiểm tra tách ID và quan hệ sai task |
| `tests/test_sync.py` | Kiểm tra phân loại liên kết và job không truy cập được |
| `docs/03-integrations/INGESTION_STARTER.md` | Hướng dẫn thiết lập và hợp đồng dữ liệu ban đầu |

Chạy tại thư mục gốc project, sau khi thiết lập `.env`:

```powershell
.\.venv\Scripts\python.exe src/sync.py
```

Hoặc chỉ định phạm vi rõ ràng:

```powershell
.\.venv\Scripts\python.exe src/sync.py --task-id 2592622 --repo DuyWebdev/annotation-qa-tracker
```

Token CVAT lưu trong `.env` local. Repo public có thể đọc không cần token GitHub;
repo private cần token có quyền đọc. `.env` và `data/raw/` đã được gitignore.
Tên `sync.py` hiện chỉ biểu thị việc gom dữ liệu, không có thao tác ghi ngược lên nguồn.

## 7. Kết quả chạy thực tế

**Lần chạy được đối chiếu:** 09/10/2026, khoảng 11:55:06–11:55:11 giờ Việt Nam.<br>
**Thư mục:** `data/raw/20261009T045506941752Z/` (tên thư mục dùng UTC).

| Nguồn | Trạng thái | Số bản ghi |
|---|---|---|
| CVAT | success | 1 task, 1 job, 1 label, 0 issues, 0 comments |
| GitHub | success | 1 issue, 10 labels, 0 comments |
| Liên kết | verified | 1 liên kết đúng; 0 mismatch; 0 unlinked; 0 invalid_reference; 0 verification_failed |

Kết quả terminal:

```text
cvat: success
github: success
Links: {'verified': 1, 'mismatch': 0, 'unlinked': 0, 'invalid_reference': 0, 'verification_failed': 0}
Saved: data\raw\20261009T045506941752Z
```

CVAT xác nhận job `4475446` thuộc task `2592622`, khớp nội dung GitHub issue #1.
Số CVAT issues/comments bằng 0 nghĩa là API không trả bản ghi trong phạm vi lần
lấy này; không đủ để kết luận task không có lỗi annotation.
10 GitHub labels là tổng nhãn đã lấy trong repo, không phải 10 loại lỗi đã chốt.

## 8. Dữ liệu bàn giao

| File đầu ra | Nội dung | Cách sử dụng |
|---|---|---|
| `cvat.json` | Task object và các arrays jobs/labels/issues/comments | Tra cứu dữ liệu nguồn CVAT |
| `github.json` | Arrays issues/labels/comments | Tra cứu nội dung và trạng thái issues |
| `links.json` | Tham chiếu CVAT trong từng issue và trạng thái kiểm tra | Đối chiếu issue với task/job |
| `manifest.json` | Phạm vi, thời điểm, trạng thái nguồn và counts | Kiểm tra lần lấy có thành công/đủ nguồn không |

Các object nguồn giữ nguyên trường API; chưa phải mô hình dữ liệu QA/QC chuẩn hóa.
Phân loại liên kết:

| Status | Ý nghĩa |
|---|---|
| `verified` | Job thuộc đúng task được ghi trong issue |
| `mismatch` | Job thuộc task khác |
| `unlinked` | Issue không có dòng tham chiếu theo mẫu đang dùng |
| `invalid_reference` | Thiếu, trùng hoặc sai định dạng task/job ID |
| `verification_failed` | Không thể xác minh qua API hoặc phản hồi thiếu trường cần thiết |

`verified` chỉ xác minh quan hệ task/job, không xác nhận annotation đạt chất lượng,
frame đúng, issue là defect hay được reviewer chấp thuận.

## 9. Kiểm thử và giới hạn hiện tại

9 automated tests đã pass. Các test bao phủ phân trang CVAT/GitHub, loại PR,
không coi lỗi HTTP là danh sách rỗng, không gửi token sang host khác theo pagination,
tách ID với xuống dòng Windows, từ chối ID trùng, phát hiện task không khớp,
giữ issue không có liên kết và phân biệt không truy cập được job với sai liên kết.

Lần chạy API thật chứng minh luồng hoạt động trên task và repo thử đã nêu.
Dữ liệu thật hiện nhỏ, chưa kiểm chứng tải lớn hoặc phân trang nhiều trang bằng
tài khoản cloud thực tế; phần phân trang đã được kiểm tra bằng mock.

Chưa triển khai: ảnh/annotation đầy đủ, Quality Reports/Ground Truth, PRs/commits,
lịch sử chuyển trạng thái, xác minh frame/object, tính chỉ số QA/QC, Power BI,
chạy theo lịch và đồng bộ hai chiều. Snapshot gồm nhiều request liên tiếp,
không bảo đảm mọi bản ghi thuộc cùng một thời điểm nếu nguồn đang bị chỉnh sửa.

## 10. Nội dung cần nhóm thống nhất trước khi mở rộng

- QA/QC sẽ sử dụng dữ liệu để kiểm tra annotation hay kiểm thử phần mềm?
- Phạm vi task/project/repo chính thức và tần suất cập nhật là gì?
- Kết quả review, pass/reject và loại lỗi sẽ được ghi ở đâu, theo quy tắc nào?
- Có dùng Ground Truth và cần lấy Quality Reports hay không?
- Quy ước liên kết issue với task/job/frame, và thông tin được phép ghi trên repo public?
- Bên nhận muốn raw JSON, bảng chuẩn hóa, CSV hay database?

**Kết luận:** đã có bản tích hợp API đầu tiên hoạt động và chạy lại bằng một lệnh.
Đầu ra hiện đủ để minh họa việc lấy dữ liệu và liên kết hai nguồn; chưa thể dùng
để tính hoặc kết luận chỉ số QA/QC khi nghiệp vụ chưa được thống nhất.
