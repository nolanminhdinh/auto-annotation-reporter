"""Prepare notification previews; remote sending is explicit and never retried automatically."""
from __future__ import annotations

from urllib.parse import urlsplit
import re
import requests


def format_message(publication, metrics, is_demo=False, dashboard_url=None):
    def value(key, pct=False):
        number = metrics.get(key)
        if number is None:
            return 'Chưa đủ dữ liệu'
        return f'{number*100:.1f}%' if pct else f'{number:,.2f}'.rstrip('0').rstrip('.')
    lines = [
        'Báo cáo gán nhãn — ' + ('DEMO' if is_demo else 'Snapshot nguồn'),
        'Snapshot: ' + publication['snapshot_id'],
        'Frames completed (job proxy): ' + value('Total_Completed_Frames'),
        'Tiến độ: ' + value('Project_Progress_Pct', True),
        'Vận tốc frames/h: ' + value('Velocity_Frames_Per_Hour'),
        'FTPR: ' + value('First_Time_Pass_Rate', True),
        'Đây là bản thảo cần nhóm trưởng duyệt.',
    ]
    if dashboard_url:
        parsed = urlsplit(dashboard_url)
        if parsed.scheme != 'https' or not parsed.netloc or parsed.username or parsed.password:
            raise ValueError('Dashboard URL must be a public HTTPS URL without credentials')
        lines.append(dashboard_url)
    return '\n'.join(lines)


def send_message(channel, message, env, session=None):
    client = session or requests
    if channel == 'telegram':
        token = env.get('TELEGRAM_BOT_TOKEN', '')
        chat = env.get('TELEGRAM_CHAT_ID', '')
        if not re.fullmatch(r'\d+:[A-Za-z0-9_-]+', token) or not chat:
            raise ValueError('Telegram token/chat ID not configured')
        url = 'https://api.telegram.org/bot' + token + '/sendMessage'
        payload = {'chat_id': chat, 'text': message[:4000], 'disable_web_page_preview': True}
    elif channel == 'discord':
        url = env.get('DISCORD_WEBHOOK_URL', '')
        parsed = urlsplit(url)
        if parsed.scheme != 'https' or parsed.netloc != 'discord.com' or parsed.query or parsed.fragment or not re.fullmatch(r'/api/webhooks/\d+/[A-Za-z0-9_.-]+', parsed.path):
            raise ValueError('Discord webhook must use https://discord.com/api/webhooks/ID/TOKEN')
        payload = {'content': message[:1900], 'allowed_mentions': {'parse': []}}
    else:
        raise ValueError('Unknown notification channel')
    try:
        response = client.post(url, json=payload, timeout=(10, 20), allow_redirects=False)
    except requests.RequestException as error:
        raise RuntimeError('Notification transport failed; delivery unknown, check destination before retrying') from None
    if response.status_code not in (200, 204):
        raise RuntimeError(f'Notification rejected (HTTP {response.status_code})')
    if channel == 'telegram':
        try:
            confirmation = response.json()
        except ValueError:
            raise RuntimeError('Telegram returned an invalid confirmation; delivery unknown') from None
        if not isinstance(confirmation, dict) or confirmation.get('ok') is not True:
            raise RuntimeError('Telegram did not confirm delivery')
    return {'channel': channel, 'status': 'sent'}
