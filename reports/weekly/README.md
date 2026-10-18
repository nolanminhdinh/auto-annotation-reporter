# 📁 HỆ THỐNG BÁO CÁO TIẾN ĐỘ TUẦN (WEEKLY REPORTS REPOSITORY)

Thư mục này lưu trữ toàn bộ hồ sơ quản lý tiến độ, kế hoạch làm việc và báo cáo tổng kết hàng tuần của dự án **Auto Annotation Report Pipeline (CVAT & GitHub Sync - Power BI Hybrid)**.

---

## ⏰ LỊCH BÁO CÁO ĐỊNH KỲ (BI-WEEKLY REPORTING CADENCE)

Nhóm áp dụng cơ chế báo cáo tiến độ **2 buổi / tuần**:
* **Phiên 1 — Tối Thứ Năm (20:00 - 21:30)**:
  * Rà soát tiến độ giữa tuần so với Timeline kế hoạch.
  * Nhận diện và tháo gỡ các vướng mắc kỹ thuật (Blockers / Impasses).
  * Điều chỉnh phân bổ nguồn lực kịp thời trước hạn chót cuối tuần.
* **Phiên 2 — Tối Chủ Nhật (20:00 - 21:30)**:
  * Tổng kết và nghiệm thu toàn diện các sản phẩm bàn giao (Deliverables) trong tuần.
  * Đánh giá kiểm thử chéo và chạy End-to-End Pipeline.
  * Chốt kế hoạch Sprint chi tiết cho tuần tiếp theo.

---

## 📂 CẤU TRÚC THƯ MỤC BÁO CÁO

```text
reports/weekly/
├── README.md                           <-- Quy chuẩn & Mục lục báo cáo tuần
├── week-01/                            <-- Tuần 1: Khởi động, Nghiệp vụ, Kiến trúc & Tích hợp Ingestion
│   ├── TIMELINE_CONG_VIEC.md           <-- Timeline chi tiết từng ngày của 5 thành viên
│   ├── BAO_CAO_TUAN_01_LAN_01.md       <-- Báo cáo Lần 1 (Tối Thứ Năm, 08/10/2026): Nghiệp vụ & Prototype
│   └── BAO_CAO_TUAN_01_LAN_02.md       <-- Báo cáo Lần 2 (Tối Chủ Nhật, 11/10/2026): Nghiệm thu & Tích hợp Ingestion API
└── week-02/                            <-- Tuần 2: ETL Engine, LLM Báo Cáo Nhóm & Demo End-to-End
    ├── KE_HOACH_SPRINT_TUAN_02.md      <-- Kế hoạch chi tiết Sprint Tuần 2 hướng tới Demo E2E Chủ Nhật
    ├── BAO_CAO_TUAN_02_LAN_01.md       <-- Báo cáo Lần 1 (Tối Thứ Năm, 15/10/2026): Hợp nhất Medallion & LLM Summarizer
    └── BAO_CAO_TUAN_02_LAN_02.md       <-- Báo cáo Lần 2 (Tối Chủ Nhật, 18/10/2026): Nghiệm thu E2E & Đóng gói Build Phase
```

---

## 📋 QUY CHUẨN MẪU BÁO CÁO (REPORTING STANDARD)

Mỗi tuần, hồ sơ báo cáo bao gồm:

1. **`TIMELINE_CONG_VIEC.md`**:
   * Phân rã mục tiêu tuần và kế hoạch làm việc từ Thứ Hai đến Chủ Nhật.
   * Chi tiết đầu việc từng ngày của 5 thành viên:
     * **Đinh Công Minh** (Project Lead & BI Architect)
     * **Nguyễn Minh Tú** (Data Integration Engineer)
     * **Vũ Trường Duy** (Data Integration Engineer)
     * **Phạm Nguyễn Tuân** (Analytics & ETL Engineer)
     * **Ngô Duy Ngọc** (DevOps & Automation Engineer)

2. **`BAO_CAO_TUAN_XX_LAN_YY.md`**:
   * **Phần 1: Công việc đã hoàn thành**: Liệt kê chi tiết kết quả đạt được, tài liệu và mã nguồn đã hoàn thiện.
   * **Phần 2: Công việc chưa hoàn thành & Lý do**: Nêu rõ nguyên nhân gốc rễ (Root Cause) và giải pháp khắc phục.
   * **Phần 3: Đề xuất & Cải tiến sản phẩm (Product Improvements)**:
     * Nội dung cải tiến mới.
     * Lý do thực hiện cải tiến.
     * Căn cứ kỹ thuật (Technical Grounds) và căn cứ thực tế nghiệp vụ (Operational Grounds).
   * **Phần 4: Đánh giá & Kế hoạch tuần tiếp theo (Next Sprint Plan)**.
