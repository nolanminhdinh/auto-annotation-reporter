"""Main Unified Orchestrator: Điều phối toàn trình End-to-End.

Luồng liên hoàn:
1. Ingestion / Snapshot Loading ->
2. Medallion Warehouse ETL (Bronze -> Silver -> Gold) ->
3. LLM Multi-Team Synthesis (Phân tích ngôn ngữ tự nhiên từ các tổ) ->
4. Markdown Report Rendering (Deep Link CVAT & Gợi ý Agenda) ->
5. Power BI Datasets Export (CSVs chuẩn UTF-8 BOM) ->
6. AI Report Agent Reconciliation & Executive Briefing.

Sử dụng:
    python src/main.py --mode offline --llm-summary --export-powerbi --verify
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

# Đảm bảo UTF-8 trên Windows console
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from src.generators.llm_summarizer import summarize_from_warehouse
from src.generators.markdown_generator import render_mentor_report
from src.generators.report_agent import ReportReaderAgent
from src.notifiers.bot import send_telegram_report
from src.storage.db_manager import DEFAULT_DB_PATH, export_gold_to_csv, get_connection
from src.storage.populate_warehouse import run_etl_to_database


def run_full_pipeline(
    mode: str = "offline",
    snapshot_dir: Optional[Path] = None,
    db_path: Optional[Path] = None,
    export_powerbi: bool = True,
    run_llm_summary: bool = True,
    run_verify: bool = True,
    show_brief: bool = True,
    notify: str = "none",
) -> int:
    """Điều phối toàn bộ quy trình từ ETL kho dữ liệu, LLM tóm tắt, xuất Power BI, kiểm toán Agent và gửi Bot."""
    target_db = db_path or DEFAULT_DB_PATH
    reports_dir = PROJECT_DIR / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_file = reports_dir / "MENTOR_REPORT_DRAFT.md"

    print("\n" + "=" * 70)
    print("🚀 [PIPELINE ORCHESTRATOR] KHỞI ĐỘNG HỆ THỐNG TỰ ĐỘNG HÓA TOÀN TRÌNH")
    print(f"🕒 Thời điểm: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"⚙️ Chế độ: {mode.upper()} | Database: {target_db.name}")
    print("=" * 70 + "\n")

    # -------------------------------------------------------------------------
    # BƯỚC 1: ETL KHO DỮ LIỆU MEDALLION (Bronze -> Silver -> Gold)
    # -------------------------------------------------------------------------
    print("📦 [1/5] Nạp dữ liệu vào Kho Medallion Warehouse...")
    try:
        run_etl_to_database(target_db)
        print("  ✓ Đã cập nhật thành công 3 tầng Bronze (Raw) -> Silver (Cleaned) -> Gold (Star Schema).\n")
    except Exception as e:
        print(f"  ❌ Lỗi nạp Database: {e}")
        return 1

    # -------------------------------------------------------------------------
    # BƯỚC 2: LLM MULTI-TEAM SUMMARIZER
    # -------------------------------------------------------------------------
    llm_result = None
    if run_llm_summary:
        print("🧠 [2/5] Động cơ LLM phân tích phản ánh từ các tổ gán nhãn...")
        try:
            llm_result = summarize_from_warehouse(db_path=target_db)
            src_mode = "Google Gemini API" if llm_result.get("source") == "gemini_api" else "Heuristic Rule-based Engine"
            print(f"  ✓ Đã trích xuất {len(llm_result.get('blockers', []))} blockers, {len(llm_result.get('guideline_disputes', []))} tranh chấp (Engine: {src_mode}).\n")
        except Exception as e:
            print(f"  ⚠️ LLM Summarizer warning: {e}\n")

    # -------------------------------------------------------------------------
    # BƯỚC 3: RENDER BÁO CÁO MARKDOWN KÈM DEEP LINK CVAT & LLM SYNTHESIS
    # -------------------------------------------------------------------------
    print("📄 [3/5] Khởi tạo bản nháp MENTOR_REPORT_DRAFT.md...")
    try:
        report_data_file = PROJECT_DIR / "sample_data" / "report_data.json"
        normalized_data = {}
        if report_data_file.exists():
            normalized_data = json.loads(report_data_file.read_text(encoding="utf-8"))

        if llm_result:
            normalized_data["llm_summary"] = llm_result

        markdown_content = render_mentor_report(normalized_data)
        report_file.write_text(markdown_content, encoding="utf-8")
        print(f"  ✓ Đã ghi bản nháp báo cáo chuẩn 4 mục ra: {report_file}\n")
    except Exception as e:
        print(f"  ❌ Lỗi render báo cáo: {e}\n")
        return 1

    # -------------------------------------------------------------------------
    # BƯỚC 4: XUẤT CSV CHO POWER BI
    # -------------------------------------------------------------------------
    if export_powerbi:
        print("📊 [4/5] Xuất các bảng Star Schema CSV cho Power BI...")
        try:
            powerbi_dir = PROJECT_DIR / "powerbi" / "data"
            pbi_files = export_gold_to_csv(powerbi_dir, db_path=target_db)
            print(f"  ✓ Đã xuất {len(pbi_files)} file CSV chuẩn UTF-8 BOM sang {powerbi_dir}\n")
        except Exception as e:
            print(f"  ⚠️ Lỗi xuất CSV Power BI: {e}\n")

    # -------------------------------------------------------------------------
    # BƯỚC 5: AI REPORT AGENT RECONCILIATION & EXECUTIVE BRIEFING
    # -------------------------------------------------------------------------
    if run_verify or show_brief:
        print("🤖 [5/5] Kích hoạt AI Report Agent đối soát và tóm lược điều hành...")
        agent = ReportReaderAgent(report_path=report_file, db_path=target_db)

        if run_verify:
            reconciliation = agent.verify_reconciliation()
            status_tag = "HOÀN TOÀN NHẤT QUÁN ✅" if reconciliation["overall_consistent"] else "CÓ ĐIỂM LƯU Ý ⚠️"
            print(f"  • Đối soát dữ liệu (Reconciliation): {status_tag}")
            for c in reconciliation["checks"]:
                mark = "✓" if c["status"] == "PASS" else ("!" if c["status"] == "WARNING" else "ℹ")
                print(f"    [{mark}] {c['target']}: {c['detail']}")
            print("")

        if show_brief:
            briefing = agent.generate_executive_briefing()
            print("\n" + briefing + "\n")

    # -------------------------------------------------------------------------
    # BƯỚC 6: BẮN THÔNG BÁO BOT TELEGRAM (NẾU CÓ YÊU CẦU HOẶC CHẠY THEO LỊCH)
    # -------------------------------------------------------------------------
    if notify == "telegram":
        print("📢 [6/6] Khởi tạo và phát thông báo qua Telegram Bot...")
        try:
            kpi_context: Dict[str, Any] = {}
            with get_connection(target_db) as conn:
                row_bp = conn.execute("SELECT * FROM gold_mart_batch_progress ORDER BY as_of DESC LIMIT 1").fetchone()
                if row_bp:
                    kpi_context.update(dict(row_bp))
                row_qa = conn.execute("SELECT * FROM gold_mart_qa_metrics ORDER BY as_of DESC LIMIT 1").fetchone()
                if row_qa:
                    kpi_context.update(dict(row_qa))

            res = send_telegram_report(
                llm_summary=llm_result,
                kpi_data=kpi_context,
                deep_link="https://app.cvat.ai/tasks/217/jobs/3001?frame=142",
            )
            if res.get("mode") == "dry_run":
                print("  ✓ Đã hiển thị bản xem trước tin nhắn Telegram định dạng chuẩn (Dry-run Mode).\n")
            elif res.get("success"):
                print("  ✓ Đã phát thành công tin nhắn báo cáo điều hành tới Telegram Group/Leader.\n")
        except Exception as e:
            print(f"  ⚠️ Lỗi phát thông báo Telegram: {e}\n")

    print("=" * 70)
    print("🎉 [HOÀN TẤT] PIPELINE TOÀN TRÌNH ĐÃ THỰC THI THÀNH CÔNG!")
    print("=" * 70 + "\n")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Auto Annotation Reporter - Unified Main Pipeline")
    parser.add_argument("--mode", choices=["offline", "online"], default="offline", help="Chế độ chạy (offline/online)")
    parser.add_argument("--snapshot", type=Path, help="Đường dẫn snapshot cụ thể nếu chạy offline")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH, help="Đường dẫn SQLite database")
    parser.add_argument("--export-powerbi", action="store_true", default=True, help="Xuất các bảng CSV cho Power BI")
    parser.add_argument("--llm-summary", action="store_true", default=True, help="Phân tích báo cáo ngôn ngữ tự nhiên bằng LLM")
    parser.add_argument("--verify", action="store_true", default=True, help="Chạy đối soát tính nhất quán bằng AI Agent")
    parser.add_argument("--notify", choices=["telegram", "none"], default="none", help="Phát thông báo tóm tắt qua bot (telegram/none)")
    parser.add_argument("--no-brief", action="store_true", help="Không in bản tóm tắt ra màn hình")
    args = parser.parse_args()

    return run_full_pipeline(
        mode=args.mode,
        snapshot_dir=args.snapshot,
        db_path=args.db,
        export_powerbi=args.export_powerbi,
        run_llm_summary=args.llm_summary,
        run_verify=args.verify,
        show_brief=not args.no_brief,
        notify=args.notify,
    )


if __name__ == "__main__":
    sys.exit(main())
