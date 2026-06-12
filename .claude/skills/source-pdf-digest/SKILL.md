---
name: source-pdf-digest
description: aitimes.kr의 상류 원천(기업 공식·컨퍼런스·정부·외신·연구/오픈소스)을 직접 감시해 그날 가장 핫한 이슈 1건을 선별하고, deep-research 방법론으로 심층 분석한 뒤 A4 1~2페이지 PDF 분석 브리프로 조립해 웹포털에 게시하는 절차. source-digest-collector(스캔·랭킹·선별·심층수집)와 source-digest-analyst(심층분석·작성·PDF·게시)가 "원천 심층 브리프"를 만들 때, 핫이슈 1건을 고를 때, 분석 PDF를 조립할 때 반드시 사용한다. "원천 동향 브리프 다시/재실행/업데이트/저녁 회차/관점 바꿔/더 깊게/단신 보강" 등 후속 요청에도 사용한다.
---

# source-pdf-digest — 원천 핫이슈 심층 PDF 브리프 절차

aitimes.kr이 한글화하기 **전의 상류 1차 원천**을 직접 감시해, 그날 **가장 핫한 이슈 1건**을 골라 **deep-research 방법론으로 심층 분석**하고, **A4 1~2p PDF 분석 브리프**로 만들어 **웹포털에 게시**한다. 독자는 과학기술 **연구자·정책자**.

설계 근거: aitimes.kr은 기업 공식 발표·컨퍼런스·정부·외신·논문을 수시간~하루 늦게 번역하는 애그리게이터다. 그 상류를 직접 보면 구조적으로 앞선다. 전체 설계는 `docs/source-digest-service-design.md` 참조.

## 5계층 원천 레지스트리
`references/sources.yaml`이 감시 대상의 단일 소스다. 5계층:
- **corporate(기업 공식)** — Anthropic·OpenAI·Google/DeepMind·Meta·Microsoft·AWS·NVIDIA·삼성·Bosch 뉴스룸/블로그 (이 스킬에서 직접 스캔)
- **conference(컨퍼런스)** — re:Invent·Google I/O·GTC·Bosch Connected World 등 (직접 스캔)
- **government(정부·규제)** — White House·EU 등 → 기존 `policy-collector` 재활용
- **media(외신)** — Reuters·FT·WSJ·TechCrunch·The Information·Semafor → 기존 `global-news-collector` 재활용
- **opensource(연구·오픈소스)** — arXiv·HuggingFace·GitHub → 기존 `news-collector` 재활용

corporate·conference만 신규 스캔하고, 나머지는 기존 수집가 산출물(`01_scan_*.json`)을 읽어 합친다. **중복 수집을 피하라.**

## 절차 (수집가 → 분석가)

### A. 스캔 (collector, corporate·conference)
1. `scripts/scan_sources.py --layer corporate --out {workdir}/01_scan_corporate.json` 실행 → RSS 피드의 신규 항목을 `_workspace/.source_digest_state.json` 대비로 검출(중복 방지).
2. RSS가 없는 원천(`feed: scrape`)은 레지스트리의 `url`을 WebFetch로 열어 최신 발표를 확인한다.
3. conference 계층도 동일하게 `--layer conference`. 진행 중/임박 행사의 발표 페이지를 폴링한다.
4. 각 항목을 공통 스키마(아래)로 저장한다.

### B. 랭킹 → 1건 선별 (collector)
전 계층(`01_scan_*.json`)을 모아 점수화한다. 루브릭은 `references/ranking-and-analysis.md` 참조. 핵심 가중치:
- **교차 노출도**(여러 계층 동시 언급) · **파급도**(출시·규제·대형 투자·인프라) · **신규성** · **연구·정책 적합성**.
- 동점 시 **원천 1차성**(공식·논문 > 2차)·최신성 우선.
1위 1건을 선정하고 2~3위·"그 외 주목 단신"을 `02_selection.json`에 남긴다.

### C. 심층 수집 (collector)
선정 1건의 **원천 원문 + 관련 소스 다수**(경쟁사 반응·해설 외신·관련 논문·정부 입장)를 모아 `03_dossier.json`을 만든다. 대표 이미지(og:image)도 확보(없으면 빈 문자열). 이미지 추출법은 기존 `news-collection` 스킬의 체인과 동일.

### D. 심층 분석 (analyst, deep-research 적용)
`03_dossier.json`을 기반으로 **deep-research 방법론을 1건으로 한정 적용**: 팬아웃 검색으로 사실·수치를 교차검증하고, 출처가 부족하면 보강한다. 본문 분석(Keynote + 본문 4섹션 + 출처)을 `04_analysis.json`으로 작성한다. 섹션별 작성 기준·주제 적응형 관점·분량 캘리브레이션은 `references/ranking-and-analysis.md` 참조.

### E. PDF 조립 (analyst)
1. `assets/brief_template.html`을 복사해 본문 4섹션 + 푸터(그 외 주목 단신)를 채워 `{workdir}/05_digest.html`을 만든다. 대표 이미지는 **로컬 다운로드 후 임베드**(핫링크 금지).
2. `python3 scripts/html_to_pdf.py {workdir}/05_digest.html {workdir}/05_digest.pdf` 실행.
3. 결과가 1~2p인지 확인. 초과 시 본문 압축·단신 축소 후 재변환.

### F. 포털 게시 (analyst)
- 산출물은 `_workspace/{date}/digest-{round}/`에 둔다(포털이 자동 스캔).
- `05_index.json`을 같은 폴더에 써서 포털 목록 메타데이터를 제공한다:
```json
{"date":"2026-06-12","round":"am","headline_ko":"...","topic_kind":"model","perspective":"research","primary_source":"Anthropic","pdf":"05_digest.pdf","pages":2}
```
- 포털(`webapp/server.py`)은 이 폴더를 읽어 `/digest` 목록과 `/pdf/{date}/{round}` 다운로드를 제공한다.

## 공통 스캔 스키마 (`01_scan_*.json`)
```json
{
  "layer": "corporate",
  "collected_at": "<UTC ISO8601>",
  "items": [
    {"title_ko":"...","title_orig":"...","url":"...","primary_source":"Anthropic",
     "image_url":"... 또는 \"\"","summary_ko":"1~2문장","published":"YYYY-MM-DD","layer":"corporate"}
  ]
}
```
기존 수집가가 만든 `01_scan_global.json`(media)·`01_scan_opensource_*.json`·`01_scan_policy.json`은 각자 스키마를 쓰되, 랭킹 시 `title_ko/url/published/primary_source(또는 media/country)`를 공통 키로 읽는다.

## 산출물 레이아웃 (`_workspace/{date}/digest-{round}/`)
```
01_scan_corporate.json  01_scan_conference.json   (collector 신규)
01_scan_global.json  01_scan_opensource_*.json  01_scan_policy.json  (재활용 수집가)
02_selection.json   03_dossier.json   04_analysis.json
05_digest.html   05_digest.pdf   05_index.json
```
중간 파일은 보존(감사·재실행용).

## 품질 체크 (게시 전)
- [ ] 선정이 정말 "그날 가장 핫한 1건"인가(랭킹 근거 `02_selection.json`에 기록)
- [ ] ② 기술 깊이 읽기에 연구자 수준 디테일(수치·방법·벤치마크)이 있는가
- [ ] ③ 의미와 파장에서 맥락(배경/위치)과 함의(변화/영향)가 중복 없이 구분되고, 함의가 주제에 맞는 관점으로 분석됐는가(주관점 명시)
- [ ] 모든 주장에 원천 직링크가 있는가
- [ ] PDF가 A4 1~2p 안에 들어왔는가
- [ ] `05_index.json`이 있어 포털이 인식하는가

## 참고
- 원천 레지스트리: `references/sources.yaml`
- 랭킹 루브릭 · 섹션 작성 기준 · 분량 캘리브레이션: `references/ranking-and-analysis.md`
- 신규 검출 스크립트: `scripts/scan_sources.py`
- HTML→PDF 변환: `scripts/html_to_pdf.py`
- PDF 템플릿: `assets/brief_template.html`
