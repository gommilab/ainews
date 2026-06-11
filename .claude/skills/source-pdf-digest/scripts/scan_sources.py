#!/usr/bin/env python3
"""원천 RSS 피드 신규 검출기 — source-pdf-digest.

references/sources.yaml의 corporate/conference 계층에서 feed: rss 원천을 폴링하고,
_workspace/.source_digest_state.json에 기록된 기존 항목을 제외한 '신규' 후보를 출력한다.
(번역·요약·이미지는 에이전트가 후속 enrich. 이 스크립트는 신규 검출과 메타 추출만 담당.)

외부 의존성 없음(파이썬 표준 라이브러리). PyYAML이 있으면 쓰고, 없으면 경량 파서로 폴백.

사용:
  python3 scan_sources.py --layer corporate --out _workspace/2026-06-12/digest-am/01_scan_corporate.json
  python3 scan_sources.py --layer conference --out <path> [--days 3] [--no-state]
"""
import argparse
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCES_YAML = os.path.join(HERE, "..", "references", "sources.yaml")
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))  # project root
STATE_PATH = os.path.join(ROOT, "_workspace", ".source_digest_state.json")
UA = "Mozilla/5.0 (compatible; ainews-source-digest/1.0)"


# ---------- sources.yaml 로딩 ----------

def load_layer_feeds(layer):
    """지정 계층의 [(name, rss_url)] 목록을 반환. PyYAML 우선, 없으면 경량 파서."""
    try:
        import yaml  # type: ignore
        data = yaml.safe_load(open(SOURCES_YAML, encoding="utf-8"))
        feeds = []
        for entry in (data.get(layer) or []):
            if entry.get("feed") == "rss" and entry.get("rss"):
                feeds.append((entry.get("name", "?"), entry["rss"]))
        return feeds
    except ImportError:
        return _light_parse(layer)


def _light_parse(layer):
    """sources.yaml의 제한된 구조만 파싱(PyYAML 부재 시). 최상위 'layer:' 블록 안의
    '- name:' 아이템에서 name/rss/feed를 추출해 feed==rss인 것만 반환."""
    feeds, cur, in_layer, item = [], None, False, {}
    for raw in open(SOURCES_YAML, encoding="utf-8"):
        line = raw.rstrip("\n")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if re.match(r"^[A-Za-z_]+:\s*$", line):           # 최상위 키 (corporate:, conference:, reuse:)
            if item:
                _flush(item, in_layer, feeds); item = {}
            in_layer = (line.strip().rstrip(":") == layer)
            continue
        if not in_layer:
            continue
        m = re.match(r"^\s*-\s*name:\s*(.+)$", line)        # 새 아이템 시작
        if m:
            _flush(item, True, feeds)
            item = {"name": m.group(1).strip()}
            continue
        m = re.match(r"^\s*(rss|feed|url):\s*(.+)$", line)
        if m and item:
            item[m.group(1)] = m.group(2).strip()
    _flush(item, in_layer, feeds)
    return feeds


def _flush(item, in_layer, feeds):
    if in_layer and item and item.get("feed") == "rss" and item.get("rss"):
        feeds.append((item["name"], item["rss"]))


# ---------- 피드 파싱 ----------

def fetch(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def strip_ns(tag):
    return tag.rsplit("}", 1)[-1].lower()


def parse_feed(xml_bytes, source_name):
    """RSS2.0 / Atom 모두 처리. [{title, url, published}] 반환."""
    out = []
    root = ET.fromstring(xml_bytes)
    # RSS: channel/item, Atom: feed/entry
    nodes = [e for e in root.iter() if strip_ns(e.tag) in ("item", "entry")]
    for n in nodes:
        title = link = pub = ""
        for c in list(n):
            t = strip_ns(c.tag)
            if t == "title" and not title:
                title = (c.text or "").strip()
            elif t == "link" and not link:
                link = (c.get("href") or c.text or "").strip()  # Atom=href, RSS=text
            elif t in ("pubdate", "published", "updated", "date") and not pub:
                pub = (c.text or "").strip()
        if title and link:
            out.append({"title_orig": title, "url": link,
                        "published": normalize_date(pub), "primary_source": source_name})
    return out


def normalize_date(s):
    if not s:
        return ""
    for parser in (lambda x: parsedate_to_datetime(x),
                   lambda x: datetime.fromisoformat(x.replace("Z", "+00:00"))):
        try:
            return parser(s).date().isoformat()
        except Exception:
            continue
    return ""


# ---------- state ----------

def load_state():
    try:
        return set(json.load(open(STATE_PATH, encoding="utf-8")).get("seen", []))
    except Exception:
        return set()


def save_state(seen):
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    seen = list(seen)[-5000:]  # 무한 증가 방지
    json.dump({"seen": seen, "updated": datetime.now(timezone.utc).isoformat()},
              open(STATE_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


# ---------- main ----------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--layer", required=True, choices=["corporate", "conference"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--days", type=int, default=3, help="최근 N일 항목만(날짜 미상은 포함)")
    ap.add_argument("--no-state", action="store_true", help="state 비교/갱신 생략")
    args = ap.parse_args()

    feeds = load_layer_feeds(args.layer)
    if not feeds:
        print(f"[warn] '{args.layer}' 계층에 rss 피드 없음(scrape 원천은 에이전트가 직접 확인).",
              file=sys.stderr)

    seen = set() if args.no_state else load_state()
    cutoff = (datetime.now(timezone.utc).date() - timedelta(days=args.days)).isoformat()
    items, errors = [], []

    for name, url in feeds:
        try:
            entries = parse_feed(fetch(url), name)
        except Exception as e:
            errors.append(f"{name}: {type(e).__name__} {e}")
            continue
        for it in entries:
            if it["url"] in seen:
                continue
            if it["published"] and it["published"] < cutoff:
                continue
            it.update({"layer": args.layer, "title_ko": "", "summary_ko": "", "image_url": ""})
            items.append(it)
            seen.add(it["url"])

    if not args.no_state:
        save_state(seen)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    json.dump({"layer": args.layer,
               "collected_at": datetime.now(timezone.utc).isoformat(),
               "items": items, "feed_errors": errors},
              open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    print(f"[ok] layer={args.layer} 신규 {len(items)}건 → {args.out}"
          + (f" (피드 오류 {len(errors)}건)" if errors else ""))
    print("    enrich(title_ko/summary_ko/image_url)와 scrape 계열 원천 확인은 에이전트가 수행.")


if __name__ == "__main__":
    main()
