"""Portable Desktop settings. No credentials belong in this configuration."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / 'config/desktop.local.json'
DEFAULTS = {'version': 1, 'mode': 'demo', 'port': 55432, 'refresh_seconds': 10,
            'completed_jobs': 10, 'snapshot': None, 'task_id': None, 'repo': None,
            'operations': None, 'team_reports': None}


def load_settings(path=None, overrides=None):
    explicit=path is not None
    path = Path(path or DEFAULT_CONFIG)
    if not path.is_absolute(): path = ROOT / path
    if explicit and not path.is_file(): raise ValueError('Desktop configuration file not found')
    supplied = json.loads(path.read_text(encoding='utf-8-sig')) if path.exists() else {}
    if not isinstance(supplied, dict) or set(supplied) - set(DEFAULTS):
        raise ValueError('Invalid Desktop configuration keys; see config/desktop.example.json')
    settings = {**DEFAULTS, **supplied, **{k: v for k, v in (overrides or {}).items() if v is not None}}
    if type(settings['version']) is not int or settings['version'] != 1 or settings['mode'] not in ('demo', 'offline', 'live'):
        raise ValueError('Use config version 1 and mode demo, offline or live')
    for key, low, high in [('port', 1024, 65535), ('refresh_seconds', 1, 3600), ('completed_jobs', 0, 15)]:
        if type(settings[key]) is not int or not low <= settings[key] <= high:
            raise ValueError(f'{key} must be an integer between {low} and {high}')
    if settings['task_id'] is not None and (type(settings['task_id']) is not int or settings['task_id'] <= 0):
        raise ValueError('task_id must be a positive integer')
    if settings['repo'] is not None and (not isinstance(settings['repo'], str) or not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', settings['repo'])):
        raise ValueError('repo must be OWNER/REPO')
    for key in ('snapshot', 'operations', 'team_reports'):
        value = settings[key]
        if value is not None:
            if not isinstance(value, str) or not value.strip(): raise ValueError(f'{key} must be a path')
            target = Path(value).expanduser()
            settings[key] = str((target if target.is_absolute() else ROOT / target).resolve())
    return settings
