#!/usr/bin/env python3
"""AI 뉴스 브리핑을 Google Apps Script 웹훅으로 발송한다(HTTPS 443).

SMTP 포트(587/465)가 막힌 클라우드 예약 환경에서 메일을 보내기 위한 경로.
Apps Script 웹앱(apps_script_mailer.gs 참고)에 JSON을 POST하면 그쪽 MailApp이 발송한다.

사용:
  send_brief_webhook.py --html <HTML경로> --subject "<제목>" [--to <수신주소>]

환경변수(코드/로그에 비밀 출력 금지):
  MAIL_WEBHOOK_URL     Apps Script 웹앱 /exec URL
  MAIL_WEBHOOK_SECRET  Apps Script 스크립트 속성 SECRET 과 동일한 공유 비밀
선택:
  MAIL_TO              기본 gommi72@naver.com (--to 미지정 시)

종료코드: 0 성공 / 1 발송오류 / 2 설정·입력 누락
"""
import argparse, json, os, sys, urllib.request


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", required=True)
    ap.add_argument("--subject", required=True)
    ap.add_argument("--to", default=os.environ.get("MAIL_TO", "gommi72@naver.com"))
    args = ap.parse_args()

    url = os.environ.get("MAIL_WEBHOOK_URL")
    secret = os.environ.get("MAIL_WEBHOOK_SECRET")
    if not url or not secret:
        print("ERROR: MAIL_WEBHOOK_URL/MAIL_WEBHOOK_SECRET 환경변수가 없습니다.", file=sys.stderr)
        return 2

    try:
        with open(args.html, encoding="utf-8") as f:
            html = f.read()
    except OSError as e:
        print(f"ERROR: HTML 파일을 읽을 수 없습니다: {e}", file=sys.stderr)
        return 2

    payload = json.dumps(
        {"secret": secret, "to": args.to, "subject": args.subject, "html": html}
    ).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            body = r.read().decode("utf-8", "replace")
            ok = ('"ok":true' in body.replace(" ", "")) or (r.status == 200)
            print(f"HTTP {r.status} {body[:300]}")
            return 0 if ok else 1
    except Exception as e:  # noqa: BLE001
        print(f"ERROR: 웹훅 발송 실패: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
