#!/usr/bin/env python3
"""AI 뉴스 브리핑을 SMTP(Gmail)로 자동 발송한다.

사용:
  send_brief_smtp.py --html <HTML경로> --subject "<제목>" [--to <수신주소>] [--text <플레인텍스트경로>]

자격증명은 환경변수에서 읽는다(프롬프트/코드에 넣지 않는다):
  SMTP_USER  발송 Gmail 주소(전용 발송 계정 권장)
  SMTP_PASS  Gmail 앱 비밀번호(2단계 인증 후 발급, 메일 전송만 가능, 즉시 폐기 가능)
선택 환경변수:
  SMTP_HOST  기본 smtp.gmail.com
  SMTP_PORT  기본 587 (STARTTLS)
  MAIL_TO    기본 gommi72@naver.com (--to 미지정 시)

종료코드: 0 성공 / 1 발송오류 / 2 자격증명·입력 누락
"""
import argparse, os, smtplib, ssl, sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", required=True, help="발송할 HTML 본문 파일")
    ap.add_argument("--subject", required=True, help="이메일 제목")
    ap.add_argument("--to", default=os.environ.get("MAIL_TO", "gommi72@naver.com"))
    ap.add_argument("--text", default=None, help="선택: 플레인텍스트 대체본 파일")
    args = ap.parse_args()

    user = os.environ.get("SMTP_USER")
    pw = os.environ.get("SMTP_PASS")
    if not user or not pw:
        print("ERROR: SMTP_USER/SMTP_PASS 환경변수가 설정되지 않았습니다.", file=sys.stderr)
        return 2

    host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    port = int(os.environ.get("SMTP_PORT", "587"))

    try:
        with open(args.html, encoding="utf-8") as f:
            html = f.read()
    except OSError as e:
        print(f"ERROR: HTML 파일을 읽을 수 없습니다: {e}", file=sys.stderr)
        return 2

    text = "이 메일은 HTML 형식입니다. HTML을 지원하는 메일 앱에서 확인하세요."
    if args.text and os.path.exists(args.text):
        with open(args.text, encoding="utf-8") as f:
            text = f.read()

    msg = MIMEMultipart("alternative")
    msg["Subject"] = args.subject
    msg["From"] = user
    msg["To"] = args.to
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid()
    msg.attach(MIMEText(text, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    ctx = ssl.create_default_context()
    try:
        with smtplib.SMTP(host, port, timeout=30) as s:
            s.ehlo()
            s.starttls(context=ctx)
            s.ehlo()
            s.login(user, pw)
            s.sendmail(user, [args.to], msg.as_string())
    except Exception as e:  # noqa: BLE001 - 어떤 실패든 명확히 보고
        print(f"ERROR: SMTP 발송 실패: {e}", file=sys.stderr)
        return 1

    print(f"OK: sent to {args.to}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
