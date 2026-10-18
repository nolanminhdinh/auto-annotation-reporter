"""Publish an existing snapshot into the canonical reporting warehouse.

python -m src.storage.populate_warehouse sample_data
"""
import argparse
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from src.reporting_pipeline import DEFAULT_DB,publish_snapshot
from src.main import frame_size

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('snapshot',type=Path)
    p.add_argument('--db',type=Path,default=DEFAULT_DB)
    p.add_argument('--output-dir',type=Path,default=ROOT/'data'/'processed')
    p.add_argument('--frame-size',type=frame_size)
    a=p.parse_args()
    print(json.dumps(publish_snapshot(a.snapshot,a.db,a.output_dir,a.frame_size),ensure_ascii=False,indent=2))

if __name__=='__main__': main()
