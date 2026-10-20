"""Source-grounded GitHub repository facts for featured Trending entries.

No language model is used. Original README excerpts are displayed as quotations,
never as invented Japanese explanations. Errors must not interrupt Trending capture.
"""
from __future__ import annotations

import base64
import datetime as dt
import os
import re
from urllib.parse import urlsplit

import requests

API = 'https://api.github.com'
REPO_RE = re.compile(r'^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$')
MAX_FEATURED_PER_PERIOD = 3
MAX_README_BYTES = 200_000

# Narrow descriptions have a defensible Japanese gloss; otherwise use original text.
USE_CASES = [
    (r'reverse.engineer|reverse engineering|binary analysis', 'AIエージェントを使い、アプリの挙動や実行ファイルの内部構造を調べるためのツール。対応環境は公式READMEで確認してください。'),
    (r'claude code plugins?|plugin directory', 'Claude Codeに追加できるプラグインを見つけるための公式ディレクトリ。開発環境の拡張に役立ちます。'),
    (r'job search|cover letters?|tailor cvs?|job application', '求人の評価、応募書類の調整、面接準備などをAIで支援する仕組み。求職活動を自分の環境で進めるためのツールです。'),
    (r'context window|context optimization', 'AIコーディングで使うコンテキストを整理し、限られた入力領域を効率よく使うための開発支援ツールです。'),
    (r'diagram design|diagram types', 'コード支援AIと組み合わせて図解や構成図を作るためのツール。技術内容の視覚化に使えます。'),
    (r'images?|illustrations?|crafting engine|designers? and filmmakers', 'アーティスト、デザイナー、映像制作者の制作作業を支えるエンジン。作品制作向けのワークフローに関係します。'),
    (r'video restoration|video generation|render video', '動画の生成、加工、レンダリングなどの工程で利用するツール。具体的な対応形式は公式READMEで確認できます。'),
    (r'ps5|playstation|emulat', 'PS5などのゲーム用ソフトの移植や解析を扱う開発ツール。技術的な前提・制限はREADMEで確認してください。'),
    (r'coding agents?|agentic coding|coding assistant', 'AIエージェントにコーディング作業を依頼したり、開発手順を自動化するためのツールです。'),
]


def _clean_text(text: str, limit: int = 400) -> str:
    """Strip small Markdown fragments and control characters; do not render as HTML."""
    text = re.sub(r'!\[[^\]]*\]\([^)]*\)', '', text)
    text = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', text)
    text = re.sub(r'<[^>]{1,250}>', ' ', text)
    text = re.sub(r'(?<!\w)[`*_~]+|[`*_~]+(?!\w)', '', text)
    text = re.sub(r'[\x00-\x1f\x7f]+', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:limit].strip()


def readme_highlights(markdown: str) -> dict:
    """Return original-language excerpts; prefer bullet points under Features.

    Anything resembling an instruction from the README is treated as plain source
    content, not as an instruction to this program or to the reader.
    """
    if not isinstance(markdown, str):
        return {'excerpt': None, 'features': []}
    paragraphs, features, buffer = [], [], []
    in_fence, in_comment, in_features = False, False, False

    def flush():
        if buffer:
            value = _clean_text(' '.join(buffer), 330)
            if 65 <= len(value) <= 330 and not value.startswith(('http', '|')):
                paragraphs.append(value)
            buffer.clear()

    for line in markdown.splitlines()[:600]:
        line = line.strip()
        if line.startswith('<!--'):
            in_comment = '-->' not in line
            continue
        if in_comment:
            in_comment = '-->' not in line
            continue
        if re.match(r'^(```|~~~)', line):
            in_fence = not in_fence
            flush()
            continue
        if in_fence:
            continue
        # Ignore linked language navigation, badge clouds and disclaimer admonitions.
        if line.count('](') >= 4 or line.count(' · ') >= 4 or line.startswith('>'):
            flush()
            continue
        header = re.match(r'^(#{1,4})\s+(.+)', line)
        if header:
            flush()
            name = _clean_text(header.group(2), 90).lower()
            if len(header.group(1)) <= 2:
                in_features = bool(re.search(r'\b(features?|capabilities|highlights|what it does|what you can analyze|what you can do|key benefits|structure)\b', name))
            elif in_features and len(features) < 4 and 5 < len(name) < 90:
                features.append(_clean_text(header.group(2), 120))
            continue
        if line.startswith(('<img', '<a ', '<div', '<p align', '<picture', '<svg', '---', '![')):
            flush()
            continue
        if line.startswith('|'):
            flush()
            if in_features and len(features) < 4:
                first_cell = line.strip('| ').split('|', 1)[0]
                if not re.fullmatch(r'[: -]+', first_cell):
                    label = _clean_text(first_cell, 125)
                    if len(label) > 20 and label.lower() not in ('feature', 'description', 'preview'):
                        features.append(label)
            continue
        bullet = re.match(r'^[-*+]\s+(.+)$', line)
        if bullet:
            flush()
            value = _clean_text(bullet.group(1), 145)
            if in_features and len(value) >= 17 and len(features) < 4:
                features.append(value)
            continue
        if not line or re.match(r'^\[[^]]+\]:', line):
            flush()
        elif len(line) < 1500 and not re.match(r'^\[!?\[', line):
            buffer.append(line)
    flush()
    return {'excerpt': paragraphs[0] if paragraphs else None, 'features': features[:4]}


def use_case_ja(description: str) -> str | None:
    for regex, text in USE_CASES:
        if re.search(regex, description or '', flags=re.IGNORECASE):
            return text
    return None


def safe_homepage(value):
    if not isinstance(value, str) or len(value) > 300:
        return None
    url = value.strip()
    parts = urlsplit(url)
    if parts.scheme not in ('https', 'http') or not parts.netloc or parts.username or parts.password:
        return None
    return url


def api_headers():
    headers = {
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28',
        'User-Agent': 'GitHubTrendNews/1.1 (public Trending repo metadata)',
    }
    token = os.getenv('GH_TREND_TOKEN') or os.getenv('GITHUB_TOKEN')
    if token:
        headers['Authorization'] = f'Bearer {token}'
    return headers


def _api_json(session: requests.Session, path: str, headers: dict):
    response = session.get(f'{API}{path}', headers=headers, timeout=12)
    if response.status_code in (403, 404, 429):
        return None
    response.raise_for_status()
    return response.json()


def iso_day(value):
    if not isinstance(value, str) or len(value) > 35:
        return None
    try:
        return dt.datetime.fromisoformat(value.replace('Z', '+00:00')).date().isoformat()
    except ValueError:
        return None


def fetch_repository_details(full_name: str, session: requests.Session) -> dict | None:
    """Fetch REST metadata + README and latest release, bounded and fault-tolerant."""
    if not REPO_RE.fullmatch(full_name or ''):
        return None
    headers = api_headers()
    try:
        data = _api_json(session, f'/repos/{full_name}', headers)
        if not isinstance(data, dict) or data.get('full_name', '').lower() != full_name.lower():
            return None
        license_data = data.get('license')
        license_name = license_data.get('spdx_id') if isinstance(license_data, dict) else None
        if license_name in ('NOASSERTION', ''):
            license_name = None
        topics = data.get('topics')
        topics = [str(t)[:40] for t in topics if isinstance(t, str)][:6] if isinstance(topics, list) else []
        details = {
            'source': 'GitHub REST API',
            'checked_at': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'),
            'summary': _clean_text(data.get('description') or '', 380) or None,
            'use_case_ja': use_case_ja(data.get('description') or ''),
            'topics': topics,
            'license': license_name,
            'forks': data.get('forks_count') if type(data.get('forks_count')) is int else None,
            'stars_total': data.get('stargazers_count') if type(data.get('stargazers_count')) is int else None,
            'pushed_on': iso_day(data.get('pushed_at')),
            'created_on': iso_day(data.get('created_at')),
            'homepage': safe_homepage(data.get('homepage')),
            'readme_excerpt': None,
            'readme_features': [],
            'latest_release': None,
            'archived': data.get('archived') is True,
        }
    except (requests.RequestException, ValueError, TypeError, KeyError, AttributeError) as exc:
        print(f'GitHub API detail skipped for {full_name}: {type(exc).__name__}', flush=True)
        return None

    # Metadata is valuable even when README or release endpoints cannot be fetched.
    try:
        readme = _api_json(session, f'/repos/{full_name}/readme', headers)
        if isinstance(readme, dict) and readme.get('encoding') == 'base64':
            encoded = readme.get('content') or ''
            if len(encoded) < MAX_README_BYTES * 1.4:
                raw = base64.b64decode(encoded, validate=False)
                if len(raw) <= MAX_README_BYTES:
                    parsed = readme_highlights(raw.decode('utf-8', errors='replace'))
                    details['readme_excerpt'] = parsed['excerpt']
                    details['readme_features'] = parsed['features']
    except (requests.RequestException, ValueError, TypeError, UnicodeError) as exc:
        print(f'README skipped for {full_name}: {type(exc).__name__}', flush=True)

    try:
        release = _api_json(session, f'/repos/{full_name}/releases/latest', headers)
        if isinstance(release, dict) and isinstance(release.get('tag_name'), str):
            tag = _clean_text(release['tag_name'], 60)
            link = release.get('html_url')
            if isinstance(link, str) and link.startswith(f'https://github.com/{full_name}/releases/'):
                details['latest_release'] = {'tag': tag, 'date': iso_day(release.get('published_at')), 'url': link}
    except (requests.RequestException, ValueError, TypeError) as exc:
        print(f'Release skipped for {full_name}: {type(exc).__name__}', flush=True)
    return details


def enrich_periods(periods: dict, session: requests.Session, top_n: int = MAX_FEATURED_PER_PERIOD) -> dict:
    """Attach details to displayed top three of each period; reuse requests by repo."""
    cache: dict[str, dict | None] = {}
    for period in ('daily', 'weekly', 'monthly'):
        for repo in periods.get(period, {}).get('repositories', [])[:top_n]:
            name = repo.get('full_name') or ''
            key = name.lower()
            if key not in cache:
                cache[key] = fetch_repository_details(name, session)
            if cache[key]:
                repo['details'] = cache[key]
                if cache[key].get('stars_total') is not None:
                    repo['stars_total'] = cache[key]['stars_total']
    return {'requested': len(cache), 'enriched': sum(bool(x) for x in cache.values())}
