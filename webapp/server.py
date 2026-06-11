#!/usr/bin/env python3
"""AI 뉴스 브리핑 포털 — 일일/주간 리포트 뷰어 (목록형 UI).

_workspace/{YYYY-MM-DD}/01_collect_*.json 을 읽어
콘텐츠를 최신순 목록으로 보여준다. 제목 클릭 시 요약 펼침 + 원문 링크 + 닫기.
외부 의존성 없음(파이썬 표준 라이브러리).

실행:  python3 webapp/server.py [--port 8765] [--host 0.0.0.0]
"""
import argparse
import html
import json
import os
import re
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKSPACE = os.path.join(ROOT, "_workspace")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

SECTION_OF_SOURCE = {
    "global": "global", "aitimes": "aitimes",
    "huggingface": "tech", "github": "tech", "arxiv": "tech",
    "policy": "policy",
}
SECTIONS = {
    "global": {"emoji": "🌐", "title": "글로벌 AI 뉴스", "color": "#2563eb"},
    "aitimes": {"emoji": "📰", "title": "AI타임스", "color": "#0891b2"},
    "tech": {"emoji": "🛠️", "title": "기술 동향", "color": "#7c3aed"},
    "policy": {"emoji": "🏛️", "title": "글로벌 AI 정책", "color": "#9333ea"},
}
SECTION_ORDER = ["global", "aitimes", "tech", "policy"]
SUB_NAME = {"huggingface": "HuggingFace", "github": "GitHub", "arxiv": "arXiv", "aitimes": "AI타임스"}
COUNTRY_FLAG = {"미국": "🇺🇸", "EU": "🇪🇺", "중국": "🇨🇳", "일본": "🇯🇵", "영국": "🇬🇧"}


def esc(s):
    return html.escape(str(s or ""))


# ---------- 데이터 로딩 ----------

def list_report_dates():
    if not os.path.isdir(WORKSPACE):
        return []
    dates = []
    for name in os.listdir(WORKSPACE):
        if not DATE_RE.match(name):
            continue
        d = os.path.join(WORKSPACE, name)
        if any(f.startswith("01_collect_") and f.endswith(".json") for f in os.listdir(d)):
            dates.append(name)
    return sorted(dates, reverse=True)


def load_day(date_str):
    d = os.path.join(WORKSPACE, date_str)
    if not os.path.isdir(d):
        return None
    items = []
    for f in sorted(os.listdir(d)):
        m = re.match(r"01_collect_(.+)\.json$", f)
        if not m:
            continue
        source = m.group(1)
        section = SECTION_OF_SOURCE.get(source, "tech")
        try:
            data = json.load(open(os.path.join(d, f), encoding="utf-8"))
        except Exception:
            continue
        for it in data.get("items", []):
            items.append({**it, "_source": source, "_section": section, "_report": date_str})
    has_brief = os.path.isfile(os.path.join(d, "02_brief.html"))
    return {"date": date_str, "items": items, "has_brief": has_brief}


def load_all_items():
    items = []
    for ds in list_report_dates():
        items.extend(load_day(ds)["items"])
    return sort_items(items)


def sort_items(items):
    """게시일(없으면 리포트일) 최신순. 같은 날짜는 섹션 우선순위(글로벌→AI타임스→기술→정책)."""
    prio = {s: i for i, s in enumerate(SECTION_ORDER)}
    return sorted(
        items,
        key=lambda it: (it.get("published") or it.get("_report") or "", -prio.get(it["_section"], 99)),
        reverse=True,
    )


def iso_week_key(date_str):
    y, w, _ = datetime.strptime(date_str, "%Y-%m-%d").date().isocalendar()
    return f"{y}-W{w:02d}"


def weeks_index():
    weeks = {}
    for ds in list_report_dates():
        weeks.setdefault(iso_week_key(ds), []).append(ds)
    return dict(sorted(weeks.items(), reverse=True))


def source_label(it):
    sec, src = it["_section"], it["_source"]
    if sec == "global":
        return esc(it.get("media") or "글로벌")
    if sec == "policy":
        c = it.get("country", "")
        return f'{COUNTRY_FLAG.get(c, "🏛️")} {esc(c)}'
    return esc(SUB_NAME.get(src, src))


# ---------- 렌더링 (목록형) ----------

PAGE_CSS = """
:root{--bg:#f4f6f9;--card:#fff;--line:#e6e9ef;--ink:#0f172a;--mut:#64748b;--blue:#2563eb}
*{box-sizing:border-box}
body{margin:0;font-family:'Pretendard','Apple SD Gothic Neo',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Malgun Gothic',sans-serif;background:var(--bg);color:var(--ink);line-height:1.6}
a{color:inherit;text-decoration:none}
.top{position:sticky;top:0;z-index:10;background:#0f172a;color:#fff;padding:13px 20px;display:flex;align-items:center;gap:18px}
.top .brand{font-weight:800;font-size:16px}
.top nav{display:flex;gap:16px;font-size:14px;color:#cbd5e1;margin-left:auto}
.top nav a:hover{color:#fff}
.wrap{max-width:860px;margin:0 auto;padding:22px 18px 60px}
.head{margin:6px 0 16px}
.head h1{margin:0 0 4px;font-size:20px}
.head .sub{color:var(--mut);font-size:13.5px}
.filter{display:flex;flex-wrap:wrap;gap:7px;margin:14px 0 10px}
.filter button{font-size:13px;background:#fff;border:1px solid var(--line);border-radius:999px;padding:6px 13px;cursor:pointer;color:#475569}
.filter button.on{background:#0f172a;color:#fff;border-color:#0f172a}
.list{list-style:none;margin:0;padding:0;border:1px solid var(--line);border-radius:12px;overflow:hidden;background:#fff}
.row{border-bottom:1px solid var(--line)}
.row:last-child{border-bottom:none}
.rowhead{width:100%;background:none;border:0;text-align:left;display:flex;align-items:center;gap:12px;padding:13px 16px;cursor:pointer;font:inherit;color:inherit}
.rowhead:hover{background:#f8fafc}
.caret{color:#cbd5e1;font-size:11px;flex:none;transition:transform .15s}
.rowhead.open .caret{transform:rotate(90deg)}
.rtitle{flex:1;font-size:15px;font-weight:600;min-width:0}
.rowhead.open .rtitle{color:var(--blue)}
.rmeta{display:flex;align-items:center;gap:10px;flex:none}
.src{font-size:11.5px;font-weight:700;color:#475569;background:#f1f5f9;border-radius:6px;padding:3px 9px;white-space:nowrap}
.date{font-size:12px;color:#94a3b8;white-space:nowrap}
.panel[hidden]{display:none}
.panel{padding:2px 16px 16px 40px;background:#f8fafc;border-top:1px dashed var(--line)}
.panel .sum{margin:12px 0;color:#334155;font-size:14px;line-height:1.75}
.panel .acts{display:flex;gap:9px;flex-wrap:wrap}
.panel .acts a,.panel .acts button{font-size:13px;font-weight:700;border-radius:8px;padding:8px 14px;border:1px solid var(--line);cursor:pointer;font-family:inherit}
.panel .acts a.src-link{background:var(--blue);color:#fff;border-color:var(--blue)}
.panel .acts button.close{background:#fff;color:#64748b}
.empty{background:#fff;border:1px dashed var(--line);border-radius:12px;padding:40px;text-align:center;color:var(--mut)}
.foot-note{margin-top:36px;color:var(--mut);font-size:12px;text-align:center}
@media(max-width:540px){.date{display:none}.rmeta{gap:8px}.panel{padding-left:16px}}
"""

LIST_JS = """
function tg(b){var p=b.nextElementSibling;if(p.hasAttribute('hidden')){p.removeAttribute('hidden');b.classList.add('open');}else{p.setAttribute('hidden','');b.classList.remove('open');}}
function cls(x){var p=x.closest('.panel');p.setAttribute('hidden','');p.previousElementSibling.classList.remove('open');}
function flt(btn,sec){document.querySelectorAll('.filter button').forEach(function(b){b.classList.toggle('on',b===btn);});
document.querySelectorAll('.row').forEach(function(r){r.style.display=(sec==='all'||r.dataset.section===sec)?'':'none';});}
"""


def page(title, body):
    return f"""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title><style>{PAGE_CSS}</style></head><body>
<header class="top"><a class="brand" href="/">🗞️ AI 뉴스 브리핑</a>
<nav><a href="/">전체</a><a href="/digest">📡 심층 브리프</a><a href="/weekly">주간</a></nav></header>
<main class="wrap">{body}</main>
<div class="foot-note">harness-ainews-brief · 매일 06:00 KST 자동 수집</div>
<script>{LIST_JS}</script></body></html>"""


def render_row(it, idx):
    sec = it["_section"]
    emoji = SECTIONS[sec]["emoji"]
    title = esc(it.get("title_ko") or it.get("title_orig") or "(제목 없음)")
    url = esc(it.get("url") or "#")
    pub = esc(it.get("published") or it.get("_report") or "")
    summ = esc(it.get("summary_ko") or "(요약 없음)")
    src = source_label(it)
    cat = f' · {esc(it.get("category"))}' if (sec == "global" and it.get("category")) else ""
    return f"""<li class="row" data-section="{sec}">
<button class="rowhead" onclick="tg(this)">
<span class="caret">▶</span>
<span class="rtitle">{emoji} {title}</span>
<span class="rmeta"><span class="src">{src}{cat}</span><span class="date">{pub}</span></span>
</button>
<div class="panel" hidden>
<p class="sum">{summ}</p>
<div class="acts">
<a class="src-link" href="{url}" target="_blank" rel="noopener">🔗 원문 보기</a>
<button class="close" onclick="cls(this)">✕ 닫기</button>
</div></div></li>"""


def render_filter():
    chips = ['<button class="on" onclick="flt(this,\'all\')">전체</button>']
    for s in SECTION_ORDER:
        chips.append(f'<button onclick="flt(this,\'{s}\')">{SECTIONS[s]["emoji"]} {SECTIONS[s]["title"]}</button>')
    return f'<div class="filter">{"".join(chips)}</div>'


def render_list(items):
    if not items:
        return '<div class="empty">표시할 항목이 없습니다.</div>'
    rows = "".join(render_row(it, i) for i, it in enumerate(items))
    return render_filter() + f'<ul class="list">{rows}</ul>'


# ---------- 뷰 ----------

def view_dashboard():
    dates = list_report_dates()
    items = load_all_items()
    if not items:
        return page("AI 뉴스 브리핑", '<div class="empty">아직 생성된 리포트가 없습니다.</div>')
    head = f"""<div class="head"><h1>전체 콘텐츠</h1>
<div class="sub">최신순 · 총 {len(items)}건 · 일일 리포트 {len(dates)}개 · 최신 {esc(dates[0])}</div></div>"""
    return page("AI 뉴스 브리핑 — 전체", head + render_list(items))


def view_daily(date_str):
    day = load_day(date_str)
    if not day:
        return None
    dt = datetime.strptime(date_str, "%Y-%m-%d").date()
    wd = "월화수목금토일"[dt.weekday()]
    brief = f' · <a href="/brief/{date_str}" target="_blank" style="color:#2563eb">📧 발송본</a>' if day["has_brief"] else ""
    head = f"""<div class="head"><h1>📅 {esc(date_str)} ({wd})</h1>
<div class="sub">총 {len(day['items'])}건 · <a href="/weekly/{iso_week_key(date_str)}" style="color:#2563eb">주간 보기</a>{brief}</div></div>"""
    return page(f"{date_str} 리포트", head + render_list(sort_items(day["items"])))


def view_weekly(week_key=None):
    weeks = weeks_index()
    if not weeks:
        return page("주간", '<div class="empty">아직 리포트가 없습니다.</div>')
    if week_key is None or week_key not in weeks:
        week_key = next(iter(weeks))
    items = []
    for ds in weeks[week_key]:
        items.extend(load_day(ds)["items"])
    days = weeks[week_key]
    rng = f"{days[-1]} ~ {days[0]}" if len(days) > 1 else days[0]
    nav = " · ".join(
        (f'<b>{wk}</b>' if wk == week_key else f'<a href="/weekly/{wk}" style="color:#2563eb">{wk}</a>')
        for wk in weeks
    )
    head = f"""<div class="head"><h1>📊 {esc(week_key)} 주간</h1>
<div class="sub">{esc(rng)} · {len(days)}일치 · 총 {len(items)}건<br>{nav}</div></div>"""
    return page(f"{week_key} 주간", head + render_list(sort_items(items)))


def serve_brief(date_str):
    p = os.path.join(WORKSPACE, date_str, "02_brief.html")
    if os.path.isfile(p):
        return open(p, encoding="utf-8").read()
    return None


# ---------- 원천 심층 PDF 브리프 (source-pdf-digest) ----------

ROUND_KO = {"am": "아침", "pm": "저녁"}


def list_digests():
    """_workspace/{date}/digest-{round}/05_index.json 들을 최신순으로 수집."""
    out = []
    for ds in list_report_dates():
        d = os.path.join(WORKSPACE, ds)
        for name in sorted(os.listdir(d)):
            m = re.match(r"^digest-(am|pm)$", name)
            if not m:
                continue
            idx = os.path.join(d, name, "05_index.json")
            if not os.path.isfile(idx):
                continue
            try:
                meta = json.load(open(idx, encoding="utf-8"))
            except Exception:
                continue
            folder = os.path.join(d, name)
            meta["_date"] = ds
            meta["_round"] = m.group(1)
            meta["_has_pdf"] = os.path.isfile(os.path.join(folder, meta.get("pdf", "05_digest.pdf")))
            meta["_has_html"] = os.path.isfile(os.path.join(folder, "05_digest.html"))
            out.append(meta)
    return sorted(out, key=lambda x: (x["_date"], x["_round"]), reverse=True)


def serve_digest_file(date_str, rnd, kind):
    """kind: 'pdf' → 바이너리 PDF, 'html' → HTML 문자열."""
    folder = os.path.join(WORKSPACE, date_str, f"digest-{rnd}")
    if kind == "pdf":
        p = os.path.join(folder, "05_digest.pdf")
        return open(p, "rb").read() if os.path.isfile(p) else None
    p = os.path.join(folder, "05_digest.html")
    return open(p, encoding="utf-8").read() if os.path.isfile(p) else None


def view_digests():
    items = list_digests()
    if not items:
        return page("원천 심층 브리프", '<div class="empty">아직 생성된 심층 브리프가 없습니다.</div>')
    rows = []
    for it in items:
        d, rnd = it["_date"], it["_round"]
        title = esc(it.get("headline_ko") or "(제목 없음)")
        src = esc(it.get("primary_source") or "")
        lens = esc(it.get("perspective") or "")
        kind = esc(it.get("topic_kind") or "")
        pages = esc(it.get("pages") or "")
        links = []
        if it["_has_pdf"]:
            links.append(f'<a class="src-link" href="/pdf/{d}/{rnd}" target="_blank">📄 PDF 다운로드</a>')
        if it["_has_html"]:
            links.append(f'<a class="src-link" href="/digest/{d}/{rnd}" target="_blank" style="background:#475569">🔎 본문 보기</a>')
        rows.append(f"""<li class="row">
<button class="rowhead" onclick="tg(this)">
<span class="caret">▶</span>
<span class="rtitle">📡 {title}</span>
<span class="rmeta"><span class="src">{src}</span><span class="date">{esc(d)} {ROUND_KO.get(rnd, rnd)}</span></span>
</button>
<div class="panel" hidden>
<p class="sum">관점: <b>{lens}</b> · 주제: {kind} · {pages}p · 원천: {src}</p>
<div class="acts">{''.join(links)}<button class="close" onclick="cls(this)">✕ 닫기</button></div>
</div></li>""")
    head = f"""<div class="head"><h1>📡 원천 심층 브리프</h1>
<div class="sub">aitimes 상류 원천 직접 감시 · 핫이슈 1건 심층분석 · 총 {len(items)}건</div></div>"""
    return page("원천 심층 브리프", head + f'<ul class="list">{"".join(rows)}</ul>')


# ---------- HTTP ----------

class Handler(BaseHTTPRequestHandler):
    def _send(self, body, code=200, ctype="text/html; charset=utf-8"):
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_bytes(self, data, ctype, filename=None):
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        if filename:
            self.send_header("Content-Disposition", f'inline; filename="{filename}"')
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = urlparse(self.path).path.rstrip("/") or "/"
        try:
            if path == "/":
                return self._send(view_dashboard())
            if path == "/weekly":
                return self._send(view_weekly())
            m = re.match(r"^/weekly/(\d{4}-W\d{2})$", path)
            if m:
                return self._send(view_weekly(m.group(1)))
            m = re.match(r"^/daily/(\d{4}-\d{2}-\d{2})$", path)
            if m:
                out = view_daily(m.group(1))
                return self._send(out) if out else self._send(page("404", '<div class="empty">리포트를 찾을 수 없습니다. <a href="/">← 전체</a></div>'), 404)
            m = re.match(r"^/brief/(\d{4}-\d{2}-\d{2})$", path)
            if m:
                out = serve_brief(m.group(1))
                return self._send(out) if out else self._send(page("404", '<div class="empty">발송본이 없습니다.</div>'), 404)
            if path == "/digest":
                return self._send(view_digests())
            m = re.match(r"^/pdf/(\d{4}-\d{2}-\d{2})/(am|pm)$", path)
            if m:
                pdf = serve_digest_file(m.group(1), m.group(2), "pdf")
                if pdf is not None:
                    return self._send_bytes(pdf, "application/pdf",
                                            f"digest_{m.group(1)}_{m.group(2)}.pdf")
                return self._send(page("404", '<div class="empty">PDF가 없습니다.</div>'), 404)
            m = re.match(r"^/digest/(\d{4}-\d{2}-\d{2})/(am|pm)$", path)
            if m:
                out = serve_digest_file(m.group(1), m.group(2), "html")
                return self._send(out) if out else self._send(page("404", '<div class="empty">본문이 없습니다.</div>'), 404)
            if path == "/api/reports":
                return self._send(json.dumps({"dates": list_report_dates(),
                                              "weeks": weeks_index()}, ensure_ascii=False),
                                  ctype="application/json; charset=utf-8")
            self._send(page("404", '<div class="empty">페이지를 찾을 수 없습니다. <a href="/">← 전체</a></div>'), 404)
        except Exception as e:
            self._send(page("오류", f'<div class="empty">서버 오류: {esc(e)}</div>'), 500)

    def log_message(self, *a):
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8765)))
    ap.add_argument("--host", default="0.0.0.0")
    args = ap.parse_args()
    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"AI 뉴스 브리핑 포털(목록형) → http://localhost:{args.port}")
    print(f"리포트 소스: {WORKSPACE}")
    srv.serve_forever()


if __name__ == "__main__":
    main()
