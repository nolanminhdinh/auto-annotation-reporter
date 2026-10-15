# 📑 BÁO CÁO CÔNG VIỆC & ĐÁNH GIÁ HIỆU QUẢ KỸ THUẬT
## Module: Tính Toán Chỉ Số & Xuất Dữ Liệu Power BI (`metrics-etl-processors`)

* **Dự án**: [auto-annotation-reporter](https://github.com/nolanminhdinh/auto-annotation-reporter)
* **Người thực hiện**: **Phạm Nguyễn Tuân** (Analytics & ETL Engineer)
* **Người nhận báo cáo / Đánh giá**: **Đinh Công Minh** (Project Lead & BI Architect)
* **Nhánh làm việc**: `feature/metrics-etl-processors-tuan`
* **Thời điểm báo cáo**: 15/10/2026
* **Trạng thái**:  **COMPLETED & READY FOR REVIEW (Hoàn thành 100% WBS 2.1 – 2.5, 48/48 tests PASS)**

---

## 🎯 I. TỔNG QUAN & MỤC TIÊU CÔNG VIỆC

Theo phân công trong Kế hoạch Dự án v1.1.0 và Sprint Tuần 2, thành viên Phạm Nguyễn Tuân chịu trách nhiệm toàn bộ tầng **Metrics ETL & Processors** (`metrics-etl-processors`), bao gồm:
1. **WBS 2.1**: Tính toán vận tốc gán nhãn, tiến độ batch, AHT và dự báo ngày hoàn thành (ETA).
2. **WBS 2.2**: Đo lường chất lượng QA/QC (FTPR, Rejection Rate, Defect Density, Taxonomy chuẩn hóa và Ground Truth F1/mIoU).
3. **WBS 2.3**: Đo lường đặc trưng hình học đối tượng (Shoelace area, Bbox area, COCO scale classification, frame area ratio).
4. **WBS 2.4**: Tổng hợp thống kê nhân sự (`AnnotatorStats`) và thuật toán ma trận phân khúc 7 nhóm nhân sự (`Final Annotator Segmentation`).
5. **WBS 2.5**: Tầng xuất bản dữ liệu chuẩn hóa CSV (`src/exporters/csv_exporter.py`) cung cấp đầu vào trực tiếp cho Power BI Dashboard.

---

## 🛠️ II. CHI TIẾT CÁC CÔNG VIỆC ĐÃ HOÀN THÀNH

### 1. Chuẩn hóa & Dọn dẹp cấu trúc thư mục
- **Loại bỏ trùng lặp**: Phát hiện và xóa bỏ file `metrics-etl-processors/readmereport.md` trùng lặp 100% nội dung với `src/processors/README.md`. Giữ lại duy nhất `src/processors/README.md` làm tài liệu kỹ thuật chuẩn mực.
- **Dọn dẹp file tạm**: Loại bỏ các file scratch/log chạy thử ngoài danh mục Data Contract để giữ workspace sạch sẽ.

### 2. Tầng Tính Toán Chỉ Số (`src/processors/`)
Toàn bộ mã nguồn tuân thủ nguyên tắc **100% Python Standard Library (không phụ thuộc third-party)**, thuật toán tất định (deterministic), khớp tuyệt đối với **20 DAX Measures** theo đặc tả [`PROJECT_ANALYTICS_SPEC.md`](file:///d:/vin/build_phase/docs/02-data-and-analytics/PROJECT_ANALYTICS_SPEC.md):

* **[`src/processors/velocity.py`](file:///d:/vin/build_phase/metrics-etl-processors/src/processors/velocity.py) (WBS 2.1)**:
  - Khớp các DAX: `#1 Total_Completed_Frames`, `#2 Total_Objects_Created`, `#3 Total_Active_Hours`, `#4 Velocity_Frames_Per_Hour`, `#5 Velocity_Objects_Per_Hour`, `#6 Avg_Time_Per_Frame_Mins`, `#7 Avg_Time_Per_Object_Secs`, `#19 System_Avg_Velocity`, `#20 Project_Progress_Pct`.
  - Hỗ trợ tham số `hours_basis="all"` (khớp DAX mặc định) và `hours_basis="completed"`.
  - Thuật toán `active_seconds_from_events`: Lọc idle time từ log sự kiện dựa trên ngưỡng `idle_gap_seconds` (mặc định 300s).
  - Thuật toán dự báo tiến độ: `completed_frames_per_day` (cửa sổ 7 ngày gần nhất) và `projected_completion_date` (ETA).

* **[`src/processors/quality.py`](file:///d:/vin/build_phase/metrics-etl-processors/src/processors/quality.py) (WBS 2.2)**:
  - Khớp các DAX: `#8 First_Time_Pass_Rate`, `#9 Rejection_Rate`, `#10 Total_Defects`, `#11 Defect_Density_Per_100F`, `#12 Avg_Defects_Per_Job`, `#13 Avg_mIoU_Score`, `#14 Avg_F1_Score`.
  - Chuẩn hóa taxonomy lỗi về 4 nhóm chuẩn: `box_displacement`, `wrong_class`, `missing_object`, `wrong_attr`; tự động ghi nhận cảnh báo và gom mã lỗi lạ vào `unclassified`.
  - Tính toán F1 Score tự động từ Precision và Recall khi nguồn đánh giá không cung cấp sẵn F1.

* **[`src/processors/geometry.py`](file:///d:/vin/build_phase/metrics-etl-processors/src/processors/geometry.py) (WBS 2.3)**:
  - Khớp các DAX: `#15 Avg_Object_Area_Pixels`, `#16 Avg_Area_Frame_Pct`, `#17 Pct_Small_Objects`.
  - Thuật toán Shoelace (Gauss) tính diện tích đa giác (polygon/polyline) và diện tích hình chữ nhật (bbox).
  - Phân loại chuẩn COCO scale: `Small` (< 1024 px²), `Medium` (1024 – 9216 px²), `Large` (> 9216 px²).
  - Bảo vệ lỗi tọa độ (raise `ValueError` khi polygon < 3 đỉnh hoặc bbox < 4 tọa độ).

* **[`src/processors/annotator_stats.py`](file:///d:/vin/build_phase/metrics-etl-processors/src/processors/annotator_stats.py) & [`src/processors/segmentation.py`](file:///d:/vin/build_phase/metrics-etl-processors/src/processors/segmentation.py) (WBS 2.4)**:
  - Xây dựng dataclass `AnnotatorStats` gom đầy đủ lịch sử: sản lượng, vận tốc, thâm niên (`tenure_days`), thời gian làm 7 ngày gần nhất (`active_hours_7d`), tỷ lệ pass, tỷ lệ reject và điểm F1.
  - Phân loại vận tốc: `SUPER_FAST` (≥ 60 f/h), `ON_TARGET` (40–59 f/h), `AVERAGE` (20–39 f/h), `SLOW` (< 20 f/h).
  - Cờ rủi ro chất lượng `QualityRiskFlag`: Cảnh báo rủi ro cao khi FTPR < 80% hoặc Rejection Rate ≥ 20% hoặc F1 < 0.85.
  - Ma trận phân khúc 7 nhóm nhân sự theo thứ tự ưu tiên (1 → 7):
    1. `FAST_AND_FAULTY`: Nguy cơ gán ẩu (Ưu tiên 1)
    2. `NEEDS_RETRAINING`: Cần đào tạo lại (Ưu tiên 2)
    3. `SLOW_BUT_STEADY`: Cầu toàn quá mức (Ưu tiên 3)
    4. `STAR_ANNOTATOR`: Nhân sự nòng cốt (Ưu tiên 4)
    5. `ONBOARDING`: Nhân sự mới đang làm quen (Ưu tiên 5)
    6. `INACTIVE`: Ngủ đông / Không hoạt động (Ưu tiên 6)
    7. `CORE_PERFORMER`: Nhân sự nền tảng (Ưu tiên 7)
  - Cung cấp sẵn nhãn ngắn `short_label` cho slicer Power BI và khuyến nghị hành động can thiệp quản lý `action`.

### 3. Tầng Xuất Bản CSV Cho Power BI (`src/exporters/csv_exporter.py` - WBS 2.5)
Đã tinh chỉnh và bám sát triệt để Data Contract và các lưu ý quản trị dữ liệu từ tài liệu ghi chú dữ liệu thực tế của Duy (`personal-notes.md`):

1. **Chuẩn mã hóa UTF-8 BOM (`utf-8-sig`)**: Đảm bảo Power BI và Excel trên hệ điều hành Windows mở file trực tiếp mà không bao giờ bị lỗi font tiếng Việt.
2. **Làm tròn chuẩn ở tầng xuất bản**: Làm tròn 4 chữ số thập phân (`ROUND_DP = 4`), giữ nguyên độ chính xác float trong suốt quá trình tính toán nghiệp vụ.
3. **Đảm bảo Header khi dữ liệu rỗng**: Bổ sung cơ chế ghi cố định hàng tiêu đề cột chuẩn ngay cả khi snapshot không có dữ liệu (0 bản ghi), giải quyết triệt để lỗi Schema mismatch / Empty file trong Power BI.
4. **Bám sát nguyên tắc quản trị dữ liệu của Duy**:
   - `total_active_hours`: Trả về `None/null` khi snapshot thiếu log CVAT Analytics; **tuyệt đối không gán 0** để tránh ngộ nhận là annotator làm việc với thời gian bằng 0.
   - `completed_frames_proxy`: Định danh rõ ràng là proxy từ các job có status `completed`, chú thích cụ thể không phải là tỷ lệ frame pass QA (thực tế = null).
   - `edge_cases.csv`: Đổi nguồn dữ liệu chính xác sang `report_data.json -> edge_cases.items[]` (được trích xuất từ GitHub issues có nhãn `ca-kho` đã xác minh liên kết CVAT), không nhầm lẫn sang defect CVAT.

---

## 📊 III. ĐÁNH GIÁ HIỆU QUẢ KỸ THUẬT (PERFORMANCE & METRICS)

| Tiêu chí | Kết quả đạt được | Ý nghĩa kỹ thuật |
|---|:---:|---|
| **Độ bao phủ Test (Coverage)** | **48/48 tests PASS (100%)** | 14 test adapter (Duy) + 34 test processors/exporters (Tuân) |
| **Thời gian thực thi test** | **0.080s** | Cực kỳ nhanh, có thể tích hợp vào pre-commit hook hoặc CI |
| **Sự phụ thuộc (Dependencies)** | **0 thư viện bên ngoài** | 100% Python Standard Library, không lo xung đột môi trường |
| **Khớp nối với DAX Measures** | **20/20 measures (100%)** | Khớp công thức tuyệt đối giữa Python backend và Power BI |
| **Khả năng tương thích dữ liệu** | **100% (cả fixture & snapshot thật)** | Chạy thành công trên cả `sample_data` và `sample_data/real_snapshot` |

### Chi tiết bộ Unit Test (48 Tests):
* `tests/adapters/test_cvat_snapshot.py`: 14 tests (Adapter CVAT & Metadata)
* `tests/processors/test_geometry.py`: 7 tests (Shoelace, Bbox, COCO Scale, Aggregates)
* `tests/processors/test_quality.py`: 7 tests (FTPR, Rejection Rate, Taxonomy, GT Scores)
* `tests/processors/test_velocity.py`: 8 tests (Velocity measures, AHT, ETA, Idle log filter)
* `tests/processors/test_annotator_stats.py`: 1 test (Gom chỉ số toàn diện per-annotator)
* `tests/processors/test_segmentation.py`: 5 tests (Ma trận phân khúc 7 nhóm, short label, action)
* `tests/exporters/test_csv_exporter.py`: 6 tests (Kiểm tra schema 4 bảng CSV, UTF-8 BOM, dữ liệu rỗng và ca khó)

---

## 🚀 IV. HƯỚNG DẪN KIỂM THỬ & SỬ DỤNG

### 1. Chạy toàn bộ Unit Tests
Từ thư mục gốc `metrics-etl-processors/`:
```bash
python -m unittest discover -s tests -v
```

### 2. Xuất dữ liệu CSV cho Power BI
```bash
# Chạy với dữ liệu mẫu (sample_data)
python -m src.exporters.csv_exporter ../sample_data --output-dir ../data/processed

# Chạy với snapshot thực tế task 217 (real_snapshot)
python -m src.exporters.csv_exporter ../sample_data/real_snapshot --output-dir ../data/processed_real
```
4 file CSV đầu ra sẽ được sinh tại thư mục đích:
- `batch_progress.csv`: Tiến độ batch và vận tốc tổng hợp
- `qa_metrics.csv`: Chỉ số chất lượng QA/QC toàn task
- `annotator_segments.csv`: Phân khúc và hiệu suất chi tiết từng annotator
- `edge_cases.csv`: Danh sách ca khó kèm deep link CVAT

---

## 📌 V. ĐỀ XUẤT TIẾP THEO CHO LEAD MINH

1. **Review & Merge**: Đề nghị Lead Minh kiểm tra mã nguồn tại nhánh `feature/metrics-etl-processors-tuan` và merge vào nhánh `main`.
2. **Tích hợp Pipeline End-to-End**: Kết nối `csv_exporter.py` vào bộ điều phối CLI chung (`src/sync.py`) để quy trình từ:
   $$\text{CVAT / GitHub API} \longrightarrow \text{Adapter Snapshot} \longrightarrow \text{Processors} \longrightarrow \text{CSV Exporters} \longrightarrow \text{Power BI}$$
   hoàn toàn tự động hóa chỉ với một lệnh chạy duy nhất.
3. **Nạp dữ liệu vào Power BI Template**: Nạp 4 file CSV tại `data/processed/` vào file template báo cáo (`.pbit`) để kiểm chứng trực quan 20 DAX Measures trên giao diện Dashboard.
