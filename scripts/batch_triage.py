#!/usr/bin/env python3
import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse


def normalize_target(url: str) -> str:
    p = urlparse(url.strip())
    host = (p.hostname or 'unknown').replace('.', '_')
    if p.port:
        port = p.port
    else:
        port = 443 if p.scheme == 'https' else 80
    return f"{host}_{port}"


def load_targets(args_targets, input_file):
    items = []
    if input_file:
        text = Path(input_file).read_text(encoding='utf-8')
        items.extend(text.splitlines())
    items.extend(args_targets)

    urls = []
    seen = set()
    for raw in items:
        s = raw.strip()
        if not s or s.startswith('#'):
            continue
        if s not in seen:
            seen.add(s)
            urls.append(s)
    return urls


def write_summary(target_dir: Path, url: str, now: str):
    summary = f"""# Summary\n\n- Target: `{url}`\n- Created: `{now}`\n- Status: initialized\n\n## Round status\n\n- Round 1: pending\n- Round 2: pending\n- Round 3: pending\n\n## Confirmed\n\n- None yet.\n\n## Pending validation\n\n- Awaiting triage execution.\n\n## Cannot conclude\n\n- Not started.\n\n## Next step\n\n- Run three-round minimal verification and update this file.\n"""
    (target_dir / 'summary.md').write_text(summary, encoding='utf-8')


def write_round_stub(target_dir: Path, round_no: int, url: str, now: str):
    content = f"""# Round {round_no}\n\n- Target: `{url}`\n- Time: `{now}`\n- Status: pending\n\n## Actions\n\n- Pending execution.\n\n## Raw findings\n\n- None yet.\n\n## Interim conclusion\n\n- Not started.\n"""
    (target_dir / f'round{round_no}.md').write_text(content, encoding='utf-8')


def write_report_stub(target_dir: Path, url: str, now: str):
    content = f"""# Report\n\n- Target: `{url}`\n- Created: `{now}`\n\n## Issue title\n\n- [Fill when a confirmed finding exists]\n\n## Risk\n\n- TBD\n\n## Affected path\n\n- TBD\n\n## Reproduction\n\n1. TBD\n\n## Evidence\n\n- TBD\n\n## Why this is confirmed\n\n- TBD\n\n## Validation boundary\n\n- Kept to minimal verification.\n"""
    (target_dir / 'report.md').write_text(content, encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description='Initialize per-target markdown structure for burp batch triage.')
    parser.add_argument('targets', nargs='*', help='Target URLs')
    parser.add_argument('--input-file', help='Text or markdown file containing one URL per line')
    parser.add_argument('--output-root', default='recon', help='Output root directory')
    parser.add_argument('--with-report-stub', action='store_true', help='Also create report.md stub')
    args = parser.parse_args()

    urls = load_targets(args.targets, args.input_file)
    if not urls:
        raise SystemExit('No targets provided.')

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    root = Path(args.output_root)
    root.mkdir(parents=True, exist_ok=True)

    manifest = []
    for url in urls:
        name = normalize_target(url)
        target_dir = root / name
        artifacts_dir = target_dir / 'artifacts'
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        write_summary(target_dir, url, now)
        for i in (1, 2, 3):
            write_round_stub(target_dir, i, url, now)
        if args.with_report_stub:
            write_report_stub(target_dir, url, now)
        manifest.append({
            'url': url,
            'dir': str(target_dir),
            'normalized': name,
        })

    print(json.dumps({'targets': manifest}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
