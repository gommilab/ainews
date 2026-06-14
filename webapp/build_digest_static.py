#!/usr/bin/env python3
"""정적 digest 포털 빌더 — GitHub Pages 게시용 (저장소 영속).

핵심: 원격 루틴은 매번 새 클론 + _workspace는 gitignore라 휘발된다.
따라서 발행물은 reports/ 아래에 '저장소에 커밋되는' 형태로 영속한다.

동작:
  1) 신규 반영: _workspace/{date}/digest-{round}/ 의 05_index.json + 05_digest.pdf 를
     reports/{date}/digest-{round}.pdf 와 reports/{date}/digest-{round}.json 으로 복사·기록.
  2) 목록 생성: reports/ 전체(과거 커밋분 포함)를 스캔해 digest.html 을 누적 렌더.

→ 매 회차 reports/ 에 파일이 쌓이고 digest.html 이 전체 이력을 보여준다.
GitHub Pages가 digest.html 과 reports/.../*.pdf 를 공개 서빙·다운로드.
외부 의존성 없음(표준 라이브러리).

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
ROUND_KO = {"am": "am", "pm": "pm"}


def esc(s):
    return html.escape(str(s or ""))


def ingest_from_workspace():
    """_workspace의 신규 digest를 reports/(영속)로 복사·기록."""
    if not os.path.isdir(WORKSPACE):
        return 0
    n = 0
    for date in os.listdir(WORKSPACE):
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
            dst_dir = os.path.join(REPORTS, date)
            os.makedirs(dst_dir, exist_ok=True)
            if os.path.isfile(pdf):
                shutil.copyfile(pdf, os.path.join(dst_dir, f"digest-{rnd}.pdf"))
                meta["pdf"] = f"reports/{date}/digest-{rnd}.pdf"
            meta["date"], meta["round"] = date, rnd
            json.dump(meta, open(os.path.join(dst_dir, f"digest-{rnd}.json"), "w",
                                 encoding="utf-8"), ensure_ascii=False, indent=2)
            n += 1
    return n


def load_all_reports():
    """reports/ 전체(커밋된 이력 포함)에서 메타를 모아 최신순 반환."""
    items = []
    if not os.path.isdir(REPORTS):
        return items
    for date in os.listdir(REPORTS):
        if not DATE_RE.match(date):
            continue
        ddir = os.path.join(REPORTS, date)
        for f in os.listdir(ddir):
            m = re.match(r"^digest-(am|pm)\.json$", f)
            if not m:
                continue
            try:
                meta = json.load(open(os.path.join(ddir, f), encoding="utf-8"))
            except Exception:
                continue
            meta.setdefault("date", date)
            meta.setdefault("round", m.group(1))
            pdf_path = os.path.join(ddir, f"digest-{meta['round']}.pdf")
            meta["_has_pdf"] = os.path.isfile(pdf_path)
            items.append(meta)
    items.sort(key=lambda x: (x.get("date", ""), x.get("round", "")), reverse=True)
    return items


CSS = """
*{box-sizing:border-box}
body{margin:0;font-family:'Pretendard','Apple SD Gothic Neo',-apple-system,'Malgun Gothic',sans-serif;
background:#f4f6f9;color:#0f172a;line-height:1.6}
.top{background:#14213d;color:#fff;padding:14px 20px;display:flex;gap:16px;align-items:center}
.top .brand{font-weight:800;font-size:15px}
.top a{color:#cbd5e1;text-decoration:none;font-size:14px}.top a:hover{color:#fff}
.top a.brand{color:#fff}
.top .sig{color:#94a3b8;font-size:13px;font-weight:600}
.wrap{max-width:860px;margin:0 auto;padding:24px 18px 60px}
h1{font-size:21px;margin:4px 0}
.sub{color:#64748b;font-size:13.5px;margin-bottom:18px}
.card{background:#fff;border:1px solid #e6e9ef;border-radius:12px;padding:16px 18px;margin-bottom:12px}
.card .meta{font-size:12px;color:#94a3b8;margin-bottom:5px}
.card .rnd{display:inline-block;font-size:11px;font-weight:800;border-radius:5px;padding:1px 8px;
margin-right:6px;background:#1d4ed8;color:#fff;letter-spacing:.3px}
.card .ttl{font-size:16px;font-weight:700;line-height:1.4;margin:0}
.card .ttl-link{color:inherit;text-decoration:none}
.card .ttl-link:hover{color:#1d4ed8;text-decoration:underline}
.pdfbox{display:inline-block;font-size:10px;font-weight:700;letter-spacing:.5px;color:#64748b;
background:#eef2f7;border:1px solid #e2e8f0;border-radius:4px;padding:1px 6px;margin-left:7px;
vertical-align:middle;text-decoration:none}
a.pdfbox:hover{background:#e2e8f0;color:#0f172a}
.pdfbox.pending{color:#ef4444;background:#fef2f2;border-color:#fecaca}
.daygroup{margin-bottom:8px}
.dayhd{font-size:13px;font-weight:800;color:#14213d;margin:18px 0 9px;padding-bottom:5px;
border-bottom:2px solid #e6e9ef}
.top .sp{flex:1}
.badge{display:inline-block;font-size:11.5px;font-weight:700;border-radius:6px;padding:2px 9px;margin-right:5px}
.b-src{background:#14213d;color:#fff}.b-lens{background:#1d4ed8;color:#fff}.b-kind{background:#eef2f7;color:#475569}
.empty{background:#fff;border:1px dashed #cbd5e1;border-radius:12px;padding:40px;text-align:center;color:#64748b}
.foot{margin-top:30px;padding-top:14px;border-top:1px solid #e6e9ef;color:#94a3b8;
font-size:11.5px;line-height:1.55;text-align:center}
"""


def pdf_filename(date, headline):
    """다운로드 파일명 = '날짜 리포트제목.pdf' (파일명 불가 문자 제거)."""
    title = re.sub(r'[\\/:*?"<>|\r\n\t]', "", str(headline or "")).strip()
    title = re.sub(r"\s+", " ", title)
    base = f"{date or ''} {title}".strip() or "AI-Outlook"
    return f"{base}.pdf"


def render_card(it):
    d, rnd = it.get("date"), it.get("round")
    kws = it.get("keywords") or []
    if kws:
        badges = "".join(f'<span class="badge b-src">{esc(k)}</span>' for k in kws[:5])
    else:
        badges = (f'<span class="badge b-src">{esc(it.get("primary_source"))}</span>'
                  f'<span class="badge b-kind">{esc(it.get("topic_kind"))}</span>')
    sub = f'<div class="meta" style="margin:6px 0 0">{esc(it.get("subhead"))}</div>' \
        if it.get("subhead") else ""
    rnd_badge = f'<span class="rnd">{esc(ROUND_KO.get(rnd, rnd)).upper()}</span>'
    headline = esc(it.get("headline_ko"))
    if it.get("_has_pdf") and it.get("pdf"):
        # 제목 클릭 → PDF 보기. 옆의 'PDF' 박스 → '날짜 리포트제목.pdf' 파일명으로 다운로드
        fname = pdf_filename(d, it.get("headline_ko"))
        title = (f'{rnd_badge}<a class="ttl-link" href="{esc(it["pdf"])}" target="_blank">'
                 f'{headline}</a>'
                 f'<a class="pdfbox" href="{esc(it["pdf"])}" download="{html.escape(fname)}" '
                 f'title="{html.escape(fname)} 다운로드">PDF</a>')
    else:
        title = f'{rnd_badge}{headline}<span class="pdfbox pending">준비 중</span>'
    return f"""<div class="card">
<div class="ttl">{title}</div>
{sub}
<div style="margin-top:8px">{badges}</div>
</div>"""


def render(items):
    if items:
        # 날짜별 그룹(최신 날짜 먼저), 각 날짜 안에서 am·pm 정렬
        by_date = {}
        for it in items:
            by_date.setdefault(it.get("date"), []).append(it)
        groups = []
        for d in sorted(by_date, reverse=True):
            rounds = sorted(by_date[d], key=lambda x: x.get("round", ""))  # am, pm
            cards = "".join(render_card(it) for it in rounds)
            groups.append(f'<div class="daygroup"><div class="dayhd">📅 {esc(d)} '
                          f'· {len(rounds)}건</div>{cards}</div>')
        body = "".join(groups)
    else:
        body = '<div class="empty">아직 생성된 심층 브리프가 없습니다.</div>'
    return f"""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI Outlook — Issue 리포트</title><style>{CSS}</style></head><body>
<header class="top"><a class="brand" href="index.html">📄 AI Outlook</a>
<a href="index.html">Top 20 뉴스</a><a href="digest.html">Issue 리포트</a>
<span class="sp"></span><span class="sig">@gommilab</span></header>
<main class="wrap">
<h1>Issue 리포트</h1>
{body}
<div class="foot">※ 정보 출처로부터 자동 수집·분석한 참고용 브리프로, 내용의 정확성·완전성을 보장하지 않으며 투자·정책 판단의 근거로 사용할 수 없습니다.<br>저작권은 각 원 출처에 있습니다.</div>
</main></body></html>"""


def main():
    ingested = ingest_from_workspace()
    items = load_all_reports()
    open(OUT_HTML, "w", encoding="utf-8").write(render(items))
    print(f"[ok] 신규 반영 {ingested}건 · 포털 총 {len(items)}건 → digest.html (reports/ 영속)")
    for it in items[:6]:
        print(f"   - {it.get('date')} {it.get('round')}: "
              f"{(it.get('headline_ko') or '')[:38]} (pdf={'O' if it.get('_has_pdf') else 'X'})")


if __name__ == "__main__":
    main()
