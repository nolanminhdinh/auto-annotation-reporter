# Bộ dữ liệu CVAT nhiều jobs — 18/10/2026

## Kết quả thực hiện

Đã tạo project riêng [SYNTHETIC E2E - Urban Mobility QA - 20261018](https://app.cvat.ai/projects/455373).
Toàn bộ ảnh và tình huống là dữ liệu giả lập phục vụ kiểm thử; API và báo cáo chất lượng chạy trên CVAT Cloud thật.

| Nội dung | Đã đọc lại trên server |
|---|---:|
| Tasks | 2 |
| Ảnh | 240, kích thước 960×540 |
| Annotation jobs | 12, mỗi job 20 frames |
| Ground Truth jobs | 2 |
| Nhãn | 6: car, pedestrian, cyclist, truck, traffic_sign, motorbike |
| Annotations trong annotation jobs | 1.080 |
| Annotations chuẩn trong GT jobs | 144, trên 24 frame kiểm định |
| Issues / comments khởi tạo | 12 / 12 |
| Jobs gán tài khoản hiện có | 6 annotation jobs + 2 GT jobs |

- [Batch 1 — Day traffic](https://app.cvat.ai/tasks/2679456).
- [Batch 2 — Night occlusion](https://app.cvat.ai/tasks/2679457).

Mỗi task có sáu tình huống: acceptance/completed, validation/new, validation/in progress,
annotation/rejected, annotation/in progress và annotation/new. Bốn jobs có đủ annotations,
một job mới vẽ một nửa, một job chưa vẽ. Có rectangle/polygon, nhiều kích thước COCO và cờ occluded.
Khung cảnh được dựng bằng hình học đơn giản; không đại diện độ khó thị giác của ảnh nghiệp vụ thực.

## QA tính bởi CVAT

Đã bật requirement rectangle/polygon trên project, nạp GT và yêu cầu tính báo cáo.
Sau đó cài lỗi sai lớp ở frame 0 và lệch hộp ở frame 10 trong job đầu mỗi task.

| Task | Quality report | Frame GT | Conflicts | Accuracy rectangle | Accuracy polygon |
|---|---:|---:|---:|---:|---:|
| 2679456 | 3291060 | 12 | 21 | 0,704918 | 0,75 |
| 2679457 | 3291067 | 12 | 21 | 0,704918 | 0,75 |

Mỗi báo cáo trả 1 mismatching_label, 19 missing_annotation và 1 extra_annotation.
Đây là kết quả CVAT tính, không phải mIoU hay FTPR và không được đổi tên thành các KPI đó.
Các issue mô tả tình huống QA là fixture; không phải mỗi issue đều tương ứng một conflict tự động.

## Kiểm thử luồng

Đã chạy `src/main.py --mode live --demo-source` cho từng task, không bổ sung operations.json giả.
Mỗi lần chạy cuối exit 0, lấy CVAT/GitHub, lưu warehouse, sinh Markdown, notification preview và xuất 14 bảng phục vụ Power BI.
Mỗi báo cáo qua 21 checks (snapshot và 20 KPI Markdown so với warehouse); đây không phải đối chiếu engine DAX.

- Batch 1: `S4d2db0c6030509ec12a1b4af`.
- Batch 2: `Sbd8beaa0cd9bd531bbe7ff7b`.
- Mỗi snapshot có 6 annotation jobs, 540 shapes, 1 annotator; GT job không cộng vào sản lượng annotation.
- Đã đưa Batch 1 vào PostgreSQL local `127.0.0.1:55432`; tài khoản reader xác nhận đúng snapshot và số dòng cả 14 views.
- Chưa quan sát lại visuals Power BI hoặc đối chiếu DAX trong lượt này.
- Chưa chạy lại toàn bộ unit suite; kiểm chứng trên là các lần chạy pipeline thực.

## Giới hạn và phát hiện

1. Tài khoản bị CVAT chặn tạo task thứ ba với HTTP 403: đã đạt maximum number of tasks.
   Đã chuẩn bị local 360 ảnh; chỉ 240 ảnh được tải lên. Không xóa task cũ hoặc nâng gói tài khoản.
2. Sau khi người dùng xác nhận, đã tạo Organization `synthetic-e2e` (35210), tên
   `Synthetic E2E Annotation QA`, chuyển project 455373 vào nhóm và xác nhận `nolanminhdinh`
   là Owner. Đã gửi lời mời Worker cho tài khoản gán nhãn được chỉ định; CVAT trả 201,
   membership 89318 hiện `is_active=false`, lời mời `accepted=false`.
   Lời mời reviewer bị CVAT chặn 403 vì đã đạt giới hạn thành viên của Organization.
   Không nâng gói, không thu hồi lời mời hoặc thay đổi người dùng để vượt giới hạn.
   Ban đầu thao tác phân công bị kiểm duyệt tự động chặn vì lời mời chưa được chấp nhận.
   Sau khi người dùng báo đã chấp nhận, đã đọc lại membership `is_active=true` và phân công
   thành công sáu annotation jobs: 4600308/4600309/4600310 và 4600314/4600315/4600316.
   API đọc lại và giao diện đều hiển thị đúng tài khoản Worker được chỉ định.
   Các job validation/acceptance và GT hiện chưa phân công; chủ nhóm vẫn có quyền quản lý.
   Chưa nghiệm thu đủ ba vai trò hoặc đăng nhập bằng tài khoản Worker để thử quyền truy cập chéo.
   Khi kiểm thử lại nguồn trong nhóm, dùng scope `CVAT_ORG=synthetic-e2e` cho lượt chạy;
   không đổi cấu hình `.env` chung vì task DEMO cũ ở personal workspace.
3. Extractor đã tải được Quality Reports/data (`available`) và issues/comments có nội dung.
   Canonical chưa ánh xạ đầy đủ schema requirements/groups mới sang GT/defect KPI:
   `fact_ground_truth_eval`, `fact_qa_defects`, `fact_qa_reviews` vẫn rỗng.
4. Chưa có lịch sử giờ làm hoặc các vòng review đáng tin cậy; velocity/AHT/FTPR để thiếu dữ liệu.
   Trạng thái job rejected không thay thế lịch sử review.
5. CVAT issues được lưu ở raw; bảng edge cases hiện dựa GitHub, không tự nhận CVAT issues.
   Không tạo GitHub issues mới trong lượt này. Issue GitHub có sẵn thuộc task DEMO cũ;
   việc verifier xác nhận link đó không chứng minh liên kết mới cho hai batch vừa tạo.
6. Pipeline hiện phục vụ từng task/snapshot. Đã kiểm thử hai task riêng, chưa có dashboard tổng hợp đồng thời toàn project.
7. Chưa kiểm thử tải lớn, nhiều tài khoản, quyền truy cập chéo hoặc dữ liệu sản xuất.

## Bằng chứng local

Trong `data/cvat_realistic_seed/` (gitignored): `seed_receipt.json`, `ground_truth_receipt.json`,
`scenario_receipt.json`, `final_remote_verification.json`, `pipeline_receipt.json`,
`directquery_receipt.json`, các raw snapshots và `cvat_project.png`.

Cập nhật nhóm/phân vai: `organization_receipt.json`, `organization_project_move.json`,
`invitation_receipt.json`, `role_assignment_pending.json`, `organization_members.png`.
Thông tin địa chỉ nhận lời mời chỉ lưu trong receipt local được gitignore.

## Kiểm thử sau khi Worker chấp nhận lời mời

- Hai lượt chạy live trong scope Organization đều exit 0, nhận đúng ba jobs Worker mỗi task.
- Batch 1: `Sb99bd2c856f7c27b448c6cd8`; Batch 2: `S8152d5e130eb9fee9429c800`.
- Mỗi lượt qua 21/21 checks đối chiếu Markdown/warehouse; không phải kiểm tra DAX hoặc đăng nhập Worker.
- Batch 1 đã được publish lại vào PostgreSQL local; reader xác nhận đủ 14 views và đúng số dòng.
- Không dùng số liệu vận hành giả để điền các bảng reviews, defects hoặc GT evaluations còn thiếu mapping.
- Bằng chứng: `worker_assignment_receipt.json`, `role_pipeline_receipt.json`,
  `role_pipeline_verification.json`, `worker_jobs_assigned.png` trong thư mục local bên trên.

Hai script chuẩn bị và nạp fixture: `tools/seed_cvat_realistic.py`, `tools/seed_cvat_ground_truth.py`.
Script được giới hạn vào project test trên. Receipt phản ánh dữ liệu ban đầu; các thay đổi cố ý
sau seed nằm trong scenario/final_remote_verification và snapshot pipeline cuối.
