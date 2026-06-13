---
name: ainews-orchestrator
description: AI 뉴스 브리핑을 생성해 gommi72@naver.com으로 발송하는 전체 워크플로우 오케스트레이터. "AI 브리핑/뉴스 브리핑 만들어/보내줘", "오늘 AI 소식 정리해줘", "글로벌 AI 동향 요약", 매일 06:00 KST 예약 실행 트리거 시, 그리고 "브리핑 다시 보내/재실행/업데이트/특정 소스만 다시/글로벌 매체만 다시/이미지·요약 수정" 등 후속 요청 시 반드시 이 스킬을 사용한다. 글로벌 매체(Reuters/AP·FT·WSJ·The Information·TechCrunch·Semafor)·AI타임스·기술동향(HuggingFace·GitHub·arXiv)·5개국 AI정책을 한글 뉴스카드로 묶어 HTML 메일로 보낸다.
---

# ainews-orchestrator — AI 뉴스 브리핑 오케스트레이터

매일 글로벌 매체·국내·기술·정책 소스에서 AI 소식을 수집 → 한글 뉴스카드로 편집 → HTML 메일로 **gommi72@naver.com** 발송.

**실행 모드: 하이브리드** — 수집은 병렬 서브에이전트(팬아웃), 편집·발송은 순차 단일 에이전트.
**모든 Agent 호출은 `model: "opus"`.**

## 고정 설정
- 수신자: `gommi72@naver.com` · 발송: 사용자 Gmail(choihs72@gmail.com)
- 분량: **글로벌 매체 5건**(메인) · AI타임스 3건 · 기술동향(HuggingFace·GitHub·arXiv 각 2건) · 정책 국가별 1~2건
- 작업 폴더: `_workspace/{YYYY-MM-DD}/` (날짜는 한국시간 기준)

## Phase 0: 컨텍스트 확인
1. 한국시간 기준 오늘 날짜 `{date}` 결정(예약 실행은 07:00 KST). UTC와 혼동 주의 — KST = UTC+9.
2. `_workspace/{date}/` 존재 여부로 실행 모드 판별:
   - 폴더 없음 → **초기 실행** (전체 Phase 1~4)
   - 폴더 있음 + 사용자가 "특정 소스/카드만 수정" → **부분 재실행** (해당 수집가/편집만)
   - 폴더 있음 + "처음부터 다시" → 기존 폴더를 `_workspace/{date}_prev/`로 이동 후 초기 실행
   - "다시 보내줘"(내용 동일) → Phase 4(발송)만
3. `_workspace/{date}/` 생성.

## Phase 1: 병렬 수집 (서브에이전트 팬아웃)
6개 수집 작업을 **동시에** 띄운다(한 메시지에 여러 Agent 호출, `run_in_background: true`).

| Agent | type | model | source | 건수 | 스킬 | out_path |
|-------|------|-------|--------|------|------|----------|
| global-news-collector | general-purpose | opus | global(6개 매체) | 5 | global-news-collection | `_workspace/{date}/01_collect_global.json` |
| news-collector | general-purpose | opus | aitimes | 3 | news-collection | `_workspace/{date}/01_collect_aitimes.json` |
| news-collector | general-purpose | opus | huggingface | 2 | news-collection | `_workspace/{date}/01_collect_huggingface.json` |
| news-collector | general-purpose | opus | github | 2 | news-collection | `_workspace/{date}/01_collect_github.json` |
| news-collector | general-purpose | opus | arxiv | 2 | news-collection | `_workspace/{date}/01_collect_arxiv.json` |
| policy-collector | general-purpose | opus | (5개국) | 1~2/국 | policy-collection | `_workspace/{date}/01_collect_policy.json` |

각 Agent 프롬프트에 반드시 포함: 에이전트 정의(`.claude/agents/{name}.md`)와 해당 스킬을 읽고 절차를 따를 것, 배정 `source`·`date`·`out_path`·목표 `count`(위 건수), 결과를 JSON으로 저장하고 경로·건수·한줄요약 반환. **글로벌 매체(global)가 메인 섹션이다.** 기술 소스(huggingface·github·arxiv)는 각 2건으로 축소(editor가 "기술 동향" 한 섹션으로 병합).

모든 수집 완료까지 대기 → 각 결과(건수/실패여부) 수집. 실패한 소스는 빈 결과로 두고 진행(누락은 최종 보고/헤더에 반영).

## Phase 2: 편집 (순차, brief-editor)
- `brief-editor`(general-purpose, opus) 1명 호출.
- 프롬프트: 에이전트 정의 + `brief-composition` 스킬을 읽고, `_workspace/{date}/01_collect_*.json` 전부를 읽어 `02_brief.html`·`02_brief.md` 생성, subject 반환.
- editor가 "수집 데이터 없음 → 발송 보류"를 반환하면 발송하지 않고 사용자에게 보고 후 종료.

## Phase 3: 검토 게이트
- `02_brief.html` 존재 확인. 총 카드 수 0이면 발송 보류.
- (선택) 예약 실행이 아닌 수동 실행이고 사용자가 원하면 미리보기 제공.

## Phase 4: 발송 (순차, mail-dispatcher)
- `mail-dispatcher`(general-purpose, opus) 호출.
- 프롬프트: 에이전트 정의 + `email-delivery` 스킬을 읽고, `subject`·`html_path`(`02_brief.html`)로 `gommi72@naver.com`에 HTML 메일 발송, `03_sent.txt` 기록, 성공/실패 반환.
- 발송 실패(특히 Gmail 미인증) 시 폴백: 파일 보존 + 사용자 알림.

## Phase 5: Top 20 데일리 뉴스 집계 + 포털 게시 (메인 세션, 1일 1회)
수집(Phase 1) 직후의 전 소스 `01_collect_*.json`을 통합해 그날의 **Top 20 뉴스 목록**을 만들고 GitHub Pages 포털에 게시한다. 발송(Phase 4)과 독립이며, 발송 보류 시에도 수집이 됐으면 이 단계는 수행한다. 하루 한 번(06:00 KST am 회차)만 집계한다 — pm 재실행 시엔 생략.
1. `python3 webapp/aggregate_top20.py {date}` → `reports/{date}/top20.json`(제목 한글+원문·출처명·일자·URL, 중복제거·중요도 Top 20). 정보출처에 **arXiv 포함**(글로벌·AI타임스·정책·HuggingFace·GitHub·arXiv 통합), 그리고 **arXiv·Hugging Face·GitHub는 각 1건 이상 보장**(그날 수집물이 있으면 비보장 소스 최저점 항목과 교체). 항목 0이면(수집 실패) 건너뛴다.
2. `python3 webapp/build_news_static.py` → `index.html`(사이트 랜딩 = 오늘 기준 Top 20 + 날짜 아카이브 셀렉터). `python3 webapp/build_digest_static.py` → `digest.html`(am·pm PDF 목록).
3. 커밋·푸시(원격 예약 런타임): `git add reports/{date}/top20.json index.html digest.html && git commit && git push` → GitHub Pages(`https://gommilab.github.io/ainews/`) 랜딩 반영. 로컬 점검 시엔 커밋 생략 가능.

## Phase 6: 보고
사용자에게 요약 보고: 소스별 수집 건수, 총 카드 수, 발송 성공/실패, **Top 20 집계 건수·랜딩(index.html) 게시 여부**, workspace 경로. 실패·누락 소스를 명시한다.

## 데이터 흐름
파일 기반(`_workspace/{date}/`): `01_collect_*.json`(수집) → `02_brief.html`/`.md`(편집) → `03_sent.txt`(발송). Top 20은 `01_collect_*.json` → `reports/{date}/top20.json`(영속) → `news.html`(정적 포털). 중간 파일 보존(감사·재실행용).

## 에러 핸들링
- 수집가 실패: 1회 재시도 → 재실패 시 해당 소스 빈 결과, 진행. 최종 보고에 누락 명시.
- 상충/중복 데이터: 삭제하지 말고 editor가 병합·출처 병기.
- 편집 결과 0건: 발송 보류(빈 메일 금지).
- 발송 실패: 파일 보존 + 알림, 조용한 실패 금지.

## 테스트 시나리오
- **정상 흐름**: 6개 수집(모두 성공) → editor가 글로벌5+AI타임스3+기술6+정책5 ≈ 19건 카드 HTML 생성(글로벌 섹션 최상단) → naver로 발송 성공 → 보고.
- **에러 흐름(글로벌 매체 부족)**: 선별 기준 통과 기사가 3건뿐 → 글로벌 섹션 3건만 표기 → 나머지 진행 → 보고에 "글로벌 기준 통과 3건" 명시.
- **에러 흐름(수집 일부 실패)**: github 수집 실패 → 나머지 5개로 진행 → editor가 기술 동향 섹션에서 GitHub 항목 생략 → 발송 → 보고에 "GitHub 수집 실패" 명시.
- **에러 흐름(발송 실패)**: Gmail 미인증/웹훅 오류 → `03_sent.txt`에 실패 기록 + HTML 보존 + 사용자 알림.
