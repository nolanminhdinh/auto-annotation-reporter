"""Script kiểm tra và hiển thị dữ liệu thực tế trong SQLite Data Warehouse."""
import sqlite3
import sys

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

conn = sqlite3.connect('data/annotation_warehouse.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall() if not r[0].startswith('sqlite_')]
print(f"\n================================================================================")
print(f"📊 BÁO CÁO HIỆN TRẠNG KHO DỮ LIỆU WAREHOUSE: data/annotation_warehouse.db")
print(f"================================================================================")

for layer, prefix in [("1. TẦNG BRONZE (RAW / AUDIT TRAIL)", "bronze_"),
                      ("2. TẦNG SILVER (CLEANSED & ENRICHED)", "silver_"),
                      ("3. TẦNG GOLD (STAR SCHEMA & DATA MARTS)", "gold_")]:
    print(f"\n📁 {layer}:")
    layer_tables = [t for t in tables if t.startswith(prefix)]
    for t in layer_tables:
        cnt = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"   • {t:<32}: {cnt:>5} bản ghi")

print(f"\n🔍 TRUY VẾT LỊCH SỬ (AUDIT TRAIL SAMPLE):")
snap = cur.execute("SELECT snapshot_id, task_id, session_name, status, created_at FROM bronze_snapshots LIMIT 1").fetchone()
if snap:
    print(f"   - Snapshot ID : {snap['snapshot_id']}")
    print(f"   - Task ID     : {snap['task_id']}")
    print(f"   - Phiên họp   : {snap['session_name']}")
    print(f"   - Trạng thái  : {snap['status']}")
    print(f"   - Thời gian   : {snap['created_at']}")

print(f"\n📈 GOLD DATA MART KPI SAMPLE:")
kpi = cur.execute("SELECT task_id, task_name, total_frames_target, completed_frames_proxy, avg_velocity_fps, projected_completion_date FROM gold_mart_batch_progress LIMIT 1").fetchone()
if kpi:
    print(f"   - Task         : [{kpi['task_id']}] {kpi['task_name']}")
    print(f"   - Mục tiêu     : {kpi['total_frames_target']} frames | Đã đạt (Proxy): {kpi['completed_frames_proxy']} frames")
    print(f"   - Vận tốc TB   : {kpi['avg_velocity_fps']} frames/giờ")
    print(f"   - Dự kiến ETA  : {kpi['projected_completion_date']}")

print(f"================================================================================\n")
conn.close()
