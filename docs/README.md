# 📚 CẨM NANG ĐIỀU HƯỚNG TÀI LIỆU DỰ ÁN (DOCUMENTATION HUB)

> **Chào mừng bạn đến với kho tài liệu chính thức của dự án**  
> **Auto Annotation Report Pipeline (CVAT & GitHub Sync - Power BI Hybrid)**  
> 
> *Tài liệu này được thiết kế để bất kỳ ai (Mentor, Tech Lead, Thành viên mới hoặc Khách thẩm định) đều có thể dễ dàng tìm kiếm và hiểu sâu từng khía cạnh kỹ thuật của dự án chỉ sau 30 giây.*

---

## 🧭 BẠN MUỐN TÌM HIỂU ĐIỀU GÌ? (QUICK NAVIGATION MATRIX)

Dựa vào vai trò hoặc câu hỏi bạn đang quan tâm, hãy chọn thư mục tương ứng:

| Bạn là ai / Đang muốn xem gì? | Câu hỏi thường gặp | Bấm vào đây |
| :--- | :--- | :---: |
| 🏛️ **Tech Lead / Solution Architect** | *"Hệ thống hoạt động theo mô hình nào? Luồng dữ liệu 5 giai đoạn ra sao? Tại sao chọn mô hình Hybrid Python + Power BI?"* | 👉 [**`01-architecture/`**](01-architecture/) |
| 📊 **Data Analyst / BI Developer / Mentor** | *"Dữ liệu gồm những bảng nào? Công thức tính Vận tốc, FTPR, Rework, Diện tích ra sao? 5 trang Power BI hiển thị gì?"* | 👉 [**`02-data-and-analytics/`**](02-data-and-analytics/) |
| 🔌 **Backend / Data Integration Engineer** | *"CVAT REST API v2 gọi như thế nào? Cách sinh Deep Link tới frame hình? GitHub API lấy Issues ra sao?"* | 👉 [**`03-integrations/`**](03-integrations/) |
| ⚙️ **DevOps / SysAdmin / Automation Engineer** | *"Cấu hình GitHub Actions Cron chạy tự động thế nào? Cài đặt biến môi trường `.env` và Notification Bot ra sao?"* | 👉 [**`04-devops-automation/`**](04-devops-automation/) |
| 👥 **Project Manager / Team Member** | *"Ai phụ trách phần nào? Ma trận RACI và tiêu chí nghiệm thu của Lead Minh là gì? Timeline chạy MVP tuần này ra sao?"* | 👉 [**`05-project-management/`**](05-project-management/) |
| 📈 **Stakeholder / Người theo dõi tiến độ** | *"Tuần này nhóm đã làm được gì? Có việc gì chưa xong và tại sao? Các cải tiến kỹ thuật trong sản phẩm là gì?"* | 👉 [**`../reports/weekly/`**](../reports/weekly/) |

---

## 📂 CHI TIẾT CÁC THƯ MỤC TÀI LIỆU CHUYÊN SÂU

```text
docs/
├── 📁 01-architecture/            <-- Kiến trúc hệ thống, Mô hình Hybrid & 4 Workflows cốt lõi
├── 📁 02-data-and-analytics/      <-- Data Dictionary, Data Model, 20 DAX Measures & Mẫu báo cáo
├── 📁 03-integrations/            <-- Hướng dẫn tích hợp CVAT API v2 & GitHub API v3
├── 📁 04-devops-automation/       <-- Hướng dẫn CI/CD GitHub Actions, Cron & Bot thông báo
├── 📁 05-project-management/      <-- Kế hoạch dự án, Ma trận RACI, WBS 5 thành viên & Tiêu chuẩn nghiệm thu
└── 📁 assets/                     <-- Sơ đồ kiến trúc & Biểu đồ SVG
```

---

### 🏛️ 1. Thư mục `01-architecture/` — Kiến Trúc & Thiết Kế Hệ Thống
*Dành cho những ai muốn hiểu bức tranh tổng thể và nguyên lý vận hành của hệ sinh thái.*
* 📄 [`SYSTEM_ARCHITECTURE.md`](01-architecture/SYSTEM_ARCHITECTURE.md): Đặc tả chi tiết kiến trúc khép kín 5 giai đoạn (*Trigger $\to$ Extract $\to$ Process $\to$ Report $\to$ Review*).
* 📄 [`HYBRID_POWERBI_ARCHITECTURE.md`](01-architecture/HYBRID_POWERBI_ARCHITECTURE.md): Phân tích lý do lựa chọn mô hình Hybrid kết hợp giữa năng lực xử lý API linh hoạt của Python và khả năng trực quan hóa của Power BI.
* 📄 [`WORKFLOWS.md`](01-architecture/WORKFLOWS.md): Tổng hợp 4 sơ đồ luồng hoạt động Mermaid trực quan (Luồng khép kín, Mô hình Hybrid, Vận hành theo lịch).

---

### 📊 2. Thư mục `02-data-and-analytics/` — Nghiệp Vụ Dữ Liệu & Bộ Chỉ Số
*Dành cho Data Analyst, BI Developer hoặc Mentor đánh giá tính chặt chẽ của số liệu.*
* 📄 [`PROJECT_ANALYTICS_SPEC.md`](02-data-and-analytics/PROJECT_ANALYTICS_SPEC.md): **Tài liệu cốt lõi** chứa Mindmap nghiệp vụ, Data Model Star Schema, Data Dictionary 9 bảng, bộ 20 công thức DAX Measures, logic phân khúc nhân sự và đặc tả chi tiết 5 trang Power BI.
* 📄 [`METRICS_ETL_PROCESSORS_TECH_DOC.md`](02-data-and-analytics/METRICS_ETL_PROCESSORS_TECH_DOC.md): **Tài liệu xây dựng kỹ thuật** chi tiết bộ tính toán chỉ số (WBS 2.1 – 2.5), công thức AHT, lọc idle, Shoelace, COCO Scale, phân khúc 7 nhóm và xuất bản CSV.
* 📄 [`REPORT_TEMPLATE_SPEC.md`](02-data-and-analytics/REPORT_TEMPLATE_SPEC.md): Quy chuẩn cấu trúc bản báo cáo văn bản tóm tắt 4 phần gửi Mentor trước buổi họp.
* 📄 [`MENTOR_REPORT_SAMPLE.md`](02-data-and-analytics/MENTOR_REPORT_SAMPLE.md): Bản báo cáo mẫu thực tế được sinh tự động từ hệ thống.

---

### 🔌 3. Thư mục `03-integrations/` — Tích Hợp API & Thu Thập Dữ Liệu
*Dành cho kỹ sư tích hợp backend (Nguyễn Minh Tú & Vũ Trường Duy) hoặc ai muốn tái lập kết nối API.*
* 📄 [`CVAT_INTEGRATION_GUIDE.md`](03-integrations/CVAT_INTEGRATION_GUIDE.md): Hướng dẫn xác thực PAT Token, danh mục endpoint `/api/tasks`, `/api/jobs`, `/api/quality/reports` và quy tắc sinh URL Deep Link trực tiếp đến từng frame.
* 📄 [`GITHUB_INTEGRATION_GUIDE.md`](03-integrations/GITHUB_INTEGRATION_GUIDE.md): Hướng dẫn tích hợp GitHub REST API trích xuất danh sách ca khó có nhãn `ca-kho`, `blocker` và tự động tạo Pull Request Draft.

---

### ⚙️ 4. Thư mục `04-devops-automation/` — Tự Động Hóa & Vận Hành Hệ Thống
*Dành cho kỹ sư DevOps (Ngô Duy Ngọc) hoặc người triển khai hệ thống lên môi trường thật.*
* 📄 [`DEPLOYMENT_AND_WORKFLOW.md`](04-devops-automation/DEPLOYMENT_AND_WORKFLOW.md): Cẩm nang cài đặt môi trường, biến cấu hình `.env`, chạy lệnh CLI và thiết lập webhook.
* 📄 [`SCHEDULED_WORKFLOW_GUIDE.md`](04-devops-automation/SCHEDULED_WORKFLOW_GUIDE.md): Chi tiết cấu hình GitHub Actions Cron Trigger, khai báo GitHub Secrets và kiểm thử luồng chạy tự động.

---

### 👥 5. Thư mục `05-project-management/` — Quản Trị Dự Án & Phân Công Nhiệm Vụ
*Dành cho Trưởng dự án (Đinh Công Minh) và toàn bộ thành viên để nắm rõ trách nhiệm.*
* 📄 [`PROJECT_MANAGEMENT_PLAN.md`](05-project-management/PROJECT_MANAGEMENT_PLAN.md): Cơ cấu nhóm 5 người, bảng phân công nhiệm vụ chi tiết (WBS), ma trận trách nhiệm RACI, quy tắc Git Flow, Hợp đồng bàn giao dữ liệu và tiêu chí nghiệm thu của Lead.

---

### 📈 6. Thư mục `reports/weekly/` — Theo Dõi Tiến Độ Hàng Tuần
*Dành cho Mentor và các bên liên quan theo dõi tiến độ thực tế theo thời gian thực.*
* 📄 [`reports/weekly/README.md`](../reports/weekly/README.md): Quy chuẩn báo cáo tuần.
* 📁 [`reports/weekly/week-01/`](../reports/weekly/week-01/):
  * ⏱️ [`TIMELINE_CONG_VIEC.md`](../reports/weekly/week-01/TIMELINE_CONG_VIEC.md): Timeline chi tiết từng ngày của 5 thành viên.
  * 📊 [`BAO_CAO_TUAN_01.md`](../reports/weekly/week-01/BAO_CAO_TUAN_01.md): Báo cáo công việc đã làm, việc chưa làm & 3 cải tiến sản phẩm quan trọng kèm căn cứ kỹ thuật.
