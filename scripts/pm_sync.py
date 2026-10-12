#!/usr/bin/env python3
"""만든 콘텐츠 vs 올린 콘텐츠 대조 (주간 PM 1단계).

로컬 작업 폴더(클로드와 만든 HTML·4종 콘텐츠)와 네이버 블로그 RSS를 맞대서
"만들었는데 안 올린 것"과 "올렸는데 폴더에 없는 것"을 뽑아 PM/업로드_대조.md로 씀.
결과는 주간 PM 때 클로드가 PM/pm_data.json의 inventory에 반영함.

사용법 (네이버에 접속되는 맥에서):
    python3 scripts/pm_sync.py
    python3 scripts/pm_sync.py --feed purpleant=저장한_rss.xml   # 오프라인 테스트

한계:
- 네이버 블로그 RSS는 최근 글 약 50개만 줌. 그보다 오래된 글은 "RSS 범위 밖"으로 표시함.
- 인스타는 공개 피드가 없어 대조 못 함. pm_data.json의 inventory에서 손으로 관리.
- 유튜브는 sources.json에 channel_id를 넣으면 최근 15개만 대조함.
"""

import argparse
import difflib
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "PM" / "sources.json"
REPORT = ROOT / "PM" / "업로드_대조.md"

TAG = re.compile(r"<[^>]+>")
TITLE = re.compile(r"<title[^>]*>(.*?)</title>", re.S | re.I)
H1 = re.compile(r"<h1[^>]*>(.*?)</h1>", re.S | re.I)
NON_WORD = re.compile(r"[^0-9a-z가-힣]+")
MATCH_RATIO = 0.55


def norm(s):
    return NON_WORD.sub("", s.lower())


def load_config(path):
    if not path.exists():
        print(f"[FAIL] {path} 없음")
        sys.exit(1)
    return json.loads(path.read_text(encoding="utf-8"))


def blog_stats(blog_id):
    """네이버 모바일 블로그 API의 공개 숫자 (오늘 방문·이웃·누적 방문)."""
    req = urllib.request.Request(f"https://m.blog.naver.com/api/blogs/{blog_id}",
                                 headers={"User-Agent": "Mozilla/5.0 (iPhone)",
                                          "Referer": f"https://m.blog.naver.com/{blog_id}"})
    with urllib.request.urlopen(req, timeout=20) as r:
        res = json.loads(r.read())["result"]
    return res["dayVisitorCount"], res["subscriberCount"], res["totalVisitorCount"]


def read_feed(source):
    """URL이나 로컬 파일에서 RSS/Atom을 읽어 [(제목, 링크, 날짜)]로."""
    if re.match(r"https?://", source):
        req = urllib.request.Request(source, headers={"User-Agent": "Mozilla/5.0 pm_sync"})
        with urllib.request.urlopen(req, timeout=20) as r:
            raw = r.read()
    else:
        raw = Path(source).expanduser().read_bytes()
    root = ET.fromstring(raw)
    items = []
    for it in root.iter("item"):
        title = (it.findtext("title") or "").strip()
        link = (it.findtext("link") or "").strip()
        date = ""
        if it.findtext("pubDate"):
            try:
                date = parsedate_to_datetime(it.findtext("pubDate")).strftime("%Y-%m-%d")
            except (TypeError, ValueError):
                pass
        items.append((title, link, date))
    atom = "{http://www.w3.org/2005/Atom}"
    for e in root.iter(atom + "entry"):
        link = e.find(atom + "link")
        items.append(((e.findtext(atom + "title") or "").strip(),
                      link.get("href", "") if link is not None else "",
                      (e.findtext(atom + "published") or "")[:10]))
    return items


def local_posts(axis, dirs):
    """클로드와 만든 결과물을 [(대조키, 표시이름, 경로, 날짜)]로."""
    out = []
    for d in dirs:
        base = Path(d).expanduser()
        if not base.is_absolute():
            base = ROOT / base
        if not base.is_dir():
            print(f"[WARN] 폴더 없음: {d}")
            continue
        if axis == "purpleant":
            for f in sorted(base.glob("*.html")):
                html = f.read_text(encoding="utf-8", errors="ignore")
                m = H1.search(html) or TITLE.search(html)
                title = TAG.sub("", m.group(1)).strip() if m else f.stem
                date = f.stem[:8] if f.stem[:8].isdigit() else ""
                out.append((title, title, f, date))
        else:
            for f in sorted(base.glob("*_4종콘텐츠.md")):
                shop = f.stem.split("_")[0]
                out.append((shop, f.stem.replace("_4종콘텐츠", ""), f, ""))
    return out


def is_match(axis, key, feed_title):
    a, b = norm(key), norm(feed_title)
    if not a or not b:
        return False
    if axis.startswith("foorog"):
        return a in b  # 푸로그는 상호명이 제목에 들어가면 같은 방문으로 봄
    return a in b or b in a or difflib.SequenceMatcher(None, a, b).ratio() >= MATCH_RATIO


def compare(axis, posts, feed):
    oldest = min((d for _, _, d in feed if d), default="")
    made_not_up, up = [], []
    used = set()
    for key, name, path, date in posts:
        hit = next((i for i, (t, _, _) in enumerate(feed) if is_match(axis, key, t)), None)
        if hit is None:
            out_of_range = bool(date and oldest and date.replace("-", "") < oldest.replace("-", ""))
            made_not_up.append((name, path, out_of_range))
        else:
            used.add(hit)
            up.append((name, feed[hit]))
    only_feed = [f for i, f in enumerate(feed) if i not in used]
    return made_not_up, up, only_feed, oldest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=Path, default=CONFIG, help="채널·폴더 설정 (기본 PM/sources.json)")
    ap.add_argument("--feed", action="append", default=[], help="축=RSS파일 (오프라인 테스트용)")
    args = ap.parse_args()
    overrides = dict(f.split("=", 1) for f in args.feed)

    cfg = load_config(args.config)
    lines = [f"# 업로드 대조 — {datetime.now():%Y-%m-%d %H:%M}", "",
             "`python3 scripts/pm_sync.py`가 만든 파일임. 주간 PM 때 클로드가 읽고 `PM/pm_data.json` inventory에 반영함.", ""]
    summary = []
    lines += ["## 블로그 공개 숫자", "", "| 블로그 | 오늘 방문 | 이웃 | 누적 방문 |", "|---|---|---|---|"]
    for axis, c in cfg["channels"].items():
        m = re.search(r"rss\.blog\.naver\.com/([^.]+)\.xml", c.get("rss", ""))
        if not m:
            continue
        try:
            day, subs, total = blog_stats(m.group(1))
            lines.append(f"| {c['label']} | {day:,} | {subs:,} | {total:,} |")
            summary.append(f"{c['label']}: 오늘 방문 {day:,} · 이웃 {subs:,}")
        except Exception as e:  # 통계는 부가 정보라 실패해도 대조는 계속함
            lines.append(f"| {c['label']} | 못 읽음 ({e}) | | |")
    lines.append("")
    for axis, c in cfg["channels"].items():
        label = c["label"]
        src = overrides.get(axis) or c.get("rss")
        if not src:
            continue
        try:
            feed = read_feed(src)
        except Exception as e:  # 네트워크·파싱 실패는 축 하나만 건너뜀
            print(f"[WARN] {label} RSS 못 읽음 — {e}")
            lines += [f"## {label}", "", f"RSS 못 읽음: `{e}`", ""]
            continue
        posts = local_posts(axis, c.get("local", []))
        made_not_up, up, only_feed, oldest = compare(axis, posts, feed)
        summary.append(f"{label}: 폴더 {len(posts)} · RSS {len(feed)} · 미업로드 {len(made_not_up)}")

        lines += [f"## {label}", "",
                  f"RSS 최근 {len(feed)}개 (가장 오래된 글 {oldest or '날짜 없음'}) · 로컬 결과물 {len(posts)}개", ""]
        lines += ["### 만들었는데 안 올린 것", ""]
        if made_not_up:
            for name, path, oor in made_not_up:
                note = " — RSS 범위보다 오래됨, 블로그에서 직접 확인" if oor else ""
                lines.append(f"- [ ] {name} (`{path.relative_to(ROOT) if path.is_relative_to(ROOT) else path}`){note}")
        else:
            lines.append("- 없음")
        lines += ["", "### 올라간 것", ""]
        lines += [f"- {name} → {d} {link}" for name, (_, link, d) in up] or ["- 없음"]
        lines += ["", "### 올렸는데 폴더에 없는 것 (클로드 밖에서 쓴 글)", ""]
        lines += [f"- {d} {t}" for t, _, d in only_feed[:20]] or ["- 없음"]
        if len(only_feed) > 20:
            lines.append(f"- … 외 {len(only_feed) - 20}개")
        lines.append("")

    REPORT.write_text("\n".join(lines), encoding="utf-8")
    for s in summary:
        print(f"[PASS] {s}")
    print(f"[PASS] {REPORT.relative_to(ROOT)} 작성")
    return 0


if __name__ == "__main__":
    sys.exit(main())
