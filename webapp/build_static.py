#!/usr/bin/env python3
"""정적 빌더 — server.py의 데이터/렌더 함수를 재사용해
GitHub Pages용 목록형 index.html(전체 콘텐츠, 최신순)을 생성한다.

사용:  python3 webapp/build_static.py [출력디렉토리]
기본 출력: webapp/landing/
"""
import os
import sys

import server  # 같은 디렉토리

OUT_DIR = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "landing")
PREVIEW_HREF = "preview/2026-06-07.html"  # 최신 발송본 정적 미리보기


def build_index():
    items = server.load_all_items()
    dates = server.list_report_dates()
    n = len(items)
    latest = dates[0] if dates else "-"
    body_head = f"""<div class="head"><h1>전체 콘텐츠</h1>
<div class="sub">최신순 · 총 {n}건 · 일일 리포트 {len(dates)}개 · 최신 {server.esc(latest)}
 · <a href="{PREVIEW_HREF}" style="color:#2563eb">📧 발송본 전체 보기</a></div></div>"""
    list_html = server.render_list(items) if items else '<div class="empty">아직 콘텐츠가 없습니다.</div>'

    html = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI 뉴스 브리핑 — 전체 콘텐츠</title>
<meta name="description" content="글로벌 AI 동향 일일·주간 브리핑 — 최신순 목록">
<style>{server.PAGE_CSS}</style></head><body>
<header class="top"><a class="brand" href="./">🗞️ AI 뉴스 브리핑</a>
<nav><a href="./">전체</a><a href="{PREVIEW_HREF}">발송본</a></nav></header>
<main class="wrap">{body_head}{list_html}</main>
<div class="foot-note">harness-ainews-brief · 매일 06:00 KST 자동 수집 · 라이브 포털(GCP)은 추후 연결</div>
<script>{server.LIST_JS}</script></body></html>"""

    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, "index.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"생성: {path}  (콘텐츠 {n}건)")


if __name__ == "__main__":
    build_index()
