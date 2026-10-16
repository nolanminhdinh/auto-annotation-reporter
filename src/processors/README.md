# 🧮 Bộ tính toán chỉ số (`src/processors/`)

> **Phạm vi**: WBS 2.1 – 2.4 · **Người phụ trách**: Phạm Nguyễn Tuân (Analytics & ETL Engineer) · **Nhánh**: `feature/metrics-etl`
> **Đặc tả gốc**: [`PROJECT_ANALYTICS_SPEC.md`](../../docs/02-data-and-analytics/PROJECT_ANALYTICS_SPEC.md) (mục 3 Data Dictionary, mục 4 Segmentation, mục 5 Measures)

Tầng tính toán của pipeline: nhận dữ liệu đã chuẩn hóa về các dataclass, trả về chỉ số theo đúng công thức của đặc tả để **số liệu Python khớp 100% với 20 measures DAX** trên Power BI.

Toàn bộ code là **Python thuần (stdlib)**, không cần cài thư viện nào, và **tất định** (cùng đầu vào luôn cho cùng kết quả, không dùng AI/LLM).

---

## 1. Cấu trúc

| File | WBS | Nội dung |
|---|:---:|---|
| `velocity.py` | 2.1 | Vận tốc frames/h và objects/h, AHT, lọc idle từ event log, tiến độ, dự báo ngày hoàn thành |
| `quality.py` | 2.2 | FTPR, Rejection Rate, Defect Density, chuẩn hóa taxonomy lỗi, điểm Ground Truth (IoU/F1) |
| `geometry.py` | 2.3 | Diện tích Shoelace và bbox, `frame_area_pct`, phân loại COCO scale |
| `segmentation.py` | 2.4 | Velocity Segment, Quality Risk Flag, Final Annotator Segmentation (7 nhóm) |
| `annotator_stats.py` | 2.4 | Gom chỉ số theo từng annotator thành `AnnotatorStats` cho segmentation |
| `models.py` | — | Dataclass đầu vào, tên trường bám Data Dictionary |
| `config.py` | — | Toàn bộ ngưỡng nghiệp vụ (`Thresholds`) |
| `_math.py` | — | `safe_div`, `mean_or_none` |

```text
dữ liệu thô (CVAT/GitHub) ──► adapters (Duy) ──► models ──► velocity / quality / geometry
                                                                 │
                                                                 ▼
                                                      annotator_stats ──► segmentation ──► exporters CSV (Tuân) ──► Power BI
```

---

## 2. Chạy thử và chạy test

Yêu cầu Python 3.10+. Chạy từ **thư mục gốc repo** (`metrics-etl-processors/`):

```bash
python -m unittest discover -s tests -v
```

Bộ test bao gồm toàn diện 48 test cases (14 adapter tests + 34 processor & exporter tests) dùng `unittest` stdlib, pass 100%.

```python
from datetime import date
from src.processors import geometry, velocity, quality, segmentation
from src.processors.annotator_stats import build_annotator_stats
from src.processors.models import Annotator, Job, Review

jobs = [Job(1, 217, "a1", "completed", 100, 50, 2.0, date(2026, 10, 9)),
        Job(2, 217, "a1", "annotation", 40, 20, 1.0)]
reviews = [Review("r1", 1, "rv1", 1, "Accepted")]

geometry.measure_shape("polygon", [0, 0, 4, 0, 4, 3, 0, 3], 1920, 1080)
# -> area_pixels=12.0, size_scale='Small', frame_area_pct≈0.00058
velocity.velocity_frames_per_hour(jobs)        # 33.33  (100 frame / 3 giờ)
quality.first_time_pass_rate(reviews)          # 1.0

stats = build_annotator_stats([Annotator("a1", joined_date=date(2026, 9, 10))],
                              jobs, reviews, as_of=date(2026, 10, 10))
segmentation.classify_annotator(stats[0]).final_segment.short_label
# -> 'Nhân sự nền tảng'
```

---

## 3. Công thức và ánh xạ sang DAX

| # | Measure (DAX) | Hàm Python | Ghi chú |
|:-:|---|---|---|
| 1 | `Total_Completed_Frames` | `velocity.total_completed_frames` | Tổng frame của job `status == "completed"` |
| 2 | `Total_Objects_Created` | `velocity.total_objects_created` | Tổng đối tượng của mọi job |
| 3 | `Total_Active_Hours` | `velocity.total_active_hours` | Cộng mọi job (không lọc status) |
| 4 | `Velocity_Frames_Per_Hour` | `velocity.velocity_frames_per_hour` | Xem lưu ý 4.1 |
| 5 | `Velocity_Objects_Per_Hour` | `velocity.velocity_objects_per_hour` | |
| 6 | `Avg_Time_Per_Frame_Mins` | `velocity.avg_time_per_frame_minutes` | giờ × 60 / frame completed |
| 7 | `Avg_Time_Per_Object_Secs` | `velocity.avg_time_per_object_seconds` | giờ × 3600 / số đối tượng |
| 8 | `First_Time_Pass_Rate` | `quality.first_time_pass_rate` | Chỉ tính review có `review_iteration == 1` |
| 9 | `Rejection_Rate` | `quality.rejection_rate` | Mọi lượt review, mọi iteration |
| 10 | `Total_Defects` | `quality.total_defects` | |
| 11 | `Defect_Density_Per_100F` | `quality.defect_density_per_100_frames` | lỗi × 100 / frame completed |
| 12 | `Avg_Defects_Per_Job` | `quality.avg_defects_per_job` | Chia cho số job khác nhau có review |
| 13 | `Avg_mIoU_Score` | `quality.avg_miou` | Bỏ qua giá trị thiếu |
| 14 | `Avg_F1_Score` | `quality.avg_f1` | Dùng `f1_score` nếu có, không thì tính từ P/R |
| 15 | `Avg_Object_Area_Pixels` | `geometry.avg_object_area` | |
| 16 | `Avg_Area_Frame_Pct` | `geometry.avg_area_frame_pct` | Đơn vị % (0–100) |
| 17 | `Pct_Small_Objects` | `geometry.pct_small_objects` | Mẫu số là toàn bộ đối tượng |
| 18 | `Count_At_Risk_Annotators` | — | Chưa có hàm riêng; đếm kết quả `classify_quality_risk` hoặc `rejection_rate >= 0.20` |
| 19 | `System_Avg_Velocity` | `velocity.velocity_frames_per_hour(tất cả job)` | Gộp toàn hệ thống |
| 20 | `Project_Progress_Pct` | `velocity.progress_ratio` | Tỷ số 0–1; cột CSV `progress_pct` = giá trị × 100 |

Ngoài bảng: `shoelace_area`, `rectangle_area`, `coco_scale`, `measure_shape` (geometry); `active_seconds_from_events`, `completed_frames_per_day`, `projected_completion_date` (velocity); `normalize_defect_type`, `defect_type_counts`, `f1_from_precision_recall` (quality).

### 3.1. COCO scale (mục 4.3)

| Diện tích (px²) | Nhãn |
|---|---|
| `< 1024` | `Small` |
| `1024 ≤ area ≤ 9216` (gồm cả hai đầu) | `Medium` |
| `> 9216` | `Large` |

### 3.2. Phân khúc (mục 4.1, 4.2, 4.4)

- **Velocity**: `≥ 60` siêu nhanh · `≥ 40` đạt chuẩn · `≥ 20` trung bình · còn lại chậm (frames/giờ).
- **Quality Risk**: rủi ro cao nếu `FTPR < 0.80` **hoặc** `Rejection Rate ≥ 0.20` **hoặc** `F1 < 0.85`.
- **Final Segment** đánh giá **lần lượt từ nhóm 1 đến 7**, nhóm nào khớp trước thì trả về ngay:

| Ưu tiên | `FinalSegment` | Điều kiện |
|:-:|---|---|
| 1 | `FAST_AND_FAULTY` | Siêu nhanh **và** rủi ro cao |
| 2 | `NEEDS_RETRAINING` | Chậm **và** rủi ro cao |
| 3 | `SLOW_BUT_STEADY` | Chậm **và** chất lượng đạt chuẩn |
| 4 | `STAR_ANNOTATOR` | Siêu nhanh/đạt chuẩn **và** chất lượng đạt chuẩn |
| 5 | `ONBOARDING` | Thâm niên ≤ 14 ngày **và** ≤ 10 job completed |
| 6 | `INACTIVE` | `active_hours_7d = 0` |
| 7 | `CORE_PERFORMER` | Các trường hợp còn lại |

Mỗi `FinalSegment` có `.priority`, `.short_label` (khớp tên slicer Power BI) và `.action` (hành động can thiệp theo bảng 4.4); `.name` là mã ổn định cho máy đọc.

---

## 4. Quy ước và lưu ý quan trọng

### 4.1. Chỗ cố ý bám đúng DAX hiện tại
`Velocity_Frames_Per_Hour` lấy **frame của job completed** chia cho **giờ của mọi job**, nên người đang có job dở bị tính thấp đi. Mặc định giữ nguyên để khớp DAX. Nếu Lead sửa DAX, đổi bằng `velocity_frames_per_hour(jobs, hours_basis="completed")`.

### 4.2. Dữ liệu thiếu
- Mẫu số bằng 0 hoặc thiếu dữ liệu → trả **`None`** (không trả 0). Lưu ý DAX `DIVIDE(..., 0)` trả 0, nên người chưa có review sẽ hiện FTPR = 0 trên Power BI; nên đổi alternate result của DAX thành `BLANK()`.
- Trong segmentation (theo ngữ nghĩa NULL của SQL trong đặc tả): vận tốc `None` coi là 0; FTPR/Rejection `None` không kích hoạt cờ rủi ro; F1 `None` coi là 1.0 (`ISNULL(mean_f1, 1.0)`); thâm niên `None` không xếp vào Onboarding.

### 4.3. Đơn vị
Tỷ lệ trả về **tỷ số 0–1** (FTPR, Rejection, progress, Pct_Small). Riêng `frame_area_pct` là **% 0–100** đúng Data Dictionary. Không làm tròn ở tầng này; làm tròn ở bước export CSV.

### 4.4. Lọc idle
`active_seconds_from_events` cộng khoảng cách giữa hai sự kiện liên tiếp nếu `≤ idle_gap_seconds` (mặc định 300 giây); khoảng dài hơn coi là treo máy và bỏ đi. `datetime` không có múi giờ được coi là UTC.

### 4.5. Dữ liệu bất thường
Tọa độ hỏng (rectangle không đủ 4 số, polygon dưới 3 đỉnh) → `ValueError`. Loại shape không đo được (`points`, `cuboid`...) → các trường đo là `None`. Mã lỗi lạ → đếm vào `unclassified` kèm cảnh báo log. Review/GT trỏ tới job không tồn tại → bỏ qua và ghi cảnh báo.

### 4.6. Taxonomy lỗi
5 mã của `REPORT_TEMPLATE_SPEC` được gộp về 4 nhóm chuẩn: `BOX_LOOSE`, `BOX_TIGHT_CLIPPED` → `box_displacement`; `MISLABELED` → `wrong_class`; `MISSED_OBJECT` → `missing_object`; `ATTRIBUTE_ERROR` → `wrong_attr`.

---

## 5. Giả định cần Lead (Minh) xác nhận

| # | Nội dung | Mặc định hiện tại |
|:-:|---|---|
| 1 | Ngưỡng idle | 300 giây (`config.idle_gap_seconds`) |
| 2 | Cửa sổ vận tốc ngày khi dự báo ETA | 7 ngày (`config.eta_window_days`) |
| 3 | `active_hours_7d` | Xấp xỉ bằng giờ của các job nộp trong 7 ngày gần nhất |
| 4 | Thứ tự đánh giá nhóm 5 (Onboarding) và 6 (Inactive) | Sau nhóm 1–4, đúng bảng 4.4. Hệ quả: người không có dữ liệu hoạt động bị xếp `SLOW_BUT_STEADY`; người mới nhưng vừa nhanh vừa lỗi nhiều bị xếp `FAST_AND_FAULTY` |
| 5 | Khoảng hở của bảng 4.4 | Vận tốc 20–59 f/h **và** rủi ro cao không thuộc nhóm 1–4 nên rơi xuống `CORE_PERFORMER`. Hành vi này được ghi lại trong `SpecLiteralBehaviourTests` |
| 6 | Đơn vị vận tốc trong `batch_progress.csv` | Hợp đồng ghi `avg_velocity_fps` (frames/**phút**, ví dụ 2.4 ≈ 144 f/h) trong khi ngưỡng phân khúc dùng frames/**giờ**. Code tính theo frames/giờ, có `frames_per_hour_to_per_minute` để đổi |
| 7 | Ánh xạ trạng thái CVAT sang `Job.status` | Adapter dùng thẳng trường `status` của job (snapshot thật của Duy có sẵn trường này, cùng từ vựng `annotation/validation/completed`), không dùng `stage`/`state`. Cần Minh xác nhận |
| 8 | "Đối tượng đã vẽ" của dữ liệu dạng track | Adapter đếm shape đơn và keyframe không `outside`; **không nội suy** track. Dữ liệu thật của Duy chỉ có track (8 track, 123 hộp vẽ), nên số này quyết định Objects/h và AHT/đối tượng |

Khi sửa quy tắc ở các mục 4–5, phải cập nhật test tương ứng cùng lúc.

---

## 6. Chưa làm

- **Adapter** đã có cho snapshot `cvat.json` của Duy (`src/adapters/cvat_snapshot.py`, chạy thử bằng `python -m src.adapters.snapshot_metrics <thư-mục-snapshot>`); chưa có cho schema chung `data/raw/` nếu nhóm đổi định dạng.
- **Exporter CSV** (WBS 2.5) vào `data/processed/`: 4 file `batch_progress`, `qa_metrics`, `annotator_segments`, `edge_cases`. Khi ghi nên dùng `utf-8-sig` để Power BI đọc đúng tiếng Việt.
- **`qa_score`** của `qa_metrics.csv`: tài liệu chưa định nghĩa cách tính nên chưa triển khai.
- **`Count_At_Risk_Annotators`** (Measure #18) chưa có hàm riêng.
- Nội suy track của CVAT: hình học chỉ đo trên các shape/keyframe được truyền vào.

---

## 7. Quy tắc phối hợp (theo `PROJECT_MANAGEMENT_PLAN.md`)

- Tên cột và kiểu dữ liệu xuất ra `data/processed/*.csv` chỉ được đổi khi **Đinh Công Minh** chấp thuận, để không làm gãy visual Power BI.
- Ngưỡng trong `config.py` ảnh hưởng trực tiếp đến phân khúc nhân sự nên cũng cần Lead duyệt.
- Mọi Pull Request do Lead review và merge; làm việc trên nhánh `feature/metrics-etl`.
