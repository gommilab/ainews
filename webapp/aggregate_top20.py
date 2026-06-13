#!/usr/bin/env python3
"""Top 20 데일리 뉴스 집계기 — ainews 수집 전 소스를 통합·랭킹.

입력: _workspace/{date}/01_collect_*.json (global·aitimes·arxiv·github·huggingface·policy)
출력: reports/{date}/top20.json  (영속 커밋 → GitHub Pages 정적 포털이 읽음)

동작:
  1) 각 소스 JSON을 공통 레코드로 정규화(title_ko·title_orig·source·url·published·section)
  2) URL/제목 기준 중복 제거
  3) 결정적 점수(소스 tier + 카테고리 가중 + 최신성)로 정렬해 상위 20건
  4) reports/{date}/top20.json 기록

외부 의존성 없음(표준 라이브러리).
사용:  python3 webapp/aggregate_top20.py <YYYY-MM-DD>   # 생략 시 _workspace 최신 날짜
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKSPACE = os.path.join(ROOT, "_workspace")
REPORTS = os.path.join(ROOT, "reports")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TOP_N = 20
# Top 20에 반드시 각 1건 이상 포함을 보장할 기술 소스(그날 수집물이 있을 때만)
GUARANTEED_KEYS = ["arxiv", "huggingface", "github"]

# 소스별 메타: (section, 기본 출처명, tier 점수). tier가 높을수록 상위.
SOURCE_META = {
    "global":      ("global",  None,            100),  # media 필드 사용
    "aitimes":     ("aitimes", "AI타임스",       72),
    "policy":      ("policy",  None,             66),   # country 사용
    "huggingface": ("tech",    "Hugging Face",   60),
    "github":      ("tech",    "GitHub",         58),
    "arxiv":       ("tech",    "arXiv",          56),
}

# 카테고리/태그에 들어가면 가중치를 더하는 키워드(중요도 부스트)
CATEGORY_BOOST = [
    ("모델", 14), ("출시", 12), ("투자", 12), ("M&A", 12), ("인수", 10),
    ("반도체", 11), ("칩", 9), ("인프라", 9), ("규제", 10), ("소송", 9),
    ("안전", 8), ("공급망", 10), ("논문", 6), ("도입", 6),
]


def _date_value(published):
    """'2026-06-07' → 정수 키(최신일수록 큼). 파싱 실패 시 0."""
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", str(published or ""))
    if not m:
        return 0
    return int(m.group(1)) * 10000 + int(m.group(2)) * 100 + int(m.group(3))


def _norm_title(t):
    return re.sub(r"\s+", " ", str(t or "")).strip().lower()


def load_source(path, source_key):
    section, default_src, tier = SOURCE_META[source_key]
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return []
    label = data.get("label_ko") or default_src
    out = []
    for it in data.get("items") or []:
        # 출처명 결정
        if source_key == "global":
            source = it.get("media") or "글로벌 매체"
        elif source_key == "policy":
            c = it.get("country")
            source = (f"{c} 정책" if c else (label or "정책"))
        else:
            source = default_src or label
        cat = it.get("category") or it.get("tag") or ""
        out.append({
            "title_ko": it.get("title_ko") or it.get("title_orig") or "(제목 없음)",
            "title_orig": it.get("title_orig") or "",
            "source": source,
            "url": it.get("url") or "",
            "published": it.get("published") or "",
            "category": cat,
            "section": section,
            "_tier": tier,
            "_skey": source_key,
        })
    return out


def score(rec, newest):
    s = rec["_tier"]
    blob = f"{rec['category']} {rec['title_ko']}"
    for kw, w in CATEGORY_BOOST:
        if kw in blob:
            s += w
    # 최신성: 가장 최근 날짜와의 일수 차이만큼 감점(최대 -20)
    dv = _date_value(rec["published"])
    if dv and newest:
        gap_days = max(0, (newest - dv))  # 정수 키 차이(대략적; 같은 달이면 일수에 비례)
        s -= min(20, gap_days % 100 if gap_days < 100 else 20)
    return s


def aggregate(date):
    wdir = os.path.join(WORKSPACE, date)
    records = []
    for key in SOURCE_META:
        path = os.path.join(wdir, f"01_collect_{key}.json")
        if os.path.isfile(path):
            records.extend(load_source(path, key))

    # 중복 제거: URL 우선, 없으면 정규화 제목
    seen, deduped = set(), []
    for r in records:
        k = (r["url"].strip().rstrip("/").lower() or _norm_title(r["title_ko"]))
        if k in seen:
            continue
        seen.add(k)
        deduped.append(r)

    newest = max((_date_value(r["published"]) for r in deduped), default=0)
    deduped.sort(key=lambda r: (-score(r, newest), -_date_value(r["published"])))

    selected = deduped[:TOP_N]
    # 보장 슬롯: arxiv·huggingface·github가 그날 수집물이 있는데 Top N 밖이면,
    # 비(非)보장 소스 중 점수 최저 항목과 교체해 각 1건 이상 포함시킨다.
    if len(deduped) > TOP_N:
        present = {r["_skey"] for r in selected}
        for req in GUARANTEED_KEYS:
            if req in present:
                continue
            cand = next((r for r in deduped[TOP_N:] if r["_skey"] == req), None)
            if not cand:
                continue  # 그날 해당 소스 수집물 없음 → 건너뜀
            victim_idx = next((i for i in range(len(selected) - 1, -1, -1)
                               if selected[i]["_skey"] not in GUARANTEED_KEYS), len(selected) - 1)
            selected[victim_idx] = cand
            present.add(req)
        selected.sort(key=lambda r: (-score(r, newest), -_date_value(r["published"])))

    items = []
    for i, r in enumerate(selected, 1):
        items.append({
            "rank": i,
            "title_ko": r["title_ko"],
            "title_orig": r["title_orig"],
            "source": r["source"],
            "url": r["url"],
            "published": r["published"],
            "category": r["category"],
            "section": r["section"],
        })
    return {
        "date": date,
        "count": len(items),
        "items": items,
        "generator": "aggregate_top20",
    }


def main():
    if len(sys.argv) > 1 and DATE_RE.match(sys.argv[1]):
        date = sys.argv[1]
    else:
        dates = sorted([d for d in os.listdir(WORKSPACE)
                        if DATE_RE.match(d) and os.path.isdir(os.path.join(WORKSPACE, d))]) \
            if os.path.isdir(WORKSPACE) else []
        if not dates:
            print("[err] _workspace에 날짜 폴더가 없습니다.", file=sys.stderr)
            sys.exit(2)
        date = dates[-1]

    result = aggregate(date)
    if not result["items"]:
        print(f"[warn] {date}: 집계할 항목이 없습니다(01_collect_*.json 확인).", file=sys.stderr)
        sys.exit(1)

    outdir = os.path.join(REPORTS, date)
    os.makedirs(outdir, exist_ok=True)
    outpath = os.path.join(outdir, "top20.json")
    with open(outpath, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"[ok] Top {result['count']} 집계 → {os.path.relpath(outpath, ROOT)}")


if __name__ == "__main__":
    main()
