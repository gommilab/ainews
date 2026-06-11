#!/usr/bin/env python3
"""HTML → PDF 변환기 — source-pdf-digest.

엔진 폴백 체인(설치된 것을 자동 선택):
  1) WeasyPrint   (권장; 한글 폰트 임베드·@page paged-media 우수)
  2) wkhtmltopdf  (CLI 바이너리)
  3) Playwright   (headless Chromium, print_to_pdf)
모두 없으면 설치 안내를 출력하고 비정상 종료(코드 3). HTML은 그대로 보존된다.

사용:  python3 html_to_pdf.py <input.html> <output.pdf>
"""
import os
import shutil
import subprocess
import sys


def via_weasyprint(src, dst):
    from weasyprint import HTML  # type: ignore
    HTML(filename=src).write_pdf(dst)
    return "weasyprint"


def via_wkhtmltopdf(src, dst):
    exe = shutil.which("wkhtmltopdf")
    if not exe:
        raise FileNotFoundError("wkhtmltopdf not on PATH")
    subprocess.run([exe, "--enable-local-file-access", "--quiet", src, dst],
                   check=True)
    return "wkhtmltopdf"


def via_playwright(src, dst):
    from playwright.sync_api import sync_playwright  # type: ignore
    url = "file://" + os.path.abspath(src)
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page()
        page.goto(url, wait_until="networkidle")
        page.pdf(path=dst, format="A4",
                 margin={"top": "15mm", "bottom": "15mm", "left": "15mm", "right": "15mm"},
                 print_background=True)
        b.close()
    return "playwright"


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    src, dst = sys.argv[1], sys.argv[2]
    if not os.path.isfile(src):
        print(f"[err] 입력 HTML 없음: {src}", file=sys.stderr)
        sys.exit(2)

    errors = []
    for engine in (via_weasyprint, via_wkhtmltopdf, via_playwright):
        try:
            used = engine(src, dst)
            print(f"[ok] PDF 생성({used}) → {dst}")
            return
        except Exception as e:
            errors.append(f"{engine.__name__}: {type(e).__name__} {e}")

    print("[err] 사용 가능한 PDF 엔진이 없습니다. HTML은 보존됨: " + src, file=sys.stderr)
    for e in errors:
        print("   - " + e, file=sys.stderr)
    print("   설치 예: pip install weasyprint  (또는)  apt-get install wkhtmltopdf  (또는)  "
          "pip install playwright && playwright install chromium", file=sys.stderr)
    sys.exit(3)


if __name__ == "__main__":
    main()
