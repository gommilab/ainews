#!/usr/bin/env python3
"""Top 20 데일리 뉴스 정적 포털 빌더 — GitHub Pages 게시용.

reports/{date}/top20.json (영속 커밋분 전체)을 읽어 news.html 한 장으로 렌더한다.
- 기본은 가장 최근 날짜(오늘)의 Top 20을 보여준다.
- 날짜 셀렉터로 이전 날짜 목록을 조회한다(정적: 전 날짜 데이터를 페이지에 임베드 후 클라이언트 전환).
- 각 항목: 순위 · 한글제목(클릭=원문 새 탭) · 원문 제목 병기 · 출처명 · 일자.

외부 의존성 없음(표준 라이브러리).
실행:  python3 webapp/build_news_static.py
"""
import html
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS = os.path.join(ROOT, "reports")
OUT_HTML = os.path.join(ROOT, "index.html")  # Top 20 뉴스를 사이트 랜딩으로 사용
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def esc(s):
    return html.escape(str(s or ""))


def render_items_html(items):
    """서버사이드 초기 렌더(무JS에서도 보이도록). JS render()와 동일한 마크업."""
    rows = []
    for it in items:
        cls = ' class="t1"' if it.get("rank") == 1 else ""
        to = (it.get("title_orig") or "").strip()
        show_orig = to and to != (it.get("title_ko") or "").strip()
        orig = f'<div class="orig">{esc(to)}</div>' if show_orig else ""
        url = it.get("url") or ""
        title = esc(it.get("title_ko"))
        link = f'<a href="{esc(url)}" target="_blank" rel="noopener">{title}</a>' if url else title
        rows.append(
            f'<li{cls}><p class="ttl">{link}</p>{orig}'
            f'<div class="meta"><span class="src">{esc(it.get("source"))}</span>'
            f'<span class="dot">·</span>{esc(it.get("published"))}</div></li>'
        )
    return "\n".join(rows)


def load_all():
    """{date: top20dict} (날짜 desc)."""
    out = {}
    if not os.path.isdir(REPORTS):
        return out
    for date in os.listdir(REPORTS):
        if not DATE_RE.match(date):
            continue
        path = os.path.join(REPORTS, date, "top20.json")
        if not os.path.isfile(path):
            continue
        try:
            with open(path, encoding="utf-8") as f:
                out[date] = json.load(f)
        except (OSError, ValueError):
            continue
    return dict(sorted(out.items(), key=lambda kv: kv[0], reverse=True))


def build():
    data = load_all()
    dates = list(data.keys())
    latest = dates[0] if dates else ""

    # 전 날짜 데이터를 JSON으로 임베드 → 클라이언트에서 셀렉터로 전환
    embed = {d: data[d].get("items", []) for d in dates}
    options = "".join(
        f'<option value="{esc(d)}">{esc(d)} · {len(data[d].get("items", []))}건</option>'
        for d in dates
    )
    empty = not dates

    page = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI 뉴스 Top 20 — AI Outlook</title>
<meta name="description" content="매일 06:00 KST 엄선한 글로벌 AI 뉴스 Top 20 — 제목·출처·일자, 날짜별 아카이브">
<style>
*{{box-sizing:border-box}}
body{{margin:0;font-family:'Pretendard','Apple SD Gothic Neo',-apple-system,'Malgun Gothic',sans-serif;
background:#f4f6f9;color:#0f172a;line-height:1.55}}
.top{{background:#14213d;color:#fff;padding:14px 20px;display:flex;gap:16px;align-items:center;flex-wrap:wrap}}
.top .brand{{font-weight:800;letter-spacing:-.3px;font-size:15px}}
.top a{{color:#cbd5e1;text-decoration:none;font-size:14px}}.top a:hover{{color:#fff}}
.top a.brand{{color:#fff}}
.top .sig{{color:#94a3b8;font-size:13px;font-weight:600}}
.top .sp{{flex:1}}
.wrap{{max-width:880px;margin:0 auto;padding:24px 18px 60px}}
h1{{font-size:22px;margin:2px 0 4px;letter-spacing:-.4px}}
.sub{{color:#64748b;font-size:13.5px;margin-bottom:16px}}
.bar{{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:14px}}
.bar label{{font-size:13px;color:#475569;font-weight:700}}
select{{font-size:14px;padding:7px 10px;border:1px solid #cbd5e1;border-radius:8px;background:#fff;color:#0f172a}}
ol.list{{list-style:none;margin:0;padding:0;counter-reset:r}}
ol.list li{{background:#fff;border:1px solid #e6e9ef;border-radius:11px;padding:13px 15px 13px 50px;
margin-bottom:9px;position:relative}}
ol.list li::before{{counter-increment:r;content:counter(r);position:absolute;left:13px;top:13px;
width:26px;height:26px;border-radius:7px;background:#14213d;color:#fff;font-weight:800;font-size:13px;
display:flex;align-items:center;justify-content:center}}
ol.list li.t1::before{{background:#14213d}}
.ttl{{font-size:15.5px;font-weight:700;line-height:1.4;margin:0}}
.ttl a{{color:#0f172a;text-decoration:none}}.ttl a:hover{{color:#1d4ed8;text-decoration:underline}}
.orig{{font-size:12.5px;color:#94a3b8;margin-top:3px;line-height:1.35}}
.meta{{font-size:12.5px;color:#64748b;margin-top:6px}}
.meta .src{{font-weight:700;color:#1d4ed8}}
.meta .dot{{color:#cbd5e1;margin:0 6px}}
.empty{{background:#fff;border:1px dashed #cbd5e1;border-radius:12px;padding:44px;text-align:center;color:#64748b}}
.foot{{margin-top:30px;padding-top:14px;border-top:1px solid #e6e9ef;color:#94a3b8;
font-size:11.5px;line-height:1.55;text-align:center}}
</style></head><body>
<header class="top"><a class="brand" href="./">📰 AI Outlook</a>
<a href="./">Top 20 뉴스</a><a href="digest.html">Issue 리포트</a>
<span class="sp"></span><span class="sig">@gommilab</span></header>
<main class="wrap">
<h1>Top 20 뉴스</h1>
<div class="sub">매일 글로벌 정보채널로부터 AI 기술·정책 동향을 통합 수집하여 제공합니다.</div>
"""

    if empty:
        page += '<div class="empty">아직 집계된 뉴스 목록이 없습니다.</div>\n'
    else:
        page += f"""<div class="bar">
<label for="d">날짜</label>
<select id="d" onchange="render(this.value)">{options}</select>
</div>
<ol class="list" id="list">
{render_items_html(data[latest].get("items", []))}
</ol>
<script>
var DATA = {json.dumps(embed, ensure_ascii=False)};
function esc(s){{return String(s==null?'':s).replace(/[&<>\"]/g,function(c){{
return {{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}}[c];}});}}
function render(date){{
  var items = DATA[date] || [];
  var h = '';
  for (var i=0;i<items.length;i++){{
    var it = items[i];
    var cls = it.rank===1 ? ' class="t1"' : '';
    var to = (it.title_orig||'').trim();
    var orig = (to && to !== (it.title_ko||'').trim()) ? '<div class="orig">'+esc(to)+'</div>' : '';
    var link = it.url
      ? '<a href="'+esc(it.url)+'" target="_blank" rel="noopener">'+esc(it.title_ko)+'</a>'
      : esc(it.title_ko);
    h += '<li'+cls+'><p class="ttl">'+link+'</p>'+orig
       + '<div class="meta"><span class="src">'+esc(it.source)+'</span>'
       + '<span class="dot">·</span>'+esc(it.published)+'</div></li>';
  }}
  document.getElementById('list').innerHTML = h;
}}
render('{latest}');
</script>
"""

    page += """<div class="foot">※ 공개된 출처를 자동 수집·요약한 참고용 정보로, 내용의 정확성·완전성을 보장하지 않습니다.<br>저작권은 각 원 출처에 있으며, 정확한 내용은 원문 링크를 확인하시기 바랍니다.</div>
</main></body></html>"""

    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"[ok] Top 20 랜딩 → {os.path.relpath(OUT_HTML, ROOT)} (날짜 {len(dates)}개, 최신 {latest or '-'})")


if __name__ == "__main__":
    build()
