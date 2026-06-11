# AI 뉴스 브리핑 포털 (webapp)

`_workspace/{YYYY-MM-DD}/01_collect_*.json` 을 읽어 **일일/주간 리포트**를 웹으로 보여주는 뷰어. 외부 의존성 없음(파이썬 표준 라이브러리만 사용).

## 실행
```bash
python3 webapp/server.py            # 기본 포트 8765
python3 webapp/server.py --port 9000
```
백그라운드 상시 실행:
```bash
nohup python3 webapp/server.py >/tmp/ainews_portal.log 2>&1 &
```
종료:
```bash
pkill -f webapp/server.py
```

## 접속 URL
- 이 PC: http://localhost:8765
- 같은 네트워크의 다른 기기: http://<이 PC의 IP>:8765

## 경로(라우트)
| 경로 | 내용 |
|------|------|
| `/` | 대시보드 — 일일 리포트 목록(날짜·섹션별 건수) |
| `/daily/{YYYY-MM-DD}` | 해당 날짜 일일 리포트(섹션별 카드 + 이전/다음 이동) |
| `/weekly` | 최신 주 주간 리포트 |
| `/weekly/{YYYY-W##}` | 특정 ISO 주 주간 집계 |
| `/brief/{YYYY-MM-DD}` | 그날 실제 발송본 HTML(02_brief.html) 원본 |
| `/api/reports` | 보유 리포트 날짜·주 목록 JSON |

## 동작 원리
- 새 브리핑이 `_workspace/`에 생기면 **자동으로** 포털에 나타난다(서버 재시작 불필요).
- 주간 리포트는 ISO 주 단위로 그날그날 일일 데이터를 실시간 집계한다.
- 이미지가 없는 항목은 섹션 색상 + 이모지 배지로 폴백한다.

## 원격(외부망)에서 24시간 접속하려면
현재는 이 PC가 켜져 있고 서버가 떠 있는 동안만 접속된다. 어디서나 항상 접속하려면:
- 사내/홈 서버에 systemd 서비스로 등록 + 포트 포워딩, 또는
- Cloudflare Tunnel / ngrok 같은 터널로 공개 URL 발급, 또는
- 클라우드 호스팅(VM/컨테이너) 배포.
필요하면 이 중 하나로 셋업해줄 수 있다.
