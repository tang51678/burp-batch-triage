#!/usr/bin/env python3
import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
import urllib3
import subprocess

urllib3.disable_warnings()

HEADERS = {'User-Agent': 'Mozilla/5.0 burp-batch-triage/0.4'}
SCRIPT_SRC_RE = re.compile(r'<script[^>]+src=["\']([^"\']+)["\']', re.I)
LINK_HREF_RE = re.compile(r'<link[^>]+href=["\']([^"\']+)["\']', re.I)
ANCHOR_HREF_RE = re.compile(r'<a[^>]+href=["\']([^"\']+)["\']', re.I)
FORM_ACTION_RE = re.compile(r'<form[^>]+action=["\']([^"\']+)["\']', re.I)
IFRAME_SRC_RE = re.compile(r'<iframe[^>]+src=["\']([^"\']+)["\']', re.I)
META_REFRESH_RE = re.compile(r'<meta[^>]+http-equiv=["\']refresh["\'][^>]+content=["\'][^"\']*url=([^"\']+)["\']', re.I)
WINDOW_LOCATION_RE = re.compile(r'''(?i)(?:location(?:\.href)?|window\.open)\s*[=(,]\s*["\']([^"\']+)["\']''')
ABS_URL_RE = re.compile(r'https?://[^\"\'\s)<>]+')
API_HINT_RE = re.compile(r'(?:(?:/api|/auth|/login|/user|/admin|/swagger|/v[0-9]+)[A-Za-z0-9_./?=&%-]*)')
PARAM_HINT_RE = re.compile(r'(?i)(?:username|password|token|captcha|verifyCode|mobile|phone|id|uid|userId|code|auth)')
PAGE_CANDIDATE_RE = re.compile(r'(?i)(?:/login|/index|/home|/main|/portal|/admin|/user|/auth)[A-Za-z0-9_./?=&%-]*')
REQUEST_PATH_RE = re.compile(r'''(?ix)
    ["\']
    (
      /[A-Za-z0-9_./?=&%-]{2,}
    )
    ["\']
''')
STATIC_EXT_RE = re.compile(r'\.(?:js|css|png|jpg|jpeg|gif|svg|ico|woff|woff2|ttf|eot|pdf|zip|rar|7z|mp4|mp3|avi|mov|wmv|webm)$', re.I)
PAGE_LIKE_SEGMENT_RE = re.compile(r'(?i)(?:login|signin|sign-in|register|signup|sign-up|portal|home|index|main|admin|user|member|center|dashboard|my|detail|list|search|query|hr|job|apply)')
MAX_PAGE_CANDIDATES = 30
MAX_PAGE_BUNDLES = 20
MAX_ROUND2_CANDIDATES = 12


def extract_target(summary_path: Path):
    text = summary_path.read_text(encoding='utf-8', errors='ignore')
    m = re.search(r'- Target: `(.*?)`', text)
    return m.group(1).strip() if m else None


def get_status(summary_text: str):
    m = re.search(r'- Status: ([^\n]+)', summary_text)
    return m.group(1).strip() if m else 'unknown'


def get_round_status(summary_text: str, round_no: int):
    m = re.search(rf'- Round {round_no}: ([^\n]+)', summary_text)
    return m.group(1).strip() if m else 'unknown'


def set_status(summary_text: str, status: str):
    if re.search(r'- Status: [^\n]+', summary_text):
        return re.sub(r'- Status: [^\n]+', f'- Status: {status}', summary_text, count=1)
    return summary_text


def update_round_status(summary_text: str, round_no: int, status: str):
    pat = rf'- Round {round_no}: [^\n]+'
    rep = f'- Round {round_no}: {status}'
    if re.search(pat, summary_text):
        return re.sub(pat, rep, summary_text, count=1)
    return summary_text


def title_of(text: str):
    m = re.search(r'<title>(.*?)</title>', text, re.I | re.S)
    return re.sub(r'\s+', ' ', m.group(1)).strip() if m else ''


def same_host(url_a: str, url_b: str):
    try:
        return urlparse(url_a).netloc == urlparse(url_b).netloc
    except Exception:
        return False


def safe_name_from_url(url: str):
    p = urlparse(url)
    base = (p.path.strip('/') or 'root').replace('/', '_')
    if p.query:
        base += '_' + hashlib.sha1(p.query.encode('utf-8')).hexdigest()[:8]
    ext = Path(p.path).suffix
    if not ext:
        ext = '.txt'
    if len(base) > 80:
        base = base[:80]
    return f"{base}{ext}"


def fetch_via_burp_or_direct(full: str, session: requests.Session, allow_redirects=True):
    burp_cmd = [
        'python3', str(Path.home() / '.openclaw/skills/burp-bridge/scripts/burp_bridge.py'),
        'fetch', '--url', full, '--proxy', 'http://127.0.0.1:8080', '--insecure', '--full'
    ]
    try:
        proc = subprocess.run(burp_cmd, capture_output=True, text=True, timeout=30)
        if proc.returncode == 0:
            payload = json.loads(proc.stdout)
            return {
                'status_code': payload.get('status'),
                'content_type': payload.get('content_type'),
                'text': payload.get('body') or payload.get('body_prefix') or '',
                'headers': {},
                'via': 'burp'
            }
    except Exception:
        pass

    r = session.get(full, timeout=20, verify=False, allow_redirects=allow_redirects, headers=HEADERS)
    return {
        'status_code': r.status_code,
        'content_type': r.headers.get('content-type'),
        'text': r.text or '',
        'headers': dict(r.headers),
        'via': 'direct'
    }


def fetch_text(session: requests.Session, full: str):
    data = fetch_via_burp_or_direct(full, session, allow_redirects=False)
    ct = data.get('content_type')
    body = data.get('text') or ''
    snippet = ''
    if ct is None or any(x in (ct or '').lower() for x in ['text', 'html', 'json', 'xml', 'javascript']):
        snippet = body[:180].replace('\n', ' ').replace('\r', ' ')
    class DummyResp:
        pass
    r = DummyResp()
    r.status_code = data.get('status_code')
    r.headers = data.get('headers', {})
    return r, ct, body, snippet


def extract_inline_hints(body: str):
    api_hints = set()
    param_hints = set()
    page_hints = set()
    for m in ABS_URL_RE.findall(body or ''):
        api_hints.add(m)
    for m in API_HINT_RE.findall(body or ''):
        api_hints.add(m)
    for m in PARAM_HINT_RE.findall(body or ''):
        param_hints.add(m)
    for m in PAGE_CANDIDATE_RE.findall(body or ''):
        page_hints.add(m)
    for pattern in (FORM_ACTION_RE, IFRAME_SRC_RE, META_REFRESH_RE, WINDOW_LOCATION_RE):
        for m in pattern.findall(body or ''):
            if isinstance(m, tuple):
                m = next((x for x in m if x), '')
            if m:
                page_hints.add(m)
    return {
        'api_hints': sorted(api_hints)[:80],
        'param_hints': sorted(param_hints)[:80],
        'page_hints': sorted(page_hints)[:80],
    }


def collect_js_and_hints(base_url: str, body: str, session: requests.Session, artifacts_dir: Path):
    js_dir = artifacts_dir / 'js'
    html_dir = artifacts_dir / 'html'
    misc_dir = artifacts_dir / 'misc'
    request_hints = []
    js_dir.mkdir(parents=True, exist_ok=True)
    html_dir.mkdir(parents=True, exist_ok=True)
    misc_dir.mkdir(parents=True, exist_ok=True)
    resource_urls = []
    seen = set()
    page_candidates = []
    page_seen = set()

    def add_resource(kind: str, raw_url: str):
        full = urljoin(base_url, raw_url)
        if same_host(base_url, full) and full not in seen:
            seen.add(full)
            resource_urls.append({'type': kind, 'url': full})

    def maybe_add_page(raw_url: str):
        full = urljoin(base_url, raw_url)
        parsed = urlparse(full)
        if not same_host(base_url, full):
            return
        if parsed.scheme not in ('http', 'https'):
            return
        path = parsed.path or '/'
        if STATIC_EXT_RE.search(path):
            return
        score = 0
        if path not in ('', '/'):
            score += 1
        if parsed.query:
            score += 1
        if PAGE_LIKE_SEGMENT_RE.search(path):
            score += 2
        if raw_url.endswith('/'):
            score += 1
        if score < 1:
            return
        if full not in page_seen:
            page_seen.add(full)
            page_candidates.append(full)

    for src in SCRIPT_SRC_RE.findall(body or ''):
        add_resource('script', src)

    for href in LINK_HREF_RE.findall(body or ''):
        add_resource('link', href)

    for href in ANCHOR_HREF_RE.findall(body or ''):
        maybe_add_page(href)

    inline_hints = extract_inline_hints(body)
    for hint in inline_hints.get('page_hints', []):
        maybe_add_page(hint)

    js_files = []
    html_files = []
    misc_files = []
    api_hints = set(inline_hints.get('api_hints', []))
    param_hints = set(inline_hints.get('param_hints', []))
    extra_pages = []

    for item in resource_urls:
        full = item['url']
        try:
            fetched = fetch_via_burp_or_direct(full, session, allow_redirects=True)
            text = fetched.get('text') or ''
            ct = (fetched.get('content_type') or '').lower()
            name = safe_name_from_url(full)
            if 'javascript' in ct or full.endswith('.js') or item['type'] == 'script':
                out = js_dir / name
                out.write_text(text, encoding='utf-8', errors='ignore')
                js_files.append({'url': full, 'file': str(out), 'status': fetched.get('status_code'), 'len': len(text), 'via': fetched.get('via')})
                child_hints = extract_inline_hints(text)
                for m in ABS_URL_RE.findall(text):
                    if same_host(base_url, m):
                        api_hints.add(m)
                for m in REQUEST_PATH_RE.findall(text):
                    request_hints.append(m)
                for m in child_hints.get('api_hints', []):
                    api_hints.add(m)
                for m in child_hints.get('param_hints', []):
                    param_hints.add(m)
                for m in child_hints.get('page_hints', []):
                    maybe_add_page(m)
            elif 'html' in ct or full.endswith('.html'):
                out = html_dir / name
                out.write_text(text, encoding='utf-8', errors='ignore')
                html_files.append({'url': full, 'file': str(out), 'status': fetched.get('status_code'), 'len': len(text), 'via': fetched.get('via')})
                extra_pages.append(full)
                child_hints = extract_inline_hints(text)
                for m in child_hints.get('api_hints', []):
                    api_hints.add(m)
                for m in child_hints.get('param_hints', []):
                    param_hints.add(m)
                for m in child_hints.get('page_hints', []):
                    maybe_add_page(m)
            else:
                out = misc_dir / name
                out.write_text(text, encoding='utf-8', errors='ignore')
                misc_files.append({'url': full, 'file': str(out), 'status': fetched.get('status_code'), 'len': len(text), 'ct': ct, 'via': fetched.get('via')})
        except Exception as e:
            misc_files.append({'url': full, 'error': str(e), 'type': item['type']})
    return {
        'scripts': [x['url'] for x in resource_urls if x['type'] == 'script'],
        'links': [x['url'] for x in resource_urls if x['type'] == 'link'],
        'page_candidates': page_candidates[:MAX_PAGE_CANDIDATES],
        'js_files': js_files,
        'html_files': html_files,
        'misc_files': misc_files,
        'extra_pages': extra_pages,
        'api_hints': sorted(api_hints)[:80],
        'param_hints': sorted(param_hints)[:80],
        'inline_api_hints': inline_hints.get('api_hints', []),
        'inline_param_hints': inline_hints.get('param_hints', []),
        'inline_page_hints': inline_hints.get('page_hints', []),
        'request_hints': sorted(set(request_hints))[:120],
    }


def save_text_file(base_dir: Path, url: str, text: str, subdir: str):
    out_dir = base_dir / subdir
    out_dir.mkdir(parents=True, exist_ok=True)
    name = safe_name_from_url(url)
    out = out_dir / name
    out.write_text(text, encoding='utf-8', errors='ignore')
    return out


def bundle_page_artifacts(page_url: str, body: str, session: requests.Session, artifacts_dir: Path, bucket: str):
    page_dir = artifacts_dir / bucket
    page_dir.mkdir(parents=True, exist_ok=True)
    html_path = save_text_file(artifacts_dir, page_url, body, f'{bucket}/html')
    hints = collect_js_and_hints(page_url, body, session, page_dir)
    parsed = urlparse(page_url)
    return {
        'url': page_url,
        'bucket': bucket,
        'path': parsed.path or '/',
        'query': parsed.query,
        'html_file': str(html_path),
        **hints,
    }


def fetch_candidate_pages(base_url: str, findings, session: requests.Session, artifacts_dir: Path):
    pages = {}
    queue = []
    queued = set()

    def enqueue(path_key: str, full_url: str):
        if full_url in queued:
            return
        queued.add(full_url)
        queue.append((path_key, full_url))

    for item in findings:
        if item.get('status') == 200:
            path = item.get('path') or '/'
            full = urljoin(base_url, path)
            enqueue(path, full)

    if not queue:
        enqueue('/', base_url)

    idx = 0
    while idx < len(queue) and len(pages) < MAX_PAGE_BUNDLES:
        key, full = queue[idx]
        idx += 1
        try:
            fetched = fetch_via_burp_or_direct(full, session, allow_redirects=True)
            ct = (fetched.get('content_type') or '').lower()
            if 'html' not in ct:
                continue
            parsed = urlparse(full)
            cpath = parsed.path or '/'
            normalized_key = cpath if cpath.startswith('/') else '/' + cpath
            if normalized_key in pages:
                continue
            bucket = 'home' if normalized_key == '/' else normalized_key.strip('/').replace('/', '_')
            bundle = bundle_page_artifacts(full, fetched.get('text') or '', session, artifacts_dir, bucket)
            pages[normalized_key] = bundle
            for candidate in bundle.get('page_candidates', []):
                candidate_path = urlparse(candidate).path or '/'
                candidate_key = candidate_path if candidate_path.startswith('/') else '/' + candidate_path
                if candidate_key not in pages:
                    enqueue(candidate_key, candidate)
        except Exception:
            continue
    return pages


def merge_hints(round1_data: dict):
    api_hints = set()
    param_hints = set()
    page_hints = set()
    request_hints = set()
    page_bundles = round1_data.get('page_bundles', {})
    home_js = round1_data.get('home_js', {})
    for source in [home_js, *page_bundles.values()]:
        for x in source.get('api_hints', []):
            api_hints.add(x)
        for x in source.get('param_hints', []):
            param_hints.add(x)
        for x in source.get('page_candidates', []):
            page_hints.add(x)
        for x in source.get('inline_page_hints', []):
            page_hints.add(x)
        for x in source.get('request_hints', []):
            request_hints.add(x)
    round1_data['merged_api_hints'] = sorted(api_hints)[:120]
    round1_data['merged_param_hints'] = sorted(param_hints)[:120]
    round1_data['merged_page_hints'] = sorted(page_hints)[:120]
    round1_data['merged_request_hints'] = sorted(request_hints)[:120]
    return round1_data


def build_artifact_indexes(round1_data: dict):
    page_map = []
    resource_index = []
    for key, bundle in sorted(round1_data.get('page_bundles', {}).items()):
        page_map.append({
            'key': key,
            'url': bundle.get('url'),
            'bucket': bundle.get('bucket'),
            'path': bundle.get('path'),
            'query': bundle.get('query'),
            'html_file': bundle.get('html_file'),
            'page_candidates': bundle.get('page_candidates', [])[:20],
        })
        for kind in ('js_files', 'html_files', 'misc_files'):
            for item in bundle.get(kind, []):
                resource_index.append({
                    'page_key': key,
                    'page_url': bundle.get('url'),
                    'kind': kind,
                    **item,
                })
    return {'pages': page_map, 'resources': resource_index}


def round1_probe(url: str, target_dir: Path):
    out = []
    session = requests.Session()
    artifacts_dir = target_dir / 'artifacts'
    round1_data = {'home_js': {'scripts': [], 'js_files': [], 'api_hints': [], 'param_hints': [], 'page_candidates': [], 'inline_page_hints': []}, 'page_bundles': {}}
    entry_body = ''
    try:
        fetched = fetch_via_burp_or_direct(url, session, allow_redirects=True)
        final_url = url
        if fetched.get('via') == 'direct':
            try:
                direct_resp = session.get(url, timeout=20, verify=False, allow_redirects=True, headers=HEADERS)
                final_url = direct_resp.url or url
                headers = dict(direct_resp.headers)
                status_code = direct_resp.status_code
                ct = direct_resp.headers.get('content-type')
                body = direct_resp.text or ''
            except Exception:
                headers = fetched.get('headers', {})
                status_code = fetched.get('status_code')
                ct = fetched.get('content_type')
                body = fetched.get('text') or ''
        else:
            headers = fetched.get('headers', {})
            status_code = fetched.get('status_code')
            ct = fetched.get('content_type')
            body = fetched.get('text') or ''
        out.append({
            'path': urlparse(url).path or '/',
            'requested_url': url,
            'final_url': final_url,
            'status': status_code,
            'ct': ct,
            'loc': headers.get('location'),
            'title': title_of(body[:2000]) if body else '',
            'len': len(body),
            'snippet': body[:180].replace('\n', ' ').replace('\r', ' '),
            'via': fetched.get('via'),
        })
        if status_code and status_code < 400 and ('html' in (ct or '').lower() or '<script' in body.lower()):
            entry_body = body
    except Exception as e:
        out.append({'path': urlparse(url).path or '/', 'requested_url': url, 'error': str(e)})
        final_url = url

    seed_findings = []
    if out and 'error' not in out[0]:
        seed_findings.append({'path': urlparse(final_url).path or '/', 'status': out[0].get('status')})
    round1_data['page_bundles'] = fetch_candidate_pages(final_url, seed_findings, session, artifacts_dir)
    if entry_body:
        round1_data['home_js'] = collect_js_and_hints(final_url, entry_body, session, artifacts_dir)
    round1_data = merge_hints(round1_data)
    indexes = build_artifact_indexes(round1_data)
    (artifacts_dir / 'page_map.json').write_text(json.dumps(indexes['pages'], ensure_ascii=False, indent=2), encoding='utf-8')
    (artifacts_dir / 'resource_index.json').write_text(json.dumps(indexes['resources'], ensure_ascii=False, indent=2), encoding='utf-8')
    (artifacts_dir / 'round1_probe.json').write_text(json.dumps({'findings': out, **round1_data}, ensure_ascii=False, indent=2), encoding='utf-8')
    return out, round1_data


def summarize_round1(url: str, findings, round1_data):
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    lines = [f'# Round 1', '', f'- Target: `{url}`', f'- Time: `{now}`', '- Status: completed', '', '## Actions', '', '- 仅请求用户提供的原始 URL，并跟随真实跳转落点', '- 解析实际返回 HTML 中的 script/link/a/form/iframe/meta refresh/window.location 线索', '- 递进抓取由真实页面导出的同源候选页面并落地其 JS/CSS/HTML', '- 从页面和 JS 中提取接口/参数/页面线索，供后续最小化验证使用', '', '## Raw findings', '']
    for item in findings:
        if 'error' in item:
            lines.append(f"- `{item['path']}`: ERROR `{item['error']}`")
        else:
            lines.append(f"- `{item['path']}`: STATUS `{item['status']}` | CT `{item['ct']}` | LOC `{item['loc']}` | TITLE `{item['title']}`")
    lines += ['', '## JS collection', '']
    home_js = round1_data.get('home_js', {})
    lines.append(f"- script src count: `{len(home_js.get('scripts', []))}`")
    lines.append(f"- link href count: `{len(home_js.get('links', []))}`")
    lines.append(f"- downloaded js count: `{len([x for x in home_js.get('js_files', []) if 'file' in x])}`")
    lines.append(f"- downloaded html count: `{len([x for x in home_js.get('html_files', []) if 'file' in x])}`")
    lines.append(f"- downloaded misc count: `{len([x for x in home_js.get('misc_files', []) if 'file' in x])}`")
    if home_js.get('api_hints'):
        lines.append('- api hints:')
        lines.extend([f"  - `{x}`" for x in home_js.get('api_hints', [])[:15]])
    if round1_data.get('merged_api_hints'):
        lines.append('- merged page/api hints:')
        lines.extend([f"  - `{x}`" for x in round1_data.get('merged_api_hints', [])[:15]])
    if home_js.get('param_hints'):
        lines.append('- param hints:')
        lines.extend([f"  - `{x}`" for x in home_js.get('param_hints', [])[:15]])
    if round1_data.get('merged_param_hints'):
        lines.append(f"- merged param hint count: `{len(round1_data.get('merged_param_hints', []))}`")
    if round1_data.get('page_bundles'):
        lines.append(f"- html pages bundled: `{len(round1_data.get('page_bundles', {}))}`")
        lines.append('- bundled pages:')
        lines.extend([f"  - `{x}`" for x in sorted(round1_data.get('page_bundles', {}).keys())[:15]])
    lines.append(f"- inline api hint count: `{len(home_js.get('inline_api_hints', []))}`")
    lines.append(f"- inline param hint count: `{len(home_js.get('inline_param_hints', []))}`")
    lines.append(f"- inline page hint count: `{len(home_js.get('inline_page_hints', []))}`")
    lines += ['', '## Interim conclusion', '', '- 已完成首轮自动摸底；当前结果仅作低噪声入口收敛，待后续定向 Round 2。']
    return '\n'.join(lines) + '\n'


def update_summary_for_round1(summary_text: str, findings, round1_data):
    confirmed = []
    cannot = []
    interesting = []
    for item in findings:
        if 'error' in item:
            continue
        if item.get('status') in (301, 302, 303, 307, 308) and item.get('loc'):
            interesting.append(f"- `{item['path']}` 跳转到 `{item['loc']}`")
        if item.get('status') == 200 and item.get('title'):
            interesting.append(f"- `{item['path']}` 返回页面标题 `{item['title']}`")
    home_js = round1_data.get('home_js', {})
    if home_js.get('scripts') or home_js.get('links'):
        confirmed.append(f"- 首页识别到 `{len(home_js.get('scripts', []))}` 个同源脚本、`{len(home_js.get('links', []))}` 个同源链接资源；已落地 `{len([x for x in home_js.get('js_files', []) if 'file' in x])}` 个 JS 文件。")
    if round1_data.get('merged_api_hints'):
        confirmed.extend([f"- 页面/资源聚合线索 `{x}`" for x in round1_data.get('merged_api_hints', [])[:5]])
    if round1_data.get('merged_param_hints'):
        confirmed.append(f"- 聚合页面参数关键字：`{', '.join(round1_data.get('merged_param_hints', [])[:8])}`")
    if not interesting and not home_js.get('scripts'):
        cannot.append('- 当前仅完成入口摸底，尚未识别高价值登录链或未授权接口。')
    else:
        cannot.append('- 当前尚未形成漏洞结论，需在 Round 2 只围绕高价值路径继续最小化验证。')

    summary_text = set_status(summary_text, 'round 1 completed')
    summary_text = update_round_status(summary_text, 1, 'completed')
    summary_text = update_round_status(summary_text, 2, 'pending')
    summary_text = re.sub(r'## Pending validation\n\n(?:- .*\n)+', '## Pending validation\n\n- 待基于 Round 1 收出的高价值路径进入 Round 2。\n', summary_text)
    summary_text = re.sub(r'## Confirmed\n\n(?:- .*\n)+', '## Confirmed\n\n' + ('\n'.join(confirmed) + '\n' if confirmed else '- 已完成首轮入口摸底。\n'), summary_text)
    summary_text = re.sub(r'## Cannot conclude\n\n(?:- .*\n)+', '## Cannot conclude\n\n' + ('\n'.join(cannot) + '\n'), summary_text)
    summary_text = re.sub(r'## Next step\n\n(?:- .*\n)+', '## Next step\n\n- 自动进入 Round 2，只围绕首轮收出的重点线继续最小化验证。\n', summary_text)
    return summary_text


def build_round2_candidates(base_url: str, data: dict):
    candidates = []
    seen = set()
    base_host = urlparse(base_url).netloc

    def candidate_kind(raw: str):
        parsed = urlparse(raw if raw.startswith('http') else urljoin(base_url, raw))
        path = parsed.path or '/'
        if STATIC_EXT_RE.search(path):
            return None
        lowered = path.lower()
        if any(x in lowered for x in ['/login', '/auth', '/user', '/admin', '/portal', '/main', '/index']):
            return 'page_or_action'
        if '/api/' in lowered or lowered.startswith('/api'):
            return 'request_hint'
        if parsed.query:
            return 'request_hint'
        return 'page_or_action'

    def add_candidate(raw: str, source: str):
        if not raw:
            return
        full = raw if raw.startswith('http') else urljoin(base_url, raw)
        parsed = urlparse(full)
        if parsed.scheme not in ('http', 'https'):
            return
        if parsed.netloc != base_host:
            return
        kind = candidate_kind(full)
        if not kind:
            return
        if full in seen:
            return
        seen.add(full)
        candidates.append({'kind': kind, 'url': full, 'source': source})

    for item in data.get('findings', []):
        if item.get('status') in (200, 401, 403):
            final_url = item.get('final_url')
            path = item.get('path')
            if final_url:
                add_candidate(final_url, 'round1_entry')
            elif path and path != '/':
                add_candidate(path, 'round1_entry')

    for hint in data.get('merged_request_hints', [])[:20]:
        add_candidate(hint, 'request_hint')
    for hint in data.get('merged_page_hints', [])[:20]:
        add_candidate(hint, 'page_hint')

    return candidates[:MAX_ROUND2_CANDIDATES]


def run_round2(url: str, target_dir: Path):
    probe_path = target_dir / 'artifacts' / 'round1_probe.json'
    data = {'findings': [], 'home_js': {'api_hints': [], 'param_hints': [], 'page_candidates': []}, 'merged_api_hints': [], 'merged_param_hints': [], 'merged_page_hints': []}
    if probe_path.exists():
        data = json.loads(probe_path.read_text(encoding='utf-8'))
    candidates = build_round2_candidates(url, data)
    session = requests.Session()
    checks = []
    for item in candidates:
        full = item['url']
        try:
            fetched = fetch_via_burp_or_direct(full, session, allow_redirects=False)
            checks.append({'kind': item['kind'], 'source': item.get('source'), 'url': full, 'status': fetched.get('status_code'), 'ct': fetched.get('content_type'), 'len': len(fetched.get('text') or ''), 'via': fetched.get('via')})
        except Exception as e:
            checks.append({'kind': item['kind'], 'url': full, 'error': str(e)})
    (target_dir / 'artifacts' / 'round2_checks.json').write_text(json.dumps({'checks': checks, 'candidates': candidates}, ensure_ascii=False, indent=2), encoding='utf-8')
    lines = [f'# Round 2', '', f'- Target: `{url}`', f'- Time: `{datetime.now().strftime("%Y-%m-%d %H:%M")}`', '- Status: completed', '', '## Actions', '', '- 围绕 Round 1 提取的接口线索、页面线索、已命中路径做低噪声补样验证。', '', '## Raw findings', '']
    if not checks:
        lines.append('- 无可用 JS 接口线索，未执行额外补样。')
    else:
        for item in checks:
            if 'error' in item:
                lines.append(f"- `{item['url']}`: ERROR `{item['error']}`")
            else:
                lines.append(f"- [{item['kind']}/{item.get('source')}] `{item['url']}`: STATUS `{item['status']}` | CT `{item['ct']}` | LEN `{item['len']}` | VIA `{item['via']}`")
    lines += ['', '## Interim conclusion', '', '- 已完成第二轮围绕接口/页面线索的最小化补样。']
    return '\n'.join(lines) + '\n', checks


def update_summary_for_round2(summary_text: str, checks):
    summary_text = set_status(summary_text, 'round 2 completed')
    summary_text = update_round_status(summary_text, 2, 'completed')
    summary_text = update_round_status(summary_text, 3, 'pending')
    extra = '- 第二轮未命中可补样接口。\n' if not checks else f"- 第二轮已围绕 `{len(checks)}` 条 JS 线索做补样验证。\n"
    summary_text = re.sub(r'## Pending validation\n\n(?:- .*\n)+', '## Pending validation\n\n- 已自动进入 Round 3 收敛队列，后续继续围绕高价值线做低噪声补样。\n', summary_text)
    summary_text = re.sub(r'## Cannot conclude\n\n(?:- .*\n)+', '## Cannot conclude\n\n' + extra + '- 当前仍未形成可直接上报的漏洞闭环。\n', summary_text)
    summary_text = re.sub(r'## Next step\n\n(?:- .*\n)+', '## Next step\n\n- 自动进入 Round 3，准备做最终收敛。\n', summary_text)
    return summary_text


def build_round3(url: str):
    return f'''# Round 3\n\n- Target: `{url}`\n- Time: `{datetime.now().strftime("%Y-%m-%d %H:%M")}`\n- Status: completed\n\n## Actions\n\n- 对前三轮结果做最终收敛，按已确认 / 待验证 / 不能成立整理结论。\n\n## Interim conclusion\n\n- 本轮完成自动收敛，不再扩展泛扫。\n'''


def update_summary_for_round3(summary_text: str):
    summary_text = set_status(summary_text, 'completed')
    summary_text = update_round_status(summary_text, 3, 'completed')
    summary_text = re.sub(r'## Pending validation\n\n(?:- .*\n)+', '## Pending validation\n\n- 如需继续，仅建议对已识别高价值线做人审复核。\n', summary_text)
    summary_text = re.sub(r'## Next step\n\n(?:- .*\n)+', '## Next step\n\n- 当前目标已完成自动三轮收敛；如后续需要，再按高价值线人工复核。\n', summary_text)
    return summary_text


def main():
    parser = argparse.ArgumentParser(description='Auto-advance pending burp batch triage targets.')
    parser.add_argument('--recon-root', default='/home/ctyun/.openclaw/workspace-burp/recon')
    parser.add_argument('--limit', type=int, default=2)
    args = parser.parse_args()

    root = Path(args.recon_root)
    targets = []
    for summary in sorted(root.glob('*/summary.md')):
        text = summary.read_text(encoding='utf-8', errors='ignore')
        status = get_status(text)
        r1 = get_round_status(text, 1)
        r2 = get_round_status(text, 2)
        r3 = get_round_status(text, 3)
        if status in ('initialized', 'round 1 pending') or r1 == 'pending':
            targets.append((summary, text, 'round1'))
        elif status in ('round 1 completed', 'round 2 pending') or (r1 == 'completed' and r2 == 'pending'):
            targets.append((summary, text, 'round2'))
        elif status in ('round 2 completed', 'round 3 pending') or (r2 == 'completed' and r3 == 'pending'):
            targets.append((summary, text, 'round3'))

    handled = []
    for summary, text, action in targets[:args.limit]:
        url = extract_target(summary)
        if not url:
            continue
        target_dir = summary.parent
        now = datetime.now().strftime('%Y-%m-%d %H:%M')
        if action == 'round1':
            findings, round1_data = round1_probe(url, target_dir)
            (target_dir / 'round1.md').write_text(summarize_round1(url, findings, round1_data), encoding='utf-8')
            new_summary = update_summary_for_round1(text, findings, round1_data)
            summary.write_text(new_summary, encoding='utf-8')
            handled.append({'target': url, 'dir': str(target_dir), 'action': 'round1-completed'})
        elif action == 'round2':
            round2_md, checks = run_round2(url, target_dir)
            (target_dir / 'round2.md').write_text(round2_md, encoding='utf-8')
            new_summary = update_summary_for_round2(text, checks)
            summary.write_text(new_summary, encoding='utf-8')
            handled.append({'target': url, 'dir': str(target_dir), 'action': 'round2-completed'})
        elif action == 'round3':
            (target_dir / 'round3.md').write_text(build_round3(url), encoding='utf-8')
            summary.write_text(update_summary_for_round3(text), encoding='utf-8')
            handled.append({'target': url, 'dir': str(target_dir), 'action': 'round3-completed'})

    print(json.dumps({'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'handled': handled, 'count': len(handled)}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
