"""Script kết nối trực tiếp Power BI với Database SQLite (annotation_warehouse.db).

CÁCH SỬ DỤNG TRONG POWER BI DESKTOP:
1. Mở Power BI Desktop.
2. Bấm "Get data" (Lấy dữ liệu) -> Chọn "More..." -> Chọn "Python script" (hoặc "Tập lệnh Python") -> Bấm "Connect".
3. Dán toàn bộ nội dung trong script này vào ô nhập mã Python.
4. Bấm "OK".
5. Cửa sổ Navigator hiện lên: Tích chọn tất cả các bảng (dim_*, fact_*, marts) -> Bấm "Load".

KẾT QUẢ:
- Toàn bộ 15 bảng dữ liệu được kéo trực tiếp từ Database SQLite.
- Mỗi khi có đợt chạy ETL mới, bạn chỉ cần bấm nút "Refresh" trên Power BI là số liệu tự động cập nhật!
"""
import sqlite3
import pandas as pd
from pathlib import Path

# Đường dẫn tuyệt đối tới file Database SQLite
DB_PATH = r"C:\Users\MINH\vinai\Build phase\data\annotation_warehouse.db"

conn = sqlite3.connect(DB_PATH)

# ==============================================================================
# 1. BẢNG CHIỀU (DIMENSIONS) - TẦNG GOLD
# ==============================================================================
dim_annotators = pd.read_sql_query("SELECT * FROM gold_dim_annotators", conn)
dim_reviewers = pd.read_sql_query("SELECT * FROM gold_dim_reviewers", conn)
dim_tasks_batches = pd.read_sql_query("SELECT * FROM gold_dim_tasks_batches", conn)
dim_classes_labels = pd.read_sql_query("SELECT * FROM gold_dim_classes_labels", conn)
dim_date = pd.read_sql_query("SELECT * FROM gold_dim_date", conn)
dim_jobs = pd.read_sql_query("SELECT * FROM gold_dim_jobs", conn)

# ==============================================================================
# 2. BẢNG SỰ KIỆN (FACTS) - TẦNG GOLD
# ==============================================================================
fact_job_sessions = pd.read_sql_query("SELECT * FROM gold_fact_job_sessions", conn)
fact_annotations = pd.read_sql_query("SELECT * FROM gold_fact_annotations", conn)
fact_qa_reviews = pd.read_sql_query("SELECT * FROM gold_fact_qa_reviews", conn)
fact_qa_defects = pd.read_sql_query("SELECT * FROM gold_fact_qa_defects", conn)
fact_ground_truth_eval = pd.read_sql_query("SELECT * FROM gold_fact_ground_truth_eval", conn)
fact_edge_cases = pd.read_sql_query("SELECT * FROM gold_fact_edge_cases", conn)

# ==============================================================================
# 3. DATA MARTS TỔNG HỢP KPI - TẦNG GOLD
# ==============================================================================
batch_progress = pd.read_sql_query("SELECT * FROM gold_mart_batch_progress", conn)
qa_metrics = pd.read_sql_query("SELECT * FROM gold_mart_qa_metrics", conn)
annotator_segments = pd.read_sql_query("SELECT * FROM gold_mart_annotator_segments", conn)

conn.close()
