import json
import shutil
import sys
import zipfile
from pathlib import Path

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

src = Path("powerbi/Dashboard.pbix")
dst = Path("powerbi/Dashboard_Configured.pbix")

pages_meta = {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.1.0/schema.json",
    "pageOrder": [
        "page_exec_360",
        "page_qa_deepdive",
        "page_annotator_matrix",
        "page_data_geometry",
        "page_edge_cases"
    ],
    "activePageName": "page_exec_360"
}

pages = [
    ("page_exec_360", "1. Executive 360"),
    ("page_qa_deepdive", "2. QA Deep-Dive"),
    ("page_annotator_matrix", "3. Annotator Matrix"),
    ("page_data_geometry", "4. Data Geometry"),
    ("page_edge_cases", "5. Edge-Case Explorer"),
]

# Đọc zip gốc
with zipfile.ZipFile(src, "r") as zin:
    files = {item.filename: zin.read(item.filename) for item in zin.infolist()}

# Xóa các page cũ
files = {k: v for k, v in files.items() if not k.startswith("Report/definition/pages/")}

# Thêm pages.json
files["Report/definition/pages/pages.json"] = json.dumps(pages_meta, ensure_ascii=False, indent=2).encode("utf-8")

# Thêm 5 page.json
for pid, dname in pages:
    page_data = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json",
        "name": pid,
        "displayName": dname,
        "displayOption": "FitToPage",
        "height": 1080,
        "width": 1920
    }
    files[f"Report/definition/pages/{pid}/page.json"] = json.dumps(page_data, ensure_ascii=False, indent=2).encode("utf-8")

with zipfile.ZipFile(dst, "w", compression=zipfile.ZIP_DEFLATED) as zout:
    for fname, data in files.items():
        zout.writestr(fname, data)

print(f"[OK] Generated {dst.name} with 5 standardized pages successfully!")
