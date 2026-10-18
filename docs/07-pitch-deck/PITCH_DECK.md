# 📑 BẢN THUYẾT TRÌNH DỰ ÁN (PITCH DECK)
## AUTO ANNOTATION REPORTER
### Hệ Thống Tự Động Hóa Quản Trị & Báo Cáo Gán Nhãn Dữ Liệu AI (CVAT & GitHub Sync)
#### *Mô Hình Hybrid: Python ETL Engine + Kho Dữ Liệu Medallion (SQLite) + Power BI 5-Page Dashboard*

> **Đội thi**: Team Auto Annotation Reporter (VinAI Build Phase 2026)  
> **Thành viên**: Đinh Công Minh (Lead & BI Architect), Phạm Nguyễn Tuân (Analytics & ETL), Vũ Trường Duy (Integration), Nguyễn Minh Tú (Data Collection), Ngô Duy Ngọc (DevOps & QA)  
> **GitHub Repository**: [https://github.com/nolanminhdinh/auto-annotation-reporter](https://github.com/nolanminhdinh/auto-annotation-reporter)  
> **Live Demo Web**: [https://nolanminhdinh.github.io/auto-annotation-reporter/](https://nolanminhdinh.github.io/auto-annotation-reporter/)

---

## 🖥️ SLIDE 1: TIÊU ĐỀ & ĐỘI NGŨ THỰC HIỆN

### 🚀 AUTO ANNOTATION REPORTER
**Enterprise-Grade Data Annotation Operations & Automated Analytics Pipeline**
*Giải pháp xóa bỏ phân mảnh dữ liệu, tự động hóa 100% báo cáo điều hành và giám sát chất lượng gán nhãn Computer Vision thời gian thực.*

* **Đinh Công Minh**: Project Lead & BI Architect — Định hướng giải pháp, thiết kế Power BI 5 trang, Star Schema và kiểm soát chất lượng.
* **Phạm Nguyễn Tuân**: Analytics & ETL Engineer — Xây dựng Python ETL Engine, thuật toán Shoelace, COCO scale và phân khúc 7 nhóm nhân sự.
* **Vũ Trường Duy**: Data Integration Engineer — Kết nối GitHub Issues API, đối soát cross-verification và Deep Link frame-level.
* **Nguyễn Minh Tú**: Data Collection Specialist — Kết nối CVAT REST API v2, bóc tách Jobs/Shapes và xây dựng Mock Data Generator.
* **Ngô Duy Ngọc**: DevOps & QA Specialist — Xây dựng CI/CD, chuẩn hóa taxonomy 4 nhóm lỗi và phụ trách bộ 136 tests.

---

## 🛑 SLIDE 2: BÀI TOÁN & NỖI ĐAU THỰC TẾ (THE PROBLEM)

Trong các dự án huấn luyện mô hình Thị giác máy tính (Computer Vision), chất lượng và tiến độ gán nhãn quyết định **80% sự thành bại** của mô hình. Tuy nhiên, khâu quản trị vận hành gán nhãn (Data Annotation Operations) đang đối mặt với 4 điểm nghẽn nghiêm trọng:

1. **Phân mảnh dữ liệu 2 thế giới**:
   - Tiến độ thực tế, bounding boxes, masks nằm trên **CVAT**.
   - Thảo luận kỹ thuật, ca khó (`ca-kho`), lỗi chặn (`blocker`) lại nằm trên **GitHub Issues**.
   - Không có sợi dây liên kết tự động giữa hai nền tảng.
2. **Lãng phí thời gian tổng hợp thủ công**:
   - Trưởng nhóm/Quản lý mất **2 đến 4 giờ** mỗi tuần để xuất CSV, đếm frame, tính vận tốc bằng Excel trước mỗi phiên họp Mentor.
3. **Mất dấu ca khó & Điểm mù chất lượng (Blind Spots)**:
   - Các frame gán nhãn gây tranh chấp bị trôi mất trên CVAT do thiếu cơ chế trỏ trực tiếp vào đúng khung hình lỗi (`?frame={idx}`).
4. **Thiếu kho kiểm toán (Audit Trail) & Báo cáo chắp vá**:
   - Dữ liệu CSV phân tán, không có lịch sử snapshot để đối soát khi có khiếu nại chất lượng hoặc tính toán KPI sai lệch.

---

## 💡 SLIDE 3: GIẢI PHÁP ĐỘT PHÁ (THE SOLUTION)

**Auto Annotation Reporter** là hệ sinh thái tự động hóa hoàn chỉnh khép kín từ khâu trích xuất dữ liệu đa nguồn đến phân tích chuyên sâu và trực quan hóa điều hành:

* 🔄 **Tích hợp hai chiều CVAT & GitHub**: Tự động thu thập API, bóc tách frame index bằng Regex và tạo sinh **Deep Link Frame-Level** chính xác 100%.
* 🏛️ **Kho dữ liệu Medallion Lakehouse 3 lớp (Bronze $\to$ Silver $\to$ Gold)**: Lưu trữ lịch sử toàn vẹn (Append-only audit trail), chuẩn hóa thực thể và tổ chức mô hình hình sao (Kimball Star Schema) trên SQLite/PostgreSQL.
* ⚡ **Động cơ phân tích hình học & KPI chuẩn hóa**: Tính toán 20 chỉ số nghiệp vụ, thuật toán Shoelace Gauss tính diện tích đa giác, phân loại COCO scale và ma trận 7 nhóm nhân sự.
* 🤖 **AI Summarizer (Gemini LLM + Heuristic Fallback)**: Tự động đọc và tổng hợp văn bản thô từ 4 tổ gán nhãn thành bản tóm tắt điều hành súc tích.
* 📊 **Trực quan hóa đa kênh**: Power BI Desktop 5 trang (Direct DB Connection / One-Click Refresh) kết hợp Standalone HTML Viewer mở xem tức thời.

---

## 🏗️ SLIDE 4: KIẾN TRÚC HỆ THỐNG (SYSTEM ARCHITECTURE)

Hệ thống được thiết kế theo chuẩn Enterprise Data Pipeline với 5 tầng rõ ràng:

1. **Trigger Layer**: GitHub Actions Cron định kỳ hoặc Lệnh kích hoạt thủ công CLI (`START_AUTO.cmd` / `src/sync.py`).
2. **Ingestion Layer**:
   - CVAT REST API v2 (`/api/tasks`, `/api/jobs`, `/api/annotations`, `/api/quality`).
   - GitHub REST API v3 (Issues, Labels, Comments).
   - Cross-System Link Verifier: Đối soát tính hợp lệ của liên kết giữa Task/Job và Issue.
3. **Storage Layer (Medallion Lakehouse)**:
   - *Bronze Layer*: Raw JSON Payloads nguyên bản (Append-only).
   - *Silver Layer*: Cleaned Entities, Shoelace Area, COCO Scale, 4 Taxonomy Groups.
   - *Gold Layer*: Star Schema (6 Bảng Chiều + 6 Bảng Sự Kiện) và 3 Data Marts nghiệp vụ.
4. **Analytics & AI Engine**:
   - Động cơ tính Vận tốc, FTPR, Rework %, Defect Density, Shoelace Area.
   - LLM Summarizer tổng hợp góc nhìn đa tổ nhóm.
5. **Consumption Layer**:
   - Power BI 5 trang chuẩn doanh nghiệp.
   - Báo cáo điều hành `MENTOR_REPORT_DRAFT.md` (chuẩn múi giờ UTC+7).
   - Interactive AI Agent CLI & Bot Telegram ping thông báo.

---

## ⭐ SLIDE 5: ĐIỂM SÁNG CÔNG NGHỆ ĐỘT PHÁ (KEY INNOVATIONS)

1. **Deep Link Frame-Level Thông Minh**:
   - Tự động bắt cặp GitHub Issue và frame gán nhãn trên CVAT qua cú pháp Regex thông minh (`frame 142`, `f:142`, `[frame=142]`).
   - Click 1 phát từ Power BI Dashboard hoặc Báo cáo Markdown nhảy thẳng vào khung hình bị lỗi trên CVAT web: `https://cvat.org/tasks/12/jobs/34?frame=142`.
2. **Thuật toán Hình học Gauss Shoelace & COCO Scale**:
   - Tính diện tích đa giác phẳng thời gian thực:
     $$\text{Area} = \frac{1}{2} \left| \sum (x_i y_{i+1} - x_{i+1} y_i) \right|$$
   - Tự động phân loại độ khó vật thể: Small ($< 32^2$), Medium, Large ($> 96^2$).
3. **Ma trận Phân khúc 7 Nhóm Nhân Sự (Annotator Matrix)**:
   - Phân loại nhân sự theo 2 trục Vận tốc và Chất lượng (FTPR): *Ngôi sao hiệu suất, Cẩn trọng, Tốc độ cần kiểm soát, Cần đào tạo lại, Chuyên gia ca khó, v.v.* Giúp phân bổ công việc công bằng và chuẩn xác.
4. **Resilience & Security by Design**:
   - Tự động retry với exponential backoff khi gặp lỗi mạng/rate-limit.
   - Chống tấn công SSRF và rò rỉ token bảo mật.
   - Bộ Heuristic Fallback bảo đảm pipeline chạy thông suốt 100% kể cả khi mất mạng.

---

## 📊 SLIDE 6: TRẢI NGHIỆM SẢN PHẨM LIVE & DASHBOARD 5 TRANG

Bản báo cáo trực quan Power BI được thiết kế theo chuẩn UI/UX doanh nghiệp hiện đại với 5 trang nghiệp vụ chuyên biệt:

* **Trang 1: Executive 360** — Bức tranh toàn cảnh tiến độ dự án: % hoàn thành, vận tốc gán nhãn, số giờ tích cực, dự báo ngày hoàn thành (ETA Completion Window).
* **Trang 2: QA Deep-Dive** — Giám sát chất lượng chuyên sâu: Tỷ lệ đạt lần đầu (FTPR), tỷ lệ từ chối (Rejection Rate), phân tích 4 nhóm lỗi gán nhãn (Taxonomy Defect Matrix), điểm kiểm tra chéo Ground Truth IoU & F1-Score.
* **Trang 3: People & Annotator Matrix** — Quản trị nhân sự: Biểu đồ Scatter 2 trục (Tốc độ vs Chất lượng), bảng xếp hạng hiệu suất 7 nhóm nhân viên.
* **Trang 4: Data Geometry & COCO Scale** — Phân tích đặc trưng tập dữ liệu: Phân bổ diện tích vật thể gán nhãn, tương quan giữa kích thước vật thể và tỷ lệ lỗi sai sót.
* **Trang 5: Edge-Case Explorer** — Quản lý điểm nóng kỹ thuật: Đồng bộ danh sách ca khó từ GitHub Issues, tích hợp nút bấm Deep Link mở trực tiếp frame CVAT để Mentor nghiệm thu tức thời.

---

## 🧪 SLIDE 7: CHẤT LƯỢNG KỸ THUẬT & KIỂM THỬ KHẮT KHE

* ✅ **136/136 Unit Tests PASS 100%**:
  - Thời gian thực thi toàn bộ test suite chỉ **2.57 giây**.
  - Kiểm thử đầy đủ: Base Client, Ingestion, Normalizer, Geometry, Processors, Storage Medallion, AI Summarizer, Notifier, Reporting Pipeline.
* ✅ **Đối soát kép (Double-Entry Reconciliation)**:
  - 20/20 chỉ số kinh doanh giữa **Python ETL Engine** và **Power BI DAX Measures** đạt độ khớp **100% (sai lệch 0.0000%)**.
  - Không có sự khác biệt giữa logic tính toán nội bộ và số liệu trình diễn trước Ban Giám Khảo.
* ✅ **Zero-Ops & Multi-Machine Portability**:
  - File khởi động `START_AUTO.cmd` và `Xem_Bao_Cao.bat` tự động cài đặt môi trường, nạp dữ liệu và mở dashboard trên bất kỳ máy Windows nào mà không gặp lỗi cấu hình.

---

## 📈 SLIDE 8: HIỆU QUẢ HOẠT ĐỘNG & TÍNH KHẢ THI (FEASIBILITY & ROI)

### Đo lường hiệu quả cụ thể:
| Chỉ số vận hành | Quy trình thủ công cũ | Giải pháp Auto Annotation Reporter | Mức độ cải thiện |
|---|:---:|:---:|:---:|
| **Thời gian tổng hợp báo cáo** | 2 – 4 giờ / tuần | **0.85 – 2.4 giây** | **Nhanh hơn ~12.000 lần** |
| **Thời gian truy vết frame lỗi** | 10 – 15 phút tìm kiếm thủ công | **1 click chuột (< 1 giây)** | **Tiết kiệm 99% thời gian** |
| **Tính toàn vẹn số liệu** | Dễ sai sót khi tính tay Excel | **Tuyệt đối (136 tests pass, DB Medallion)** | **Loại bỏ 100% lỗi con người** |
| **Chi phí hạ tầng vận hành** | Server Database phức tạp | **Zero-Ops (SQLite Embedded / GitHub Actions)** | **Tiết kiệm 100% chi phí server** |

### Tính khả thi cao (Feasibility):
- **Khả thi kỹ thuật**: Sử dụng 100% công nghệ tiêu chuẩn (Python, SQLite, Power BI, GitHub Actions), không đòi hỏi hạ tầng đắt tiền.
- **Khả năng ứng dụng ngay**: Sẵn sàng tích hợp ngay vào bất kỳ dự án AI/CVAT nào đang chạy tại VinAI hoặc các công ty AI.

---

## 🚀 SLIDE 9: ĐỊNH HƯỚNG PHÁT TRIỂN (ROADMAP)

Dự án có lộ trình phát triển rõ ràng từ giải pháp quản trị hiện tại đến nền tảng điều phối thông minh cho Data-Centric AI:

* 🏁 **Giai đoạn 1 (Hiện tại - Build Phase)**:
  - Hoàn thiện trọn vẹn pipeline tự động hóa: Ingestion đa nguồn $\to$ Medallion DB $\to$ Power BI 5 trang $\to$ AI Summarizer $\to$ Multi-Machine Setup.
* 🌿 **Giai đoạn 2 (Q1/2027) — Mở rộng & Phân tích Nâng cao**:
  - Hỗ trợ thêm các nền tảng gán nhãn phổ biến khác: **Label Studio**, **Roboflow**, **V7 Darwin**.
  - Tích hợp mô hình Machine Learning phát hiện bất thường tự động (**Anomaly Detection**): Tự động cảnh báo annotator có dấu hiệu gian lận thời gian hoặc tỷ lệ lỗi tăng đột biến.
* 🚀 **Giai đoạn 3 (Q2/2027) — Điều phối Thông minh (Smart AI Orchestration)**:
  - **Smart Task Routing**: Tự động phân phối các frame có vật thể nhỏ (COCO Small) hoặc góc quay khó cho những annotators có điểm chất lượng cao nhất.
  - **Active Learning Feedback Loop**: Tích hợp mô hình AI gán nhãn sơ bộ (Pre-annotation) và đánh giá độ tự tin (Confidence Scoring) trước khi chuyển qua con người kiểm duyệt.

---

## 👥 SLIDE 10: ĐỘI NGŨ THỰC HIỆN & CAM KẾT (TEAM & EXECUTION)

Dự án được xây dựng bởi đội ngũ 5 thành viên đầy nhiệt huyết với tinh thần làm việc kỷ luật, bám sát phương pháp Agile/Scrum:

* 👑 **Đinh Công Minh (Project Lead & BI Architect)**: Người dẫn dắt tầm nhìn sản phẩm, thiết kế kiến trúc BI 5 trang, Data Model Star Schema và chỉ đạo hoàn thiện toàn bộ hồ sơ dự án.
* ⚙️ **Phạm Nguyễn Tuân (Analytics & ETL Engineer)**: Tác giả của bộ máy tính toán chỉ số, thuật toán Shoelace và mô hình phân khúc nhân sự.
* 🔗 **Vũ Trường Duy (Data Integration Engineer)**: Chuyên gia kết nối GitHub API, thuật toán đối soát Deep Link và cơ chế an toàn mạng.
* 📦 **Nguyễn Minh Tú (Data Collection Specialist)**: Chuyên gia kết nối CVAT REST API và bộ dữ liệu giả lập chuẩn hóa.
* 🛡️ **Ngô Duy Ngọc (DevOps & QA Specialist)**: Người thiết lập hệ thống kiểm thử tự động, chuẩn hóa 4 nhóm lỗi QA và luồng CI/CD.

---

## 🎯 SLIDE 11: LỜI KẾT & KÊU GỌI HÀNH ĐỘNG (CALL TO ACTION)

> *"Dữ liệu sạch tạo nên mô hình AI xuất sắc. Auto Annotation Reporter biến quá trình gán nhãn dữ liệu từ một 'hộp đen' thủ công, phân mảnh thành một dây chuyền công nghiệp minh bạch, chuẩn xác và tự động hóa 100%."*

* 🌐 **Trải nghiệm Live Demo ngay**: [https://nolanminhdinh.github.io/auto-annotation-reporter/](https://nolanminhdinh.github.io/auto-annotation-reporter/)
* 💻 **Mã nguồn dự án**: [https://github.com/nolanminhdinh/auto-annotation-reporter](https://github.com/nolanminhdinh/auto-annotation-reporter)
* 📬 **Liên hệ**: Đinh Công Minh (`nolanminhdinh`)

**CẢM ƠN BAN GIÁM KHẢO VÀ CÁC MENTOR VINAI ĐÃ THEO DÕI!**
