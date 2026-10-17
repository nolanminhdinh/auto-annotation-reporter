"""Run the local synthetic pipeline and optionally open the native Power BI report."""
from __future__ import annotations
import argparse
import os
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--open-report',action='store_true')
    parser.add_argument('--rebuild-project',action='store_true',help='Regenerate PBIP design from template')
    args=parser.parse_args()
    from src.reporting_pipeline import publication_lock
    from powerbi.create_demo_snapshot import create_demo
    from src.main import main as run
    os.chdir(ROOT)
    try:
        with publication_lock(ROOT/'data'/'.demo-run.lock'):
            source=create_demo()
            code=run(['--mode','offline','--snapshot',str(source),'--llm-summary','--notify','preview','--session','Power BI Demo'])
            if code: return code
            project=ROOT/'powerbi/project_desktop/AnnotationReporter.pbip'
            if args.rebuild_project or not project.exists():
                from powerbi.build_project import build
                build(project.parent)
            report=ROOT/'powerbi/AnnotationReporter_Desktop.pbix'
            if args.rebuild_project or not report.exists(): report=project
            print('Latest run receipt: '+str(ROOT/'data/runs/latest.json'))
            print('Report: '+str(report))
            print('Desktop: select Refresh, wait for completion, then Save.')
            if args.open_report:
                if os.name!='nt':
                    print('Open the report on a Windows machine with Power BI Desktop.',file=sys.stderr)
                    return 2
                try:
                    # Read/write open is only a sharing probe; no bytes are changed.
                    # Desktop holds the PBIX against writes while it is in use.
                    with report.open('r+b'): pass
                except PermissionError:
                    print('Report is already in use or read-only. Use its existing Desktop window; no duplicate was opened.')
                    return 0
                try: os.startfile(str(report))
                except OSError:
                    print('Data is ready, but the report could not open automatically. Open the path above in Power BI Desktop.',file=sys.stderr)
                    return 2
        return 0
    except (OSError,ValueError) as error:
        print('Demo did not complete: '+str(error),file=sys.stderr)
        return 1


if __name__=='__main__': raise SystemExit(main())
