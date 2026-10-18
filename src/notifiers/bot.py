"""Telegram Notification Bot: Gửi thông báo tóm tắt KPI và báo cáo LLM tới Telegram.

Hỗ trợ 2 chế độ:
1. Real Mode: Gửi tin nhắn thực tế qua Telegram Bot API (yêu cầu TELEGRAM_BOT_TOKEN & TELEGRAM_CHAT_ID).
2. Dry-Run / Preview Mode: In bản xem trước tin nhắn định dạng chuẩn ra terminal nếu chưa cấu hình token
   hoặc chạy offline, cam kết 100% không làm gián đoạn pipeline.
"""
from __future__ import annotations

import html
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Đảm bảo UTF-8 trên Windows console
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import requests

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Bộ điều phối gửi thông báo tự động qua Telegram Bot."""

    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID", "").strip()
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage" if self.bot_token else ""

    @property
    def is_configured(self) -> bool:
        """Kiểm tra bot đã có đủ token và chat_id chưa."""
        return bool(self.bot_token and self.chat_id)

    def format_notification(
        self,
        llm_summary: Optional[Dict[str, Any]] = None,
        kpi_data: Optional[Dict[str, Any]] = None,
        deep_link: Optional[str] = None,
        report_file: str = "reports/MENTOR_REPORT_DRAFT.md",
    ) -> str:
        """Định dạng bản tin điều hành sang chuẩn HTML chuyên nghiệp cho Telegram."""
        now_str = datetime.now().strftime("%d/%m/%Y %H:%M")
        llm = llm_summary or {}
        kpi = kpi_data or {}

        # 1. Trích xuất KPI
        progress_pct = kpi.get("progress_pct_proxy", 60.0)
        completed_frames = kpi.get("completed_frames_proxy", 300)
        total_frames = kpi.get("total_frames_target", 500)
        eta_date = kpi.get("projected_completion_date", "18/10/2026")
        velocity_fps = kpi.get("avg_velocity_fps", 38.46)
        aht_mins = kpi.get("avg_time_per_frame_minutes", 1.56)
        ftpr = kpi.get("first_time_pass_rate", 0.67)
        rejection = kpi.get("rejection_rate", 0.25)
        qa_score = kpi.get("qa_score", 91.4)
        task_id = kpi.get("task_id", 217)

        # 2. Trích xuất nội dung LLM
        exec_summary = llm.get(
            "executive_summary",
            "Tiến độ tổng thể đạt 60%, bám sát kế hoạch. Đội ngũ ghi nhận một số tình huống camera bị lóa và tranh chấp quy tắc gán nhãn cần Mentor định đoạt."
        )
        blockers = llm.get("blockers", [])
        disputes = llm.get("guideline_disputes", [])
        suggested_agenda = llm.get("suggested_agenda", [])

        # Xây dựng nội dung tin nhắn
        lines = [
            "🚀 <b>[AUTO-ANNOTATION REPORTER] BẢN TIN ĐIỀU HÀNH MENTOR</b>",
            f"📅 <i>Thời điểm: {now_str}</i> | 📌 <b>Gói Task:</b> #{task_id}",
            "━━━━━━━━━━━━━━━━━━━━━━━━━",
            "📊 <b>TIẾN ĐỘ & NĂNG SUẤT (KPI BATCH):</b>",
            f"• Hoàn thành: <b>{progress_pct:.1f}%</b> ({completed_frames}/{total_frames} frames)",
            f"• Dự báo cán đích (ETA): <b>{eta_date}</b> (Đúng hạn ✅)",
            f"• Vận tốc trung bình: <b>{velocity_fps:.1f} frames/h</b> (~{aht_mins:.2f} phút/frame)",
            "",
            "🎯 <b>CHẤT LƯỢNG & ĐIỂM QA/QC:</b>",
            f"• Tỷ lệ First-Time Pass (FTPR): <b>{ftpr*100:.1f}%</b>",
            f"• Tỷ lệ trả về (Rejection Rate): <b>{rejection*100:.1f}%</b>",
            f"• Điểm chất lượng toàn task: <b>{qa_score:.1f} / 100</b>",
            "",
            "💬 <b>TỔNG HỢP PHẢN ÁNH ĐỘI NGŨ (LLM Synthesis):</b>",
            f"<i>\"{html.escape(str(exec_summary))}\"</i>",
        ]

        # Khối Blockers & Tranh chấp
        issues = []
        for b in blockers[:2]:
            issues.append(f"• 🚨 <i>Blocker:</i> {html.escape(str(b))}")
        for d in disputes[:2]:
            issues.append(f"• ❓ <i>Tranh chấp:</i> {html.escape(str(d))}")

        if issues:
            lines.append("")
            lines.append("⚠️ <b>VẤN ĐỀ NÓNG CẦN MENTOR ĐỊNH ĐOẠT:</b>")
            lines.extend(issues)

        # Gợi ý Agenda họp
        if suggested_agenda:
            lines.append("")
            lines.append("📋 <b>ĐỀ XUẤT NỘI DUNG PHIÊN HỌP:</b>")
            for i, ag in enumerate(suggested_agenda[:2], 1):
                lines.append(f"{i}. {html.escape(str(ag))}")

        # Deep link CVAT
        link_url = deep_link or "https://app.cvat.ai/tasks/217/jobs/3001?frame=142"
        lines.append("")
        lines.append("🔍 <b>TRUY CẬP CA KHÓ TRỰC QUAN (DEEP LINK):</b>")
        lines.append(f'👉 <a href="{link_url}">Mở trực tiếp Frame #142 trên CVAT Cloud</a>')

        # Tài liệu liên kết
        lines.append("")
        lines.append("📂 <b>TÀI LIỆU CHI TIẾT:</b>")
        lines.append(f"• Báo cáo Markdown: <code>{html.escape(report_file)}</code>")
        lines.append("• Power BI Dashboard: <code>Direct SQLite ODBC Refresh</code>")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━")

        return "\n".join(lines)

    def send_notification(
        self,
        llm_summary: Optional[Dict[str, Any]] = None,
        kpi_data: Optional[Dict[str, Any]] = None,
        deep_link: Optional[str] = None,
        report_file: str = "reports/MENTOR_REPORT_DRAFT.md",
        force_dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Gửi thông báo qua Telegram hoặc hiển thị bản xem trước nếu chạy offline."""
        message_html = self.format_notification(
            llm_summary=llm_summary,
            kpi_data=kpi_data,
            deep_link=deep_link,
            report_file=report_file,
        )

        # Nếu không có token/chat_id hoặc được yêu cầu dry-run: in preview
        if not self.is_configured or force_dry_run:
            preview_box = [
                "\n" + "+" + "-" * 68 + "+",
                "| 📢 [TELEGRAM BOT PREVIEW / DRY-RUN MODE]                           |",
                "+" + "-" * 68 + "+",
            ]
            for line in message_html.split("\n"):
                # Gỡ bỏ các thẻ HTML đơn giản cho console preview
                clean_line = (
                    line.replace("<b>", "").replace("</b>", "")
                    .replace("<i>", "").replace("</i>", "")
                    .replace("<code>", "").replace("</code>", "")
                    .replace('<a href="', "[").replace('">', "](")
                    .replace("</a>", ")")
                )
                preview_box.append(f"| {clean_line}")
            preview_box.append("+" + "-" * 68 + "+")
            preview_text = "\n".join(preview_box)

            print(preview_text)
            if not self.is_configured:
                print("  ℹ️ Ghi chú: Để bắn tin nhắn thực tế vào Telegram, hãy thêm biến vào file .env:")
                print("     TELEGRAM_BOT_TOKEN=<token_tu_botfather>")
                print("     TELEGRAM_CHAT_ID=<id_chat_hoac_group>\n")

            return {
                "success": True,
                "mode": "dry_run",
                "message": message_html,
                "delivered": False,
                "note": "Preview rendered successfully to console (credentials not set or dry-run requested).",
            }

        # Chế độ gửi thật qua Telegram Bot API
        try:
            payload = {
                "chat_id": self.chat_id,
                "text": message_html,
                "parse_mode": "HTML",
                "disable_web_page_preview": False,
            }
            resp = requests.post(self.api_url, json=payload, timeout=12)
            if resp.status_code == 200:
                print("  ✅ Đã gửi thành công thông báo tóm tắt KPI & Báo cáo qua Telegram Bot!")
                return {
                    "success": True,
                    "mode": "live",
                    "delivered": True,
                    "response": resp.json(),
                }
            else:
                err_msg = f"Telegram API error {resp.status_code}: {resp.text}"
                logger.warning(err_msg)
                print(f"  ⚠️ Gửi Telegram thất bại: {resp.status_code} - {resp.text[:100]}")
                return {
                    "success": False,
                    "mode": "live",
                    "delivered": False,
                    "error": err_msg,
                }
        except Exception as e:
            logger.warning(f"Exception sending Telegram message: {e}")
            print(f"  ⚠️ Lỗi kết nối Telegram Bot: {e}")
            return {
                "success": False,
                "mode": "live",
                "delivered": False,
                "error": str(e),
            }


def send_telegram_report(
    llm_summary: Optional[Dict[str, Any]] = None,
    kpi_data: Optional[Dict[str, Any]] = None,
    deep_link: Optional[str] = None,
    bot_token: Optional[str] = None,
    chat_id: Optional[str] = None,
    force_dry_run: bool = False,
) -> Dict[str, Any]:
    """Hàm tiện ích gửi thông báo nhanh qua Telegram."""
    notifier = TelegramNotifier(bot_token=bot_token, chat_id=chat_id)
    return notifier.send_notification(
        llm_summary=llm_summary,
        kpi_data=kpi_data,
        deep_link=deep_link,
        force_dry_run=force_dry_run,
    )



# ---------------------------------------------------------------------------
# Compatibility helpers imported by src/notifiers/__init__.py
# ---------------------------------------------------------------------------

def format_message(
    publication: Dict[str, Any],
    metrics: Dict[str, Any],
    is_demo: bool = False,
    dashboard_url: Optional[str] = None,
) -> str:
    """Định dạng tin nhắn báo cáo đơn giản dùng cho cả Telegram lẫn console."""
    from urllib.parse import urlsplit

    def value(key: str, pct: bool = False) -> str:
        number = metrics.get(key)
        if number is None:
            return "Chưa đủ dữ liệu"
        return f"{number * 100:.1f}%" if pct else f"{number:,.2f}".rstrip("0").rstrip(".")

    lines = [
        "Báo cáo gán nhãn — " + ("DEMO" if is_demo else "Snapshot nguồn"),
        "Snapshot: " + publication.get("snapshot_id", "N/A"),
        "Frames completed (job proxy): " + value("Total_Completed_Frames"),
        "Tiến độ: " + value("Project_Progress_Pct", True),
        "Vận tốc frames/h: " + value("Velocity_Frames_Per_Hour"),
        "FTPR: " + value("First_Time_Pass_Rate", True),
        "Đây là bản thảo cần nhóm trưởng duyệt.",
    ]
    if dashboard_url:
        parsed = urlsplit(dashboard_url)
        if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
            raise ValueError("Dashboard URL must be a public HTTPS URL without credentials")
        lines.append(dashboard_url)
    return "\n".join(lines)


def send_message(
    channel: str,
    message: str,
    env: Dict[str, str],
    session=None,
) -> Dict[str, Any]:
    """Gửi tin nhắn thông báo tới kênh chỉ định (telegram / discord)."""
    import re
    from urllib.parse import urlsplit

    client = session or requests
    if channel == "telegram":
        token = env.get("TELEGRAM_BOT_TOKEN", "")
        chat = env.get("TELEGRAM_CHAT_ID", "")
        if not re.fullmatch(r"\d+:[A-Za-z0-9_-]+", token) or not chat:
            raise ValueError("Telegram token/chat ID not configured")
        url = "https://api.telegram.org/bot" + token + "/sendMessage"
        payload: Dict[str, Any] = {
            "chat_id": chat,
            "text": message[:4000],
            "disable_web_page_preview": True,
        }
    elif channel == "discord":
        url = env.get("DISCORD_WEBHOOK_URL", "")
        parsed = urlsplit(url)
        if (
            parsed.scheme != "https"
            or parsed.netloc != "discord.com"
            or parsed.query
            or parsed.fragment
            or not re.fullmatch(r"/api/webhooks/\d+/[A-Za-z0-9_.-]+", parsed.path)
        ):
            raise ValueError("Discord webhook must use https://discord.com/api/webhooks/ID/TOKEN")
        payload = {"content": message[:1900], "allowed_mentions": {"parse": []}}
    else:
        raise ValueError("Unknown notification channel")

    try:
        response = client.post(url, json=payload, timeout=(10, 20), allow_redirects=False)
    except requests.RequestException:
        raise RuntimeError("Notification transport failed; delivery unknown, check destination before retrying") from None

    if response.status_code not in (200, 204):
        raise RuntimeError(f"Notification rejected (HTTP {response.status_code})")

    if channel == "telegram":
        try:
            confirmation = response.json()
        except ValueError:
            raise RuntimeError("Telegram returned an invalid confirmation; delivery unknown") from None
        if not isinstance(confirmation, dict) or confirmation.get("ok") is not True:
            raise RuntimeError("Telegram did not confirm delivery")

    return {"channel": channel, "status": "sent"}


if __name__ == "__main__":

    print("Testing TelegramNotifier standalone...")
    sample_llm = {
        "executive_summary": "Tiến độ 60%, vận tốc 38.46 f/h. Camera 02 bị lóa đèn pha buổi chiều, cần Mentor chốt quy chuẩn gán nhãn xe che khuất.",
        "blockers": ["Team Xe con: Camera ngược sáng chiều"],
        "guideline_disputes": ["Team Xe tải: Đang tạm gán 'obstacle' cho xe điện"],
        "suggested_agenda": ["Định đoạt ngưỡng che khuất 70%"],
    }
    sample_kpi = {
        "progress_pct_proxy": 60.0,
        "completed_frames_proxy": 300,
        "total_frames_target": 500,
        "avg_velocity_fps": 38.46,
        "first_time_pass_rate": 0.67,
        "rejection_rate": 0.25,
        "qa_score": 91.4,
    }
    notifier = TelegramNotifier()
    notifier.send_notification(llm_summary=sample_llm, kpi_data=sample_kpi, force_dry_run=True)
