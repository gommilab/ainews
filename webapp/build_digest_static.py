#!/usr/bin/env python3
"""정적 digest 포털 빌더 — GitHub Pages 게시용.

_workspace/{date}/digest-{round}/05_index.json + 05_digest.pdf 를 읽어:
  1) reports/{date}/digest-{round}.pdf 로 PDF 복사(Pages가 직접 서빙·다운로드)
  2) digest.html (최신순 목록 + PDF 링크) 생성

원격 루틴이 PDF 생성 후 이 스크립트를 돌려 결과를 저장소에 커밋하면,
GitHub Pages가 https://gommilab.github.io/ainews/digest.html 과
reports/.../*.pdf 를 공개 서빙한다. 외부 의존성 없음(표준 라이브러리).

실행:  python3 webapp/build_digest_static.py
"""
import html
import json
import os
import re
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKSPACE = os.path.join(ROOT, "_workspace")
REPORTS = os.path.join(ROOT, "reports")
OUT_HTML = os.path.join(ROOT, "digest.html")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ROUND_KO = {"am": "아침", "pm": "저녁"}


def esc(s):
    return html.escape(str(s or ""))


def collect():
    """digest-{round} 폴더들을 스캔해 메타+PDF경로 목록을 최신순 반환."""
    items = []
    if not os.path.isdir(WORKSPACE):
        return items
    for date in sorted(os.listdir(WORKSPACE), reverse=True):
        if not DATE_RE.match(date):
            continue
        ddir = os.path.join(WORKSPACE, date)
        for name in sorted(os.listdir(ddir)):
            m = re.match(r"^digest-(am|pm)$", name)
            if not m:
                continue
            rnd = m.group(1)
            folder = os.path.join(ddir, name)
            idx = os.path.join(folder, "05_index.json")
            pdf = os.path.join(folder, "05_digest.pdf")
            if not os.path.isfile(idx):
                continue
            try:
                meta = json.load(open(idx, encoding="utf-8"))
            except Exception:
                continue
            rel_pdf = None
            if os.path.isfile(pdf):
                dst_dir = os.path.join(REPORTS, date)
                os.makedirs(dst_dir, exist_ok=True)
                dst = os.path.join(dst_dir, f"digest-{rnd}.pdf")
                shutil.copyfile(pdf, dst)
                rel_pdf = f"reports/{date}/digest-{rnd}.pdf"
            meta.update({"_date": date, "_round": rnd, "_pdf": rel_pdf})
            items.append(meta)
    items.sort(key=lambda x: (x["_date"], x["_round"]), reverse=True)
    return items


CSS = """
*{box-sizing:border-box}
body{margin:0;font-family:'Pretendard','Apple SD Gothic Neo',-apple-system,'Malgun Gothic',sans-serif;
background:#f4f6f9;color:#0f172a;line-height:1.6}
.top{background:#14213d;color:#fff;padding:14px 20px;display:flex;gap:16px;align-items:center}
.top .brand{font-weight:800}
.top a{color:#cbd5e1;text-decoration:none;font-size:14px}.top a:hover{color:#fff}
.wrap{max-width:860px;margin:0 auto;padding:24px 18px 60px}
h1{font-size:21px;margin:4px 0}
.sub{color:#64748b;font-size:13.5px;margin-bottom:18px}
.card{background:#fff;border:1px solid #e6e9ef;border-radius:12px;padding:16px 18px;margin-bottom:12px}
.card .meta{font-size:12px;color:#94a3b8;margin-bottom:5px}
.card .ttl{font-size:16px;font-weight:700;line-height:1.4;margin-bottom:8px}
.badge{display:inline-block;font-size:11.5px;font-weight:700;border-radius:6px;padding:2px 9px;margin-right:5px}
.b-src{background:#14213d;color:#fff}.b-lens{background:#1d4ed8;color:#fff}.b-kind{background:#eef2f7;color:#475569}
.dl{display:inline-block;margin-top:10px;background:#1d4ed8;color:#fff;font-weight:700;font-size:13.5px;
border-radius:8px;padding:8px 16px;text-decoration:none}
.dl:hover{background:#1e40af}
.empty{background:#fff;border:1px dashed #cbd5e1;border-radius:12px;padding:40px;text-align:center;color:#64748b}
.foot{margin-top:36px;color:#94a3b8;font-size:12px;text-align:center}
"""


def render(items):
    if items:
        cards = []
        for it in items:
            d, rnd = it["_date"], it["_round"]
            badges = (f'<span class="badge b-src">{esc(it.get("primary_source"))}</span>'
                      f'<span class="badge b-kind">{esc(it.get("topic_kind"))}</span>'
                      f'<span class="badge b-lens">{esc(it.get("perspective"))} 관점</span>')
            dl = (f'<a class="dl" href="{esc(it["_pdf"])}" target="_blank">📄 PDF 다운로드 '
                  f'({esc(it.get("pages"))}p)</a>') if it.get("_pdf") else \
                 '<span style="color:#ef4444;font-size:13px">PDF 준비 중</span>'
            cards.append(f"""<div class="card">
<div class="meta">📡 {esc(d)} · {ROUND_KO.get(rnd, rnd)} 회차</div>
<div class="ttl">{esc(it.get("headline_ko"))}</div>
<div>{badges}</div>
{dl}
</div>""")
        body = "".join(cards)
    else:
        body = '<div class="empty">아직 생성된 심층 브리프가 없습니다.</div>'
    return f"""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI 원천 동향 데일리 — 심층 브리프</title><style>{CSS}</style></head><body>
<header class="top"><span class="brand">📡 AI 원천 동향 데일리</span>
<a href="index.html">← 랜딩</a><a href="https://github.com/gommilab/ainews" target="_blank">GitHub</a></header>
<main class="wrap">
<h1>원천 심층 브리프</h1>
<div class="sub">aitimes.kr 상류 1차 원천을 직접 감시 · 그날 핫이슈 1건 심층분석 · A4 1~2p PDF · 하루 2회</div>
{body}
<div class="foot">harness-ainews-brief · 매일 06:00·18:00 KST 자동 생성 · 과학기술 연구자·정책자용</div>
</main></body></html>"""


def main():
    items = collect()
    open(OUT_HTML, "w", encoding="utf-8").write(render(items))
    print(f"[ok] digest.html 생성 · 브리프 {len(items)}건 · PDF "
          f"{sum(1 for x in items if x.get('_pdf'))}건 → reports/")
    for it in items:
        print(f"   - {it['_date']} {it['_round']}: {it.get('headline_ko','')[:40]} "
              f"({it.get('_pdf') or 'PDF 없음'})")


if __name__ == "__main__":
    main()
