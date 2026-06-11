/**
 * AI 뉴스 브리핑 메일 발송용 Google Apps Script 웹앱.
 *
 * 동작: 외부에서 HTTPS POST(JSON)를 받아, 공유 비밀(secret) 확인 후
 *       MailApp으로 HTML 메일을 발송한다. SMTP 포트 차단 환경(클라우드 예약 실행)에서
 *       443 포트만으로 메일을 보내기 위한 우회 경로다.
 *
 * 배포 방법:
 *  1) https://script.google.com → 새 프로젝트 → 이 코드 붙여넣기.
 *  2) 프로젝트 설정(톱니) → 스크립트 속성 → 속성 추가: SECRET = <긴 랜덤 문자열>.
 *     (이 값이 호출 측 환경변수 MAIL_WEBHOOK_SECRET 와 같아야 한다.)
 *  3) 배포 → 새 배포 → 유형: 웹 앱 → 실행 주체: 나(Me) / 액세스 권한: 모든 사용자(Anyone)
 *     → 배포 → 권한 승인 → /exec 로 끝나는 웹앱 URL 복사.
 *     (이 URL 이 호출 측 환경변수 MAIL_WEBHOOK_URL.)
 *  4) 발송 계정 = 이 스크립트를 소유한 Google 계정(전용 발송 계정 권장).
 *     MailApp 일일 한도(소비자 계정 100통)면 충분.
 *
 * 요청 본문(JSON): { "secret": "...", "to": "받는주소", "subject": "제목", "html": "<...>" }
 * 응답(JSON): { "ok": true } 또는 { "ok": false, "error": "..." }
 */
function doPost(e) {
  try {
    var body = JSON.parse(e.postData.contents);
    var secret = PropertiesService.getScriptProperties().getProperty('SECRET');
    if (!secret || body.secret !== secret) {
      return _json({ ok: false, error: 'unauthorized' });
    }
    if (!body.to || !body.subject || !body.html) {
      return _json({ ok: false, error: 'missing to/subject/html' });
    }
    MailApp.sendEmail({
      to: body.to,
      subject: body.subject,
      htmlBody: body.html,
      name: 'AI 뉴스 브리핑'
    });
    return _json({ ok: true });
  } catch (err) {
    return _json({ ok: false, error: String(err) });
  }
}

// 헬스체크용(브라우저에서 URL 열면 보임). 메일은 보내지 않는다.
function doGet() {
  return _json({ ok: true, hint: 'POST JSON {secret,to,subject,html} to send mail' });
}

function _json(obj) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
