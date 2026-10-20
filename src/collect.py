"""Capture GitHub Trending rankings and preserve daily history, without invented data."""
from __future__ import annotations
import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path
from zoneinfo import ZoneInfo
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "site" / "data"
PERIODS = ("daily", "weekly", "monthly")
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; GitHubTrendNews/1.0)", "Accept-Language": "en-US,en;q=0.9"}
RULES = [
    ("AI・エージェント", r"\bagents?\b|\bagentic\b|\bllm\b|\bai\b|language model|generative|chatbot|\brag\b|\bclaude\b|\bgpt\b"),
    ("セキュリティ", r"secur|cyber|penetration|malware|vulnerab|reverse.engineer|exploit|forensic|pentest|\bctf\b"),
    ("デザイン・制作", r"video|image|design|drawing|diagram|photo|animation|graphics|artwork|creative|figma"),
    ("クラウド・インフラ", r"kubernetes|cloud|container|devops|deploy|observab|infrastructure|server|database|postgres|storage"),
    ("データ・分析", r"analytics|dataset|data.pipeline|visualiz|scraper|analysis|notebook|statistic|\bsql\b"),
    ("ゲーム・エンタメ", r"game|gaming|emulat|playstation|\bps5\b|minecraft|music"),
    ("開発ツール", r"editor|\bide\b|developer|framework|library|\bsdk\b|\bcli\b|terminal|plugin|coding|compiler|typescript|python|javascript"),
    ("学習・教育", r"learn|tutorial|course|education|interview|curriculum|handbook"),
]
EXPLAIN = {
    "AI・エージェント": "AIの活用や自動化に関係するプロジェクトです。",
    "セキュリティ": "ソフトウェアやシステムの安全性を調べる分野のプロジェクトです。",
    "デザイン・制作": "画像・映像・デザインなどの制作に関係するプロジェクトです。",
    "クラウド・インフラ": "サービスを動かすサーバーや基盤に関係するプロジェクトです。",
    "データ・分析": "情報の収集・整理・分析に関係するプロジェクトです。",
    "ゲーム・エンタメ": "ゲームやエンターテインメントに関係するプロジェクトです。",
    "開発ツール": "プログラムの作成や開発作業を助けるプロジェクトです。",
    "学習・教育": "技術の学習や知識の共有に関係するプロジェクトです。",
    "その他": "公開されているソフトウェア開発プロジェクトです。",
}
COUNT_RE = re.compile(r"\b([\d,]+)\s+stars?\s+(today|this week|this month)\b", re.I)
REPO_RE = re.compile(r"^/([\w.-]+)/([\w.-]+)/?$")

def compact_number(value):
    if value is None: return None
    match = re.fullmatch(r"([\d.]+)\s*([kmb])?", value.strip().lower().replace(",", ""))
    if not match: return None
    return round(float(match.group(1)) * {"k": 1000, "m": 1000000, "b": 1000000000}.get(match.group(2), 1))

def categorize(name, description):
    text = f"{name} {description}".lower()
    for category, rx in RULES:
        if re.search(rx, text): return category
    return "その他"

def japanese_intro(name, description, category):
    text = f"{name} {description}".lower()
    if re.search(r"\bagents?\b|\bagentic\b", text): return "AIに作業を任せる「エージェント」に関係するツールです。"
    if "plugin" in text or "extension" in text: return "既存のサービスや開発環境に機能を追加する仕組みです。"
    if re.search(r"\b(video|animation)\b", text): return "動画やアニメーションの作成・処理に関連します。"
    if re.search(r"\b(image|drawing|diagram)\b", text): return "画像や図表の作成・処理に関連します。"
    if "reverse engineering" in text: return "ソフトウェアの内部構造を解析するためのツールです。"
    return EXPLAIN.get(category, EXPLAIN["その他"])

def parse_trending(html, period):
    if period not in PERIODS: raise ValueError(f"Unexpected period: {period}")
    soup = BeautifulSoup(html, "html.parser")
    articles = soup.select("article.Box-row") or soup.select("div.Box-row")
    expected = {"daily": "today", "weekly": "this week", "monthly": "this month"}[period]
    result, seen = [], set()
    for article in articles:
        a = article.select_one("h2 a[href]")
        href = (a.get("href", "") if a else "").split("?")[0].split("#")[0]
        match = REPO_RE.fullmatch(href)
        if not match: continue
        name = f"{match.group(1)}/{match.group(2)}"
        if name.lower() in seen: continue
        seen.add(name.lower())
        p = article.select_one("p.col-9") or article.select_one("p")
        description = p.get_text(" ", strip=True) if p else ""
        language_node = article.select_one('[itemprop="programmingLanguage"]')
        language = language_node.get_text(" ", strip=True) if language_node else None
        stars_node = article.select_one('a[href$="/stargazers"]')
        stars_total = compact_number(stars_node.get_text(" ", strip=True)) if stars_node else None
        stars_period = None
        for el in [*article.select("span"), article]:
            m = COUNT_RE.search(el.get_text(" ", strip=True))
            if m and m.group(2).lower() == expected:
                stars_period = int(m.group(1).replace(",", ""))
                break
        category = categorize(name, description)
        result.append({"rank": len(result)+1, "full_name": name, "url": f"https://github.com/{name}",
            "description": description, "intro_ja": japanese_intro(name, description, category),
            "language": language, "category": category,
            "stars_period": stars_period, "stars_total": stars_total})
    return result

def fetch_period(period, session=None):
    session = session or requests.Session()
    url = f"https://github.com/trending?since={period}"
    response = session.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    rows = parse_trending(response.text, period)
    if len(rows) < 5: raise RuntimeError(f"{period}: only {len(rows)} entries parsed. No update.")
    if not any(isinstance(row["stars_period"], int) for row in rows):
        raise RuntimeError(f"{period}: star-growth counters missing. No update.")
    return {"source_url": url, "repositories": rows}

def save_snapshot(snapshot, data_dir=DATA):
    day = snapshot["date_jst"]
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day): raise ValueError("Invalid date")
    if set(snapshot["periods"]) != set(PERIODS): raise ValueError("Missing period")
    for period in PERIODS:
        if len(snapshot["periods"][period]["repositories"]) < 5:
            raise ValueError(f"{period}: incomplete data")
    directory = data_dir / "snapshots"
    directory.mkdir(parents=True, exist_ok=True)
    def atomic_json(path, value):
        temporary = path.with_name(path.name+".tmp")
        with temporary.open("w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
        os.replace(temporary, path)
    try: index = json.loads((data_dir/"index.json").read_text("utf-8"))
    except (OSError, ValueError): index = {"dates": []}
    dates = {item["date"]: item for item in index.get("dates", []) if isinstance(item, dict) and "date" in item}
    dates[day] = {"date": day, "path": f"data/snapshots/{day}.json", "captured_at": snapshot["captured_at"]}
    ordered = sorted(dates.values(), key=lambda x: x["date"], reverse=True)
    atomic_json(directory/f"{day}.json", snapshot)
    if ordered[0]["date"] == day: atomic_json(data_dir/"latest.json", snapshot)
    atomic_json(data_dir/"index.json", {"dates": ordered, "updated_at": snapshot["captured_at"]})

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=DATA)
    args = parser.parse_args()
    now = dt.datetime.now(dt.timezone.utc)
    with requests.Session() as session:
        periods = {}
        for period in PERIODS:
            print(f"Fetching {period}", flush=True)
            periods[period] = fetch_period(period, session)
    snapshot = {"schema_version": 1, "date_jst": now.astimezone(ZoneInfo("Asia/Tokyo")).date().isoformat(),
        "captured_at": now.isoformat(timespec="seconds"), "timezone": "Asia/Tokyo",
        "source": "GitHub Trending public HTML (unofficial scraper)", "periods": periods}
    save_snapshot(snapshot, args.data_dir)
    print(json.dumps({"date": snapshot["date_jst"], "counts": {k:len(v["repositories"]) for k,v in periods.items()}}, ensure_ascii=False))

if __name__ == "__main__":
    try: main()
    except Exception as e:
        print(f"Collection failed safely: {e}", file=sys.stderr)
        sys.exit(1)
