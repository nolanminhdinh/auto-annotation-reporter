"""Main pipeline runner: Extracts data from CVAT & GitHub, verifies cross-system links, and generates mentor reports."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Dict, Optional

from dotenv import load_dotenv

# Ensure utf-8 output on Windows consoles
try:
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
    if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
        sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# Ensure 'src' is in python search path
SRC_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SRC_DIR.parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from src.extractors.cvat_extractor import CVATExtractor
from src.extractors.github_extractor import GitHubExtractor
from src.generators.markdown_generator import render_mentor_report
from src.processors.normalizer import normalize_snapshot


def write_json_file(file_path: Path, payload: Any) -> None:
    """Save payload to a UTF-8 JSON file formatted cleanly."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def run_pipeline(
    task_id: Optional[int] = None,
    repo: Optional[str] = None,
    session_name: Optional[str] = None,
    output_dir: Optional[Path] = None,
    offline_snapshot: Optional[Path] = None,
    snapshot_folder: Optional[Path] = None,
) -> int:
    """Run full automated sync pipeline."""
    load_dotenv(PROJECT_DIR / ".env")

    # Mode 1: Offline Snapshot Replay / Testing
    if offline_snapshot is not None:
        if not offline_snapshot.exists():
            print(f"❌ Error: Offline snapshot path does not exist: {offline_snapshot}")
            return 1

        print(f"🔄 Running offline pipeline from snapshot: {offline_snapshot}")
        manifest = json.loads((offline_snapshot / "manifest.json").read_text(encoding="utf-8"))
        
        cvat_file = offline_snapshot / "cvat.json"
        cvat_data = json.loads(cvat_file.read_text(encoding="utf-8")) if cvat_file.exists() else None

        github_file = offline_snapshot / "github.json"
        github_data = json.loads(github_file.read_text(encoding="utf-8")) if github_file.exists() else None

        links_file = offline_snapshot / "links.json"
        links_data = json.loads(links_file.read_text(encoding="utf-8")) if links_file.exists() else []

        normalized = normalize_snapshot(
            manifest=manifest,
            cvat_data=cvat_data,
            github_data=github_data,
            links_data=links_data,
            snapshot_dir=offline_snapshot,
            session_name=session_name or manifest.get("mentor_session") or "OFFLINE TEST SESSION",
        )

        out_json = offline_snapshot / "report_data.json"
        write_json_file(out_json, normalized)

        report_md = render_mentor_report(normalized)
        out_md = offline_snapshot / "MENTOR_REPORT_DRAFT.md"
        out_md.write_text(report_md, encoding="utf-8")

        print(f"✅ Generated JSON: {out_json}")
        print(f"✅ Generated Markdown Draft: {out_md}")
        return 0

    # Mode 2: Live API Synchronization
    resolved_task_id = task_id
    if resolved_task_id is None:
        try:
            resolved_task_id = int(os.getenv("CVAT_TASK_ID", ""))
        except ValueError:
            pass

    resolved_repo = repo or os.getenv("GITHUB_REPO")
    cvat_token = os.getenv("CVAT_TOKEN", "").strip()
    cvat_host = os.getenv("CVAT_HOST", "https://app.cvat.ai").rstrip("/")
    cvat_org = os.getenv("CVAT_ORG")
    github_token = os.getenv("GITHUB_TOKEN", "").strip()

    if not resolved_task_id or resolved_task_id <= 0:
        print("❌ Error: Missing or invalid CVAT_TASK_ID. Specify via --task-id or .env")
        return 1

    if not resolved_repo or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", resolved_repo):
        print("❌ Error: Missing or invalid GITHUB_REPO. Specify OWNER/REPO via --repo or .env")
        return 1

    if not cvat_token or cvat_token.startswith("your_"):
        print("❌ Error: CVAT_TOKEN is required in .env")
        return 1

    now_utc = datetime.now(timezone.utc)
    target_folder = snapshot_folder or ((output_dir or (PROJECT_DIR / "data" / "raw")) / now_utc.strftime("%Y%m%dT%H%M%S%fZ"))
    target_folder.mkdir(parents=True, exist_ok=True)

    manifest = {
        "schema_version": 1,
        "started_at": now_utc.isoformat(),
        "scope": {
            "task_id": resolved_task_id,
            "repo": resolved_repo,
            "cvat_host": cvat_host,
            "org": cvat_org,
        },
        "sources": {},
    }

    # Initialize Extractors
    cvat_ext = CVATExtractor(host=cvat_host, token=cvat_token, org=cvat_org)
    gh_ext = GitHubExtractor(token=github_token)

    # 1. Fetch CVAT
    print(f"📡 Extracting CVAT Task {resolved_task_id} from {cvat_host}...")
    cvat_start = datetime.now(timezone.utc).isoformat()
    cvat_payload: Optional[Dict[str, Any]] = None
    try:
        cvat_payload = cvat_ext.extract_snapshot(resolved_task_id)
        write_json_file(target_folder / "cvat.json", cvat_payload)
        manifest["sources"]["cvat"] = {
            "status": "success",
            "file": "cvat.json",
            "started_at": cvat_start,
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "counts": {k: len(v) if isinstance(v, list) else 1 for k, v in cvat_payload.items() if v is not None},
            "annotations": {
                "successful_jobs": sum(1 for r in cvat_payload.get("annotations", []) if r.get("status") == "success"),
                "failed_jobs": sum(1 for r in cvat_payload.get("annotations", []) if r.get("status") == "failed"),
            },
            'optional_sources':cvat_payload.get('optional_sources',{}),
            'quality_reports_status':cvat_payload.get('quality_reports_data',{}).get('status','unavailable'),
        }
        print("  ✓ CVAT extraction succeeded.")
    except Exception as err:
        manifest["sources"]["cvat"] = {
            "status": "failed",
            "error_type": type(err).__name__,
            "error": str(err),
            "started_at": cvat_start,
            "finished_at": datetime.now(timezone.utc).isoformat(),
        }
        print(f"  ✗ CVAT extraction failed: {err}")

    # 2. Fetch GitHub
    print(f"📡 Extracting GitHub Issues from {resolved_repo}...")
    gh_start = datetime.now(timezone.utc).isoformat()
    gh_payload: Optional[Dict[str, Any]] = None
    try:
        gh_payload = gh_ext.extract_snapshot(resolved_repo)
        write_json_file(target_folder / "github.json", gh_payload)
        manifest["sources"]["github"] = {
            "status": "success",
            "file": "github.json",
            "started_at": gh_start,
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "counts": {k: len(v) if isinstance(v, list) else 1 for k, v in gh_payload.items()},
        }
        print("  ✓ GitHub extraction succeeded.")
    except Exception as err:
        manifest["sources"]["github"] = {
            "status": "failed",
            "error_type": type(err).__name__,
            "error": str(err),
            "started_at": gh_start,
            "finished_at": datetime.now(timezone.utc).isoformat(),
        }
        print(f"  ✗ GitHub extraction failed: {err}")

    # 3. Verify Links
    links_payload = []
    try:
        if gh_payload and "issues" in gh_payload:
            print("🔗 Verifying CVAT references in GitHub issues...")
            cvat_jobs = cvat_payload.get("jobs", []) if cvat_payload else []
            links_payload = gh_ext.link_issues(gh_payload["issues"], cvat_ext, cvat_jobs)
            write_json_file(target_folder / "links.json", links_payload)

            status_counts = {
                st: sum(1 for r in links_payload if r.get("status") == st)
                for st in ("verified", "mismatch", "unlinked", "invalid_reference", "verification_failed")
            }
            manifest["links"] = {"file": "links.json", "counts": status_counts}
            print(f"  ✓ Links verified: {status_counts}")
        else:
            manifest["links"] = {"status": "skipped", "reason": "GitHub source extraction failed"}
    finally:
        cvat_ext.close()
        gh_ext.client.close()

    manifest["finished_at"] = datetime.now(timezone.utc).isoformat()
    write_json_file(target_folder / "manifest.json", manifest)

    # 4. Normalize & Generate Report
    print("📝 Normalizing report data and rendering markdown...")
    normalized = normalize_snapshot(
        manifest=manifest,
        cvat_data=cvat_payload,
        github_data=gh_payload,
        links_data=links_payload,
        snapshot_dir=target_folder,
        session_name=session_name,
    )
    write_json_file(target_folder / "report_data.json", normalized)

    report_content = render_mentor_report(normalized)
    draft_file = target_folder / "MENTOR_REPORT_DRAFT.md"
    draft_file.write_text(report_content, encoding="utf-8")

    # Also copy to root reports/ if directory exists
    reports_dir = PROJECT_DIR / "reports"
    if reports_dir.exists():
        (reports_dir / "MENTOR_REPORT_DRAFT.md").write_text(report_content, encoding="utf-8")

    print(f"\n🎉 Pipeline completed successfully!")
    print(f"📂 Snapshot Folder: {target_folder}")
    print(f"📄 Report File: {draft_file}")

    has_fatal_failure = any(s.get("status") == "failed" for s in manifest["sources"].values())
    return 1 if has_fatal_failure else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-id", type=int, help="CVAT Task ID")
    parser.add_argument("--repo", help="GitHub repository in OWNER/REPO format")
    parser.add_argument("--session", help="Tên phiên họp Mentor hoặc đợt báo cáo")
    parser.add_argument("--output", type=Path, help="Thư mục xuất dữ liệu thô (mặc định: data/raw)")
    parser.add_argument("--offline", type=Path, help="Đường dẫn snapshot offline để chạy thử nghiệm")
    args = parser.parse_args()

    return run_pipeline(
        task_id=args.task_id,
        repo=args.repo,
        session_name=args.session,
        output_dir=args.output,
        offline_snapshot=args.offline,
    )


if __name__ == "__main__":
    sys.exit(main())
