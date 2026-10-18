"""Local Desktop readiness report. Never prints credentials or calls remote APIs."""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]


def inspect_local(require_live=False):
    config = {**dotenv_values(ROOT / '.env'), **os.environ}
    def configured(name):
        value = (config.get(name) or '').strip()
        return bool(value and not value.lower().startswith(('your_', 'replace_', 'changeme')))
    parsed = urlsplit(config.get('CVAT_HOST') or '')
    host_ok = parsed.scheme in ('https', 'http') and bool(parsed.hostname) and not parsed.username and not parsed.password
    host_ok = bool(host_ok and not any(parsed.hostname == h or parsed.hostname.endswith('.' + h) for h in ('example.com', 'example.org', 'example.net')))
    task_ok = str(config.get('CVAT_TASK_ID') or '').isdigit() and int(config['CVAT_TASK_ID']) > 0
    repo_ok = bool(re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', config.get('GITHUB_REPO') or ''))
    checks = {'cvat_host_configured': host_ok, 'cvat_task_id_configured': task_ok,
              'cvat_token_configured': configured('CVAT_TOKEN'), 'github_repo_configured': repo_ok,
              'github_token_configured': configured('GITHUB_TOKEN'),
              'desktop_report_exists': any((ROOT / 'powerbi' / name).is_file() for name in ('AnnotationReporter_Desktop.pbix', 'AnnotationReporter.pbix'))}
    actions = []
    for key, advice in (
        ('cvat_host_configured', 'Điền CVAT_HOST của máy chủ thật vào .env.'),
        ('cvat_task_id_configured', 'Điền CVAT_TASK_ID là số nguyên dương trong .env.'),
        ('cvat_token_configured', 'Điền PAT vào CVAT_TOKEN trong .env; không gửi token qua chat.'),
        ('github_repo_configured', 'Điền GITHUB_REPO theo dạng OWNER/REPO vào .env.'),
    ):
        if require_live and not checks[key]: actions.append(advice)
    publication = {'available': False}
    pointer_path = ROOT / 'data/processed/current.json'
    if pointer_path.exists():
        try:
            pointer = json.loads(pointer_path.read_text(encoding='utf-8-sig'))
            bundle = (pointer_path.parent / pointer['relative_folder']).resolve()
            bundle.relative_to((pointer_path.parent / 'snapshots').resolve())
            with (bundle / 'report_status.csv').open(encoding='utf-8-sig', newline='') as stream:
                status = next(csv.DictReader(stream))
            with (bundle / 'kpi_reconciliation.csv').open(encoding='utf-8-sig', newline='') as stream:
                unavailable = [row['metric'] for row in csv.DictReader(stream) if not row['expected_value'].strip()]
            publication = {'available': True, 'snapshot_id': pointer['snapshot_id'], 'is_demo': status['is_demo'] == '1',
                           'as_of': status['as_of'], 'missing_metrics': unavailable,
                           'source_availability': {k: status[k] == '1' for k in ('reviews_available', 'defects_available', 'hours_available', 'gt_available')}}
            if publication['is_demo'] and require_live: actions.append('Báo cáo đang dùng DEMO; chạy live thành công trước khi trình bày số liệu thật.')
            if unavailable: actions.append('Bổ sung nguồn giờ làm/review/GT có xác nhận cho các KPI thiếu; giữ BLANK nếu chưa có.')
        except (ValueError, OSError, KeyError, StopIteration, TypeError):
            publication = {'available': False, 'error': 'Current CSV bundle missing or invalid'}
            actions.append('Chạy lại pipeline để tạo bộ CSV đầy đủ trước khi Refresh.')
    else:
        actions.append('Chạy RUN_DEMO.ps1 hoặc pipeline nguồn thật để tạo dữ liệu Power BI.')
    ready = all(checks[k] for k in ('cvat_host_configured', 'cvat_task_id_configured', 'cvat_token_configured', 'github_repo_configured'))
    desktop_ready=checks['desktop_report_exists'] and publication['available']
    if desktop_ready and not require_live: actions.append('Dữ liệu local đã sẵn sàng. Trong Power BI chọn Refresh rồi Save; demo không cần CVAT_TOKEN.')
    return {'created_at_utc': datetime.now(timezone.utc).isoformat(), 'target': 'Power BI Desktop',
            'desktop_data_ready': desktop_ready, 'requested_mode': 'live' if require_live else 'local',
            'live_configuration_ready': ready, 'remote_access_verified': False,
            'checks': checks, 'current_publication': publication, 'next_actions': actions,
            'note': 'Local configuration check only; configured credentials do not prove API access. GitHub token is optional for public repositories.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--require-live', action='store_true')
    args = parser.parse_args()
    result = inspect_local(args.require_live)
    output = ROOT / 'data/desktop_readiness.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if args.require_live and not result['live_configuration_ready'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
