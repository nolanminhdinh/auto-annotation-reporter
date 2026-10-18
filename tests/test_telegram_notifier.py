"""Unit Tests: Telegram Notification Bot."""
import os
import unittest
from unittest.mock import MagicMock, patch

from src.notifiers.bot import TelegramNotifier, send_telegram_report


class TestTelegramNotifier(unittest.TestCase):
    """Kiểm thử tính năng định dạng và gửi tin nhắn Telegram."""

    def setUp(self):
        self.sample_llm = {
            "executive_summary": "Tiến độ 60%, vận tốc 38.46 f/h. Camera 02 bị lóa đèn pha buổi chiều.",
            "blockers": ["Team Xe con: Camera ngược sáng chiều"],
            "guideline_disputes": ["Team Xe tải: Đang tạm gán 'obstacle' cho xe điện"],
            "suggested_agenda": ["Định đoạt ngưỡng che khuất 70%"],
        }
        self.sample_kpi = {
            "progress_pct_proxy": 60.0,
            "completed_frames_proxy": 300,
            "total_frames_target": 500,
            "projected_completion_date": "2026-10-18",
            "avg_velocity_fps": 38.46,
            "avg_time_per_frame_minutes": 1.56,
            "first_time_pass_rate": 0.67,
            "rejection_rate": 0.25,
            "qa_score": 91.4,
            "task_id": 217,
        }

    def test_format_notification_contains_key_elements(self):
        """Tin nhắn phải chứa đầy đủ KPI, LLM summary, Deep Link và escape HTML an toàn."""
        notifier = TelegramNotifier()
        msg = notifier.format_notification(
            llm_summary=self.sample_llm,
            kpi_data=self.sample_kpi,
            deep_link="https://app.cvat.ai/tasks/217/jobs/3001?frame=142",
        )
        self.assertIn("60.0%", msg)
        self.assertIn("38.5 frames/h", msg)
        self.assertIn("91.4 / 100", msg)
        self.assertIn("Camera 02 bị lóa đèn pha", msg)
        self.assertIn("https://app.cvat.ai/tasks/217/jobs/3001?frame=142", msg)
        self.assertIn("reports/MENTOR_REPORT_DRAFT.md", msg)

    def test_dry_run_mode_when_unconfigured(self):
        """Khi không có TELEGRAM_BOT_TOKEN, bot tự động chạy ở chế độ dry-run mà không ném exception."""
        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "", "TELEGRAM_CHAT_ID": ""}):
            notifier = TelegramNotifier(bot_token="", chat_id="")
            res = notifier.send_notification(
                llm_summary=self.sample_llm,
                kpi_data=self.sample_kpi,
            )
            self.assertTrue(res["success"])
            self.assertEqual(res["mode"], "dry_run")
            self.assertFalse(res["delivered"])

    @patch("src.notifiers.bot.requests.post")
    def test_live_send_success(self, mock_post):
        """Khi có token và chat_id, bot gọi đúng Telegram Bot API và trả về success."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"ok": True, "result": {"message_id": 12345}}
        mock_post.return_value = mock_resp

        notifier = TelegramNotifier(bot_token="123456:ABC-DEF", chat_id="-100987654321")
        res = notifier.send_notification(
            llm_summary=self.sample_llm,
            kpi_data=self.sample_kpi,
            force_dry_run=False,
        )
        self.assertTrue(res["success"])
        self.assertEqual(res["mode"], "live")
        self.assertTrue(res["delivered"])
        mock_post.assert_called_once()

    @patch("src.notifiers.bot.requests.post")
    def test_live_send_api_error_handled_gracefully(self, mock_post):
        """Khi Telegram API trả về lỗi (400, 403), bot bắt lỗi an toàn và không làm sập pipeline."""
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.text = '{"ok":false,"description":"Bad Request: chat not found"}'
        mock_post.return_value = mock_resp

        notifier = TelegramNotifier(bot_token="123456:ABC-DEF", chat_id="-100987654321")
        res = notifier.send_notification(
            llm_summary=self.sample_llm,
            kpi_data=self.sample_kpi,
            force_dry_run=False,
        )
        self.assertFalse(res["success"])
        self.assertEqual(res["mode"], "live")
        self.assertFalse(res["delivered"])


if __name__ == "__main__":
    unittest.main()
