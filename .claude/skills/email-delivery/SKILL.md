---
name: email-delivery
description: 완성된 HTML 브리핑을 gommi72@naver.com으로 HTML 메일 발송하는 절차. 클라우드 예약의 정식 자동발송은 Google Apps Script 웹훅(HTTPS), 로컬 점검은 Gmail MCP 드래프트를 쓴다. (SMTP는 클라우드에서 포트 차단되어 보조 경로.) mail-dispatcher 에이전트가 브리핑을 발송할 때, 이메일을 보낼 때 반드시 사용한다.
---

# email-delivery — 메일 발송 절차

완성된 `02_brief.html`을 **gommi72@naver.com**으로 HTML 메일 발송한다.

발송 경로(상황에 맞게):
- **A. 웹훅 자동발송 (클라우드 예약의 기본):** Apps Script 웹앱에 HTTPS POST → 그쪽 MailApp이 발송. SMTP 포트 차단을 443으로 우회. 손 안 대고 도착.
- **B. Gmail MCP 드래프트 (로컬 수동 점검):** 임시보관함에 작성만 됨(커넥터에 send 없음). 사용자가 [보내기] 필요. 디자인 미리보기용.
- **C. SMTP (보조):** `scripts/send_brief_smtp.py`. 포트(587)가 열린 로컬/환경에서만. 클라우드 예약 환경은 587 egress가 막혀 실패하므로 A를 쓴다.

## A. 웹훅 자동발송 (권장·클라우드 기본)
번들: 발송 스크립트 `scripts/send_brief_webhook.py`, 수신 웹앱 코드 `assets/apps_script_mailer.gs`.

1. (1회 준비) `assets/apps_script_mailer.gs`를 Google Apps Script 웹앱으로 배포한다(파일 상단 주석의 배포 절차). 스크립트 속성 `SECRET` 설정 후 /exec URL 확보.
2. 자격은 **환경변수**에서만 읽는다(코드/로그에 비밀 출력 금지):
   - `MAIL_WEBHOOK_URL` = Apps Script /exec URL
   - `MAIL_WEBHOOK_SECRET` = 위 `SECRET`과 동일한 공유 비밀
   - `MAIL_TO` = 수신주소(기본 gommi72@naver.com)
3. 실행:
   ```bash
   python3 scripts/send_brief_webhook.py --html <workspace>/02_brief.html --subject "<subject>"
   ```
   (HTTPS POST JSON {secret,to,subject,html}. 응답 `ok:true` 또는 HTTP 200이면 성공.)
4. 종료코드 0이면 성공. 아니면 stderr 사유를 `03_sent.txt`에 기록하고 폴백.

**보안:** 웹훅은 공유 비밀로 보호되고, 발송은 Apps Script 소유 Google 계정(전용 발송 계정 권장)에서 나간다. URL·비밀은 환경변수로만 둔다.

## B. Gmail MCP 드래프트 (수동/테스트)
로컬 세션에서 디자인 미리보기·테스트용. **주의: claude.ai Gmail 커넥터에는 직접 '발송' 도구가 없고 `create_draft`만 있다.** 즉 임시보관함에 작성만 되고, 실제 전송은 사용자가 Gmail에서 [보내기]를 눌러야 한다(자동발송엔 부적합 → A를 쓴다).

1. ToolSearch로 `mcp__claude_ai_Gmail__create_draft`를 로드한다(인증 필요 시 `/mcp` → "claude.ai Gmail" 안내).
2. `create_draft` 호출: `to=["gommi72@naver.com"]`, `subject`, `htmlBody`=HTML 본문, `body`=플레인텍스트 대체본.
3. 반환된 draft id와 "드래프트 작성됨 — 사용자가 [보내기] 필요"를 `03_sent.txt`에 기록하고 사용자에게 안내한다.
- 한글 깨짐 방지: UTF-8.

## 폴백 (발송 불가 시)
다음의 경우 **조용히 실패하지 않는다**:
- 웹훅 설정(`MAIL_WEBHOOK_URL`/`MAIL_WEBHOOK_SECRET`) 부재
- 웹훅 응답 오류(ok:false / 비200) 1회 재시도 후 재실패
- (로컬) Gmail MCP 도구 부재/미인증

조치:
1. `03_sent.txt`에 "발송 실패: {사유}" + HTML 경로 기록.
2. 가능하면 PushNotification으로 "오늘 브리핑 발송 실패, 파일은 {경로}에 보존" 알림.
3. HTML 파일은 삭제하지 않고 보존 → 사용자가 수동 발송/확인 가능.
4. 웹훅 실패이고 로컬에 Gmail MCP가 있으면 드래프트(B)로라도 남긴다.

## 멱등성
- `03_sent.txt`에 같은 날짜 성공 기록이 있으면, 명시적 재발송 지시 없이는 다시 보내지 않는다(중복 방지).
