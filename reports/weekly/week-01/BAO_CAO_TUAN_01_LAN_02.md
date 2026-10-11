# 📊 BÁO CÁO TIẾN ĐỘ TUẦN 1 — LẦN 2 (WEEK 1 PROGRESS REPORT - SESSION 2)

> **Dự án**: Auto Annotation Report Pipeline (CVAT & GitHub Sync - Power BI Hybrid)  
> **Giai đoạn**: Tuần 1 — Khảo sát Nghiệp vụ, Kiến trúc Hệ thống & Tích hợp Prototype Ingestion  
> **Phiên báo cáo**: Phiên 2 — Tối Chủ Nhật (11/10/2026)  
> **Người lập báo cáo**: Đinh Công Minh (Project Lead & BI Architect)  
> **Ngày phê duyệt**: 11/10/2026  

---

## 📌 I. CÔNG VIỆC ĐÃ HOÀN THÀNH (COMPLETED TASKS)

Trong giai đoạn nửa cuối Tuần 1 (từ Thứ Sáu đến Chủ Nhật), sau phiên báo cáo Lần 1 (Tối Thứ Năm), toàn đội đã tập trung nghiệm thu, kiểm thử chéo và tích hợp thành công module **Data Ingestion & Verification Pipeline** vào nhánh chính (`main`) của repository:

### 1. Về mặt Quản lý Dự án & Nghiệm thu Kỹ thuật (Đinh Công Minh)
* ✅ **Review & Nghiệm thu chéo mã nguồn của Vũ Trường Duy**:
  * Đánh giá toàn diện repository prototype [`DuyWebdev/mentor-report-integration-demo`](https://github.com/DuyWebdev/mentor-report-integration-demo).
  * Ban hành biên bản nghiệm thu kỹ thuật chính thức: [`reports/NGHIEM_THU_VA_TICH_HOP_API_INGESTION.md`](../NGHIEM_THU_VA_TICH_HOP_API_INGESTION.md).
* ✅ **Trực tiếp Tái cấu trúc & Hợp nhất Kiến trúc (Architecture Consolidation)**:
  * Quy hoạch cấu trúc thư mục quy chuẩn `src/` gồm 3 tầng rõ ràng:
    * `src/extractors/`: Thu thập API đa nguồn (CVAT & GitHub).
    * `src/processors/`: Chuẩn hóa dữ liệu theo Data Contract v1 (`report_data.json`).
    * `src/generators/`: Động cơ kết xuất báo cáo Markdown 4 mục (`MENTOR_REPORT_DRAFT.md`).
  * Nâng cấp logic Deep Link lên cấp Frame (`?frame={idx}`), thỏa mãn 100% tiêu chí đặc tả trong `CVAT_INTEGRATION_GUIDE.md`.
  * Viết bộ kiểm thử tự động **17 Unit Tests** với tỷ lệ pass **100%**.

### 2. Về mặt Tích hợp Dữ liệu & API (Nguyễn Minh Tú & Vũ Trường Duy)
* ✅ **Xây dựng Base HTTP Client hoàn chỉnh (`src/extractors/base_client.py`)**:
  * Tích hợp cơ chế tự động thử lại (Retry) với exponential backoff trên các lỗi HTTP 429/500/502/503/504.
  * Tự động duyệt phân trang an toàn, ngăn chặn vòng lặp URL vô tận (Safe pagination traversal).
  * Bảo mật thông tin token và bảo vệ chống tấn công SSRF / Open Redirect.
* ✅ **Hoàn thiện CVAT Extractor (`src/extractors/cvat_extractor.py`)**:
  * Trích xuất đầy đủ thông tin Task, danh sách Jobs, Class Labels, Issues và Comments.
  * Trích xuất dữ liệu Annotations thô theo từng job và hàm tính toán tóm lược (Shapes, Tracks, Tags).
  * Khảo sát và tích hợp kết nối tới endpoint Quality Reports của CVAT.
* ✅ **Hoàn thiện GitHub Extractor (`src/extractors/github_extractor.py`)**:
  * Trích xuất danh sách Issues có gắn các nhãn `ca-kho`, `mentor-question`, `blocker`, `guideline-update`.
  * Thuật toán đối soát chéo liên kết Task/Job, phân loại chi tiết 5 trạng thái liên kết (`verified`, `mismatch`, `unlinked`, `invalid_reference`, `verification_failed`).

### 3. Về mặt Xử lý Dữ liệu & ETL (Phạm Nguyễn Tuân)
* ✅ **Xây dựng Data Normalizer (`src/processors/normalizer.py`)**:
  * Chuẩn hóa dữ liệu đa nguồn thành `report_data.json` theo đúng chuẩn Data Contract v1.
  * Tự động loại bỏ các issue thử nghiệm (`[API test]`) và các issue trỏ nhầm sang task khác.
* ✅ **Hoàn thiện Markdown Generator (`src/generators/markdown_generator.py`)**:
  * Tự động sinh bản thảo báo cáo chuẩn 4 phần `MENTOR_REPORT_DRAFT.md`.
  * Tự động chuyển đổi múi giờ sang giờ Việt Nam (UTC+7).
* ✅ **Xây dựng Adapter đọc snapshot CVAT thực tế (`metrics-etl-processors/src/adapters/cvat_snapshot.py`)**:
  * Đọc file `cvat.json` từ snapshot do Duy thu thập, ánh xạ sang dataclass chuẩn hóa `Job`, `Annotator`, `ShapeGeometry`.
  * Xử lý đúng các đối tượng "đã vẽ": shape đơn và keyframe không `outside` của track, không nội suy.
* ✅ **Xây dựng Runner tổng hợp chỉ số (`metrics-etl-processors/src/adapters/snapshot_metrics.py`)**:
  * Tích hợp luồng tính toán đầy đủ: gọi các module velocity, quality, geometry, segmentation và xuất kết quả JSON tổng hợp.
  * Hỗ trợ cờ `--frame-size` và `--as-of` để chạy offline không cần kết nối CVAT.
  * Cơ chế `not_computable`: chỉ số thiếu nguồn được ghi rõ lý do, không thay bằng số 0 giả.
* ✅ **Hoàn thiện tài liệu kỹ thuật tầng processors (`metrics-etl-processors/src/processors/README.md`)**:
  * Đặc tả đầy đủ 20 Measures DAX và ánh xạ sang hàm Python tương ứng.
  * Ghi rõ 8 giả định nghiệp vụ cần Lead phê duyệt trước khi code (ngưỡng idle, cửa sổ ETA, v.v.).

### 4. Về mặt Tự động hóa & DevOps (Ngô Duy Ngọc)
* ✅ **Triển khai GitHub Issue Templates**:
  * Tạo 2 templates `.github/ISSUE_TEMPLATE/edge-case.yml` và `mentor-question.yml` để chuẩn hóa dữ liệu đầu vào từ đội ngũ annotators.
* ✅ **Chuẩn hóa script điều phối (`src/sync.py`)**:
  * Hỗ trợ chạy cả 2 chế độ: Online Live Sync và Offline Snapshot Replay.

---

## ⚠️ II. CÔNG VIỆC CHƯA HOÀN THÀNH & NGUYÊN NHÂN (PENDING TASKS & ROOT CAUSE)

| Công Việc Chưa Hoàn Thành | Mức Độ | Người Phụ Trách | Nguyên Nhân Gốc Rễ (Root Cause) | Giải Pháp Khắc Phục (Action Plan) |
| :--- | :---: | :---: | :--- | :--- |
| **1. Viết các module tính toán chỉ số (`velocity.py`, `quality.py`, `geometry.py`, `segmentation.py`, `models.py`, `config.py`)** | Cao | Phạm Nguyễn Tuân | Tuần 1 tập trung hoàn thiện tầng Adapter và tài liệu đặc tả kỹ thuật (README). Kiến trúc và công thức đã được thiết kế xong; chưa có file code `.py` thực thi. Runner `snapshot_metrics.py` đã import sẵn các module này nhưng chúng chưa tồn tại. | Tuân viết đủ 7 file module theo đúng công thức đặc tả trong `README.md` vào **đầu Tuần 2**. Ưu tiên thứ tự: `models.py` → `config.py` → `velocity.py` → `quality.py` → `geometry.py` → `segmentation.py` → `annotator_stats.py`. |
| **2. Xuất bộ 4 file CSV cho Power BI** | Cao | Phạm Nguyễn Tuân | Chưa có Exporter CSV (WBS 2.5); phụ thuộc trực tiếp vào việc các module tính toán (WBS 2.1–2.4) phải hoàn thành trước. | Sau khi processors xong, Tuân viết exporter xuất `batch_progress.csv`, `qa_metrics.csv`, `annotator_segments.csv`, `edge_cases.csv` vào `data/processed/` với encoding `utf-8-sig` để Power BI đọc đúng tiếng Việt. |
| **3. Tính toán điểm QA tự động từ Ground Truth API** | Thấp | Vũ Trường Duy & Đinh Công Minh | Instance CVAT thử nghiệm của nhóm chưa gắn sẵn Job Ground Truth mẫu, dẫn đến endpoint `/api/quality/reports` trả về rỗng. | Duy trì cơ chế trả về `scores.status = "unavailable"` kèm lý do rõ ràng. Tú & Duy tạo 1 Ground Truth Job mẫu (~50 frames) trên CVAT trong Tuần 2. |
| **4. Tích hợp tự động Git Commit trong GitHub Actions** | Vừa | Ngô Duy Ngọc | Workflow gặp lỗi quyền ghi (`403 Permission Denied`) khi tự động commit CSV mới sinh ra ngược trở lại repo. | Cấp quyền `permissions: contents: write` trong `scheduled_report.yml` và dùng `GITHUB_TOKEN` có quyền ghi. Ngọc cập nhật và test lại trong Tuần 2. |

---

## 💡 III. CÁC ĐIỂM CẢI TIẾN TRONG SẢN PHẨM (PRODUCT IMPROVEMENTS)

Trong đợt nghiệm thu và tích hợp cuối Tuần 1, nhóm đã bổ sung **2 cải tiến kỹ thuật quan trọng**:

### 🌟 CẢI TIẾN 1: Tự động Bóc tách Frame Index & Sinh Deep Link Frame-Level
* **Nội dung cải tiến**:
  * Thay vì chỉ mở chung chung vào trang chính của Job, hệ thống tự động bóc tách chỉ số Frame từ nội dung mô tả của issue trên GitHub (ví dụ: `Frame index (nếu có): 142`, `Frame: 142`, `Khung hình: 142`).
  * Đường dẫn Deep Link được tạo tự động dưới dạng:
    $$\text{URL} = \text{CVAT\_HOST} + \text{/tasks/\{task\_id\}/jobs/\{job\_id\}?frame=\{frame\_idx\}}$$
* **Lý do & Căn cứ nghiệp vụ**:
  * *Căn cứ thực tế*: Trong các job có hàng trăm hoặc hàng nghìn frames, nếu liên kết chỉ trỏ đến Job, Mentor và Leader phải mất nhiều phút dò tìm thủ công khung hình gây tranh chấp.
  * *Căn cứ kỹ thuật*: CVAT Web Frontend hỗ trợ trực tiếp query parameter `?frame={index}` để tua thẳng tới vị trí frame. Bằng cách hiển thị `🎯 [🔗 Mở trực tiếp Frame 142 trên CVAT]`, thời gian tra cứu được rút ngắn xuống chỉ còn 1 cú click chuột.

---

### 🌟 CẢI TIẾN 2: Cơ chế Snapshot Bất biến & Hỗ trợ Replay Offline với Báo cáo `not_computable`
* **Nội dung cải tiến**:
  * Mỗi lần chạy pipeline, dữ liệu thô từ CVAT và GitHub được đóng băng thành một thư mục snapshot độc lập tại `data/raw/<timestamp>/` kèm file kiểm toán `manifest.json`.
  * Hỗ trợ cờ `--offline sample_data/` cho phép chạy và kiểm thử toàn trình pipeline offline không cần mạng hoặc token thật.
  * Cơ chế `not_computable`: các chỉ số thiếu nguồn dữ liệu (ví dụ: thiếu log giờ làm việc, thiếu GT) được ghi rõ lý do thay vì thay bằng `0`, tránh tạo ra số liệu giả trên báo cáo.
* **Lý do & Căn cứ kỹ thuật**:
  * *Căn cứ kỹ thuật*: Bảo đảm tính toàn vẹn dữ liệu (Data Lineage & Reproducibility). Số liệu báo cáo luôn có bằng chứng gốc đối chiếu.
  * *Căn cứ nghiệp vụ*: Giúp các thành viên khác trong nhóm (Tuân làm ETL, Ngọc làm DevOps, Minh làm Power BI) có thể phát triển và kiểm thử code độc lập mà không bị phụ thuộc vào tính sẵn sàng của server CVAT Cloud.

---

## 📈 IV. ĐÁNH GIÁ CHUNG & KẾ HOẠCH TUẦN 2 (HƯỚNG TỚI MVP)

### 1. Đánh giá chung Tuần 1
* **Tiến độ tổng thể**: Đạt **90%** kế hoạch đề ra cho Tuần 1.
  * Tầng Ingestion (Extractors, Normalizer, Generator): **Hoàn thành 100%**.
  * Tầng Adapter ETL (cvat_snapshot, snapshot_metrics, tài liệu đặc tả): **Hoàn thành 100%**.
  * Tầng Processors (velocity, quality, geometry, segmentation): **0% — chuyển sang Tuần 2**.
* **Tình trạng phối hợp**: Nhóm giao tiếp hiệu quả, phân vai rõ ràng, tài liệu đặc tả chuẩn chỉ; kiến trúc được thiết kế kỹ trước khi code giúp tránh refactor lớn.
* **Rủi ro**: Các module processors chưa có file code là điểm chặn (blocker) chính của tuần 2, cần Tuân giải quyết sớm để không trễ tiến độ nạp CSV vào Power BI.

### 2. Kế hoạch trọng tâm Tuần 2 (Hạn chót Thứ Năm: 15/10/2026)
* **Phạm Nguyễn Tuân (Ưu tiên cao nhất)**:
  * Viết đủ 7 file module `src/processors/` theo thứ tự: `models.py` → `config.py` → `velocity.py` → `quality.py` → `geometry.py` → `segmentation.py` → `annotator_stats.py`.
  * Chạy `snapshot_metrics.py` end-to-end trên snapshot thực tế của Duy, kiểm chứng số liệu.
  * Viết Exporter CSV xuất bộ 4 file vào `data/processed/`.
  * Xin Lead Minh phê duyệt 8 giả định nghiệp vụ trong `README.md` mục 5.
* **Đinh Công Minh**:
  * Phê duyệt 8 giả định trong `src/processors/README.md` để unlock code cho Tuân.
  * Phác thảo wireframe chi tiết 5 trang Power BI, chuẩn bị sẵn Star Schema model.
  * Sau khi Tuân xuất CSV → nạp dữ liệu và viết bộ 20 công thức DAX Measures.
* **Nguyễn Minh Tú & Vũ Trường Duy**:
  * Tạo 1 Ground Truth Job mẫu (~50 frames) trên CVAT để endpoint `/api/quality/reports` trả về dữ liệu thật.
  * Kiểm thử tải dữ liệu trên task CVAT thực tế với số lượng frames lớn (>1,000 frames).
  * Hỗ trợ Tuân đối chiếu số liệu kiểm tra chéo (Data Reconciliation) khi processors xong.
* **Ngô Duy Ngọc**:
  * Cấp quyền `contents: write` trong `scheduled_report.yml`, test lại auto-commit CSV.
  * Hoàn thiện Bot Telegram bắn thông báo tóm tắt KPI trước các buổi họp.
* **Thứ 4 (14/10/2026)**: Họp tổng duyệt nội bộ (Internal Dry Run) toàn trình End-to-End.
* **Thứ 5 (15/10/2026)**: **Bảo vệ và nghiệm thu chính thức sản phẩm MVP cùng Mentor!**
