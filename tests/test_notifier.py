import unittest
from unittest.mock import Mock
import requests
from src.notifiers.bot import format_message, send_message


class NotificationTests(unittest.TestCase):
    def test_preview_preserves_missing_data_and_demo_label(self):
        message=format_message({'snapshot_id':'demo'}, {'Total_Completed_Frames':100,'First_Time_Pass_Rate':None},True)
        self.assertIn('DEMO',message)
        self.assertIn('Chưa đủ dữ liệu',message)
        self.assertNotIn('None',message)

    def test_config_required_before_send(self):
        session=Mock()
        with self.assertRaises(ValueError):send_message('telegram','test',{},session)
        session.post.assert_not_called()

    def test_telegram_payload_is_plain_text(self):
        session=Mock();session.post.return_value.status_code=200;session.post.return_value.json.return_value={'ok':True}
        result=send_message('telegram','<b>demo</b>',{'TELEGRAM_BOT_TOKEN':'123:fake_key','TELEGRAM_CHAT_ID':'test'},session)
        self.assertEqual(result['status'],'sent')
        self.assertNotIn('parse_mode',session.post.call_args.kwargs['json'])
        self.assertFalse(session.post.call_args.kwargs['allow_redirects'])

    def test_discord_disables_mentions(self):
        session=Mock();session.post.return_value.status_code=204
        send_message('discord','@everyone',{'DISCORD_WEBHOOK_URL':'https://discord.com/api/webhooks/123/fake-key'},session)
        self.assertEqual(session.post.call_args.kwargs['json']['allowed_mentions'],{'parse':[]})

    def test_arbitrary_webhook_destination_rejected(self):
        with self.assertRaises(ValueError):send_message('discord','test',{'DISCORD_WEBHOOK_URL':'https://example.org/api/webhooks/123/token'},Mock())

    def test_http_failure_not_reported_as_sent(self):
        session=Mock();session.post.return_value.status_code=403
        with self.assertRaises(RuntimeError):send_message('telegram','test',{'TELEGRAM_BOT_TOKEN':'123:fake_key','TELEGRAM_CHAT_ID':'test'},session)

    def test_transport_timeout_no_retry_or_secret_leak(self):
        session=Mock();session.post.side_effect=requests.Timeout('secret-token')
        with self.assertRaises(RuntimeError) as result:send_message('telegram','test',{'TELEGRAM_BOT_TOKEN':'123:fake_key','TELEGRAM_CHAT_ID':'test'},session)
        self.assertNotIn('secret-token',str(result.exception))
        self.assertEqual(session.post.call_count,1)

    def test_dashboard_credentials_not_in_preview(self):
        with self.assertRaises(ValueError):format_message({'snapshot_id':'demo'},{},dashboard_url='https://user:secret@example.org/report')


if __name__=='__main__':unittest.main()
