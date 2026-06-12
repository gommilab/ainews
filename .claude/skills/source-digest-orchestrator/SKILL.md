---
name: source-digest-orchestrator
description: aitimes.kr 상류 원천을 직접 감시해 그날 가장 핫한 AI 이슈 1건을 선별·심층분석한 A4 1~2p PDF 분석 브리프를 만들어 웹포털에 게시하는 전체 워크플로우 오케스트레이터. "원천 동향 브리프/심층 브리프 만들어", "오늘의 핵심 이슈 분석해줘", "원천 PDF 리포트", 하루 2회(아침·저녁) 예약 실행 트리거 시, 그리고 "원천 브리프 다시/재실행/업데이트/저녁 회차/관점 바꿔/더 깊게/단신 보강/1위 말고 N위로" 등 후속 요청 시 반드시 이 스킬을 사용한다. (광역 HTML 메일 브리핑은 ainews-orchestrator를 쓴다 — 이 스킬은 PDF 심층 브리프 전용.)
---

# source-digest-orchestrator — 원천 핫이슈 심층 PDF 오케스트레이터

aitimes.kr이 한글화하기 전의 **상류 1차 원천**을 직접 감시 → 그날 **가장 핫한 1건** 선별 → **deep-research 심층 분석** → **A4 1~2p PDF** → **웹포털 게시**. 독자는 과학기술 연구자·정책자. 하루 2회(아침·저녁).

**실행 모드: 하이브리드** — 스캔은 병렬 서브에이전트(팬아웃), 선별·심층수집·분석·PDF는 순차 파이프라인.
**모든 Agent 호출은 `model: "opus"`.** 방법 세부는 `source-pdf-digest` 스킬을 따른다.

## 고정 설정
- 산출물 폴더: `_workspace/{date}/digest-{round}/` (date=KST 기준, round=`am`|`pm`)
- 전달: 웹포털 아카이브 게시 + on-demand PDF 다운로드 (메일 발송 없음)
- 분량: A4 1~2p 고정 / 핫이슈 1건 심층 + 푸터 단신 2~3건

## Phase 0: 컨텍스트 확인
1. KST 기준 오늘 `{date}`, 회차 `{round}` 결정. 예약: 아침 06:00→`am`, 저녁 18:00→`pm`. 수동 호출이면 현재 시각으로 추정하거나 사용자 지정을 따른다.
2. `_workspace/{date}/digest-{round}/` 존재 여부로 실행 모드 판별:
   - 없음 → **초기 실행**(Phase 1~4 전체)
   - 있음 + "관점 바꿔/더 깊게/단신 보강/특정 섹션" → **부분 재실행**(analyst만, `03_dossier.json` 재사용)
   - 있음 + "1위 말고 N위로/선별 다시" → collector 재선정(`02_selection.json` 후보 활용) → analyst 재작성
   - 있음 + "처음부터 다시" → 폴더를 `digest-{round}_prev/`로 이동 후 초기 실행
3. 폴더 생성.

## Phase 1: 병렬 스캔 (서브에이전트 팬아웃)
다섯 수집 작업을 **동시에** 띄운다(한 메시지에 여러 Agent 호출, `run_in_background: true`). 산출물은 모두 위 폴더에 저장.

| Agent | type | model | 담당 계층/소스 | 스킬 | out_path(폴더 내) |
|-------|------|-------|---------------|------|------------------|
| source-digest-collector | general-purpose | opus | corporate·conference (직접 스캔) | source-pdf-digest | `01_scan_corporate.json`, `01_scan_conference.json` |
| global-news-collector | general-purpose | opus | media(외신 6매체) | global-news-collection | `01_scan_global.json` |
| news-collector | general-purpose | opus | arxiv | news-collection | `01_scan_opensource_arxiv.json` |
| news-collector | general-purpose | opus | huggingface | news-collection | `01_scan_opensource_huggingface.json` |
| news-collector | general-purpose | opus | github | news-collection | `01_scan_opensource_github.json` |
| policy-collector | general-purpose | opus | government(5개국) | policy-collection | `01_scan_policy.json` |

각 프롬프트에 포함: 에이전트 정의(`.claude/agents/{name}.md`)+해당 스킬을 읽을 것, `date`·`round`·`workdir`·out_path, 결과 JSON 저장 후 경로·건수 반환. **이번 목적은 "핫이슈 1건 선별용 신규 스캔"** 이므로 기존 수집가는 평소대로 모으되 출력만 이 폴더에 저장한다(메일 브리핑과 무관).

모든 스캔 완료까지 대기.

## Phase 2: 선별 + 심층 수집 (순차, source-digest-collector)
- `source-digest-collector` 재호출(스캔과 동일 에이전트, 이번엔 랭킹·선별·심층수집 단계).
- 프롬프트: `workdir`의 모든 `01_scan_*.json`을 읽어 랭킹 루브릭으로 **1위 1건 선정** → `02_selection.json`, 선정 1건 **심층 수집** → `03_dossier.json`. 2~3위·그 외 단신도 기록.
- 핫이슈가 명확히 없으면 추적 이슈 1건 선정(사유 명시).

## Phase 3: 심층 분석 + HTML 작성 (순차, source-digest-analyst)
- `source-digest-analyst` 호출.
- 프롬프트: `03_dossier.json` 기반 **deep-research 방법론 적용** 심층 분석 → `04_analysis.json` → `assets/brief_template.html`로 `05_digest.html` 조립 → `05_index.json`(초안, pages는 미정/0) 작성.
- **analyst는 PDF 변환을 수행하지 않는다.** 서브에이전트 Bash는 네트워크·실행이 샌드박스 차단될 수 있어 `html_to_pdf.py`가 막힌다(2026-06-12 시범실행 확인). analyst는 HTML/분석/index까지만 완료하고 반환한다.

## Phase 3.5: PDF 변환 + 페이지 검증 (오케스트레이터 본문 = 메인 세션)
**이 단계는 서브에이전트가 아니라 오케스트레이터(메인 세션)가 직접 Bash로 수행한다.** 메인 세션은 실행 권한이 있어 로컬 WeasyPrint 변환이 가능하다.
1. `python3 .claude/skills/source-pdf-digest/scripts/html_to_pdf.py {workdir}/05_digest.html {workdir}/05_digest.pdf` 실행.
2. 페이지 수 확인: `python3 -c "import fitz; print(fitz.open('{workdir}/05_digest.pdf').page_count)"` (PyMuPDF). **1~2p 초과 시** `05_digest.html`의 본문 밀도를 더 조이거나(폰트 9pt·행간 1.38) ③ 의미와 파장의 맥락 단락·푸터 단신을 줄여 재변환. ② 기술 깊이 읽기와 ③ 함의의 깊이는 유지.
3. `05_index.json`의 `pages`를 실제 페이지 수로 갱신.
4. PDF 엔진이 모두 부재하면(폴백 체인 실패) HTML을 게시본으로 두고 보고에 명시.
- 환경 준비: 변환에는 `weasyprint`(+로컬 한글 폰트 NanumGothic/Noto)와 `pymupdf`(페이지 검증·미리보기 래스터)가 필요하다. 없으면 `pip install --user --break-system-packages weasyprint pymupdf`.

## Phase 4: 검토 게이트 + 보고
- `05_digest.pdf` 또는 (변환 실패 시) `05_digest.html` 존재 확인.
- 사용자에게 보고: 선정 1건 제목·원천·관점, 페이지 수, 포털 URL(`/digest`·`/pdf/{date}/{round}`), 2~3위 후보, 실패·누락(피드 오류, PDF 엔진 부재 등).

## 데이터 흐름
파일 기반(`_workspace/{date}/digest-{round}/`): `01_scan_*.json`(스캔) → `02_selection.json`(선별) → `03_dossier.json`(심층수집) → `04_analysis.json`(분석) → `05_digest.html/.pdf`+`05_index.json`(발행·게시). 신규 검출 상태는 `_workspace/.source_digest_state.json`. 중간 파일 보존.

## 에러 핸들링
- 수집가/피드 실패: 1회 재시도 → 재실패 시 해당 소스 제외 진행, 보고에 누락 명시(전체 중단 금지).
- 신규 항목 없음: 추적 이슈 1건으로 진행.
- 상충 수치: analyst가 1차 출처 우선·불확실은 한계 섹션 명시(삭제 금지).
- PDF 엔진 부재: HTML 보존 + 변환 실패 보고(스킬 폴백 체인 시도 후).
- 2p 초과: 압축 재조립.

## 테스트 시나리오
- **정상 흐름**: 6스캔 → collector가 corporate에서 "신규 프런티어 모델 출시"를 1위 선정·심층수집 → analyst가 🔬연구 관점 2p PDF 생성 → 포털 게시 → 보고.
- **에러(신규 부재)**: 한산한 날 → 추적 이슈 1건 선정 → 1p 브리프 → "신규 부재—추적 이슈" 명시.
- **에러(스캔 일부 실패)**: github 스캔 실패 → 나머지로 랭킹 진행 → 보고에 "GitHub 스캔 실패" 명시.
- **에러(PDF 엔진 부재)**: WeasyPrint/대체 모두 없음 → `05_digest.html` 보존 + "PDF 변환 실패, HTML 게시" 보고.
- **후속(관점 변경)**: "정책 관점으로 다시" → analyst만 재호출, `03_dossier.json` 재사용 → PDF 재생성.
