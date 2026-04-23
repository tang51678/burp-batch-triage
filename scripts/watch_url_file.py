#!/usr/bin/env python3
import argparse
import json
import subprocess
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


def load_urls(path: Path):
    if not path.exists():
        return []
    urls = []
    seen = set()
    for raw in path.read_text(encoding='utf-8').splitlines():
        s = raw.strip()
        if not s or s.startswith('#'):
            continue
        if s not in seen:
            seen.add(s)
            urls.append(s)
    return urls


def run_init(workspace: Path, urls):
    cmd = [
        'python3',
        str(workspace / 'skills/burp-batch-triage/scripts/batch_triage.py'),
        *urls,
        '--output-root', str(workspace / 'recon'),
        '--with-report-stub',
    ]
    out = subprocess.check_output(cmd, text=True, cwd=str(workspace))
    return json.loads(out)


def main():
    parser = argparse.ArgumentParser(description='Watch a URL file and initialize new burp triage targets.')
    parser.add_argument('--input-file', default=str(Path.home() / '桌面' / 'url.txt'))
    parser.add_argument('--workspace', default='/home/ctyun/.openclaw/workspace-burp')
    parser.add_argument('--state-file', default='/home/ctyun/.openclaw/workspace-burp/recon/.url_watch_state.json')
    args = parser.parse_args()

    workspace = Path(args.workspace)
    input_file = Path(args.input_file)
    state_file = Path(args.state_file)
    state_file.parent.mkdir(parents=True, exist_ok=True)

    state = {'processed': []}
    if state_file.exists():
        try:
            state = json.loads(state_file.read_text(encoding='utf-8'))
        except Exception:
            state = {'processed': []}

    processed = set(state.get('processed', []))
    urls = load_urls(input_file)
    new_urls = [u for u in urls if normalize_target(u) not in processed]

    result = {
        'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'input_file': str(input_file),
        'found': len(urls),
        'new': len(new_urls),
        'initialized': [],
    }

    if new_urls:
        manifest = run_init(workspace, new_urls)
        for item in manifest.get('targets', []):
            target_dir = Path(item['dir'])
            required = ['summary.md', 'round1.md', 'round2.md', 'round3.md']
            if all((target_dir / name).exists() for name in required):
                result['initialized'].append(item)
                processed.add(item['normalized'])
            else:
                result.setdefault('init_errors', []).append({'target': item, 'missing': [name for name in required if not (target_dir / name).exists()]})
        state_file.write_text(json.dumps({'processed': sorted(processed)}, ensure_ascii=False, indent=2), encoding='utf-8')

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
