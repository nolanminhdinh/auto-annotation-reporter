"""Optional Python connector: only the currently published canonical snapshot.
Prefer AnnotationReporter.pbip's CSV source (no pandas/ODBC installation needed).
"""
import sqlite3
from contextlib import closing
import pandas as pd

# Update this path on another machine. mode=ro prevents creating an empty DB.
DB_PATH = r"C:\Users\MINH\vinai\Build phase\data\annotation_reporting.db"
TABLES = (
    "dim_annotators", "dim_reviewers", "dim_tasks_batches", "dim_classes_labels",
    "dim_date", "dim_jobs", "fact_job_sessions", "fact_annotations", "fact_qa_reviews",
    "fact_qa_defects", "fact_ground_truth_eval", "fact_edge_cases", "report_status", "kpi_reconciliation",
)
with closing(sqlite3.connect("file:" + DB_PATH.replace("\\", "/") + "?mode=ro", uri=True)) as conn:
    for name in TABLES:
        globals()[name] = pd.read_sql_query("SELECT * FROM pbi_" + name, conn).drop(columns=["snapshot_id"])
