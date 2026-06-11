---
name: brief-composition
description: 수집된 JSON들을 한글 뉴스카드(제목·이미지·요약)로 편집하고 발송용 HTML 이메일 본문과 마크다운 백업을 조립하는 절차. brief-editor 에이전트가 AI 브리핑을 완성할 때, 뉴스카드 HTML을 만들 때 반드시 사용한다.
---

# brief-composition — 뉴스 브리핑 조립 절차

수집 JSON들을 읽어 이메일 한 통으로 완성한다. 출력은 HTML(발송용)과 마크다운(백업) 두 가지.

## 절차
1. `_workspace/{date}/01_collect_*.json`을 모두 읽는다.
2. 섹션 순서로 정렬: **🌐 글로벌 AI 뉴스(메인) → 📰 AI타임스 → 🛠️ 기술 동향(HuggingFace·GitHub·arXiv 병합) → 🏛️ 글로벌 AI 정책 동향**(미국·EU·중국·일본·영국).
   - **글로벌 AI 뉴스**는 `01_collect_global.json` (5건). 브리핑의 **최상단 메인 섹션**.
   - **기술 동향**은 `01_collect_huggingface.json`·`github`·`arxiv` 3개를 **한 섹션으로 병합**한다. 섹션 헤더는 `🛠️ 기술 동향`, 각 카드에 하위 출처 라벨(HuggingFace🤗 / GitHub🐙 / arXiv📄)을 붙인다.
3. 중복 제거: 같은 사건이 여러 소스에 있으면 하나로 합치고 출처를 병기. 글로벌 뉴스와 AI타임스가 같은 사건이면 글로벌 카드에 합치고 AI타임스 출처 병기.
4. 각 항목을 카드로 변환(아래 카드 양식).
5. `assets/email-template.html`을 베이스로 헤더·섹션·카드를 채워 `02_brief.html` 생성.
6. 동일 내용을 마크다운으로 `02_brief.md` 생성.
7. 이메일 제목(subject) 문자열 작성.

## 카드 양식 (한글)
각 카드는 3요소: **제목 / 대표 이미지 / 주요내용 요약**.
- **제목**: `title_ko`. 원문 링크(`url`)를 건다. 정책 카드는 제목 앞에 국기 이모지 + 국가명(🇺🇸 미국 / 🇪🇺 EU / 🇨🇳 중국 / 🇯🇵 일본 / 🇬🇧 영국).
- **글로벌 뉴스 카드 추가 표기**: 제목 위/아래에 작은 메타 줄로 `발견 매체(media)` + `분류(category)` 배지를 둔다(예: `Reuters · 투자/M&A`). 메인 섹션이므로 카드를 조금 더 크게(요약 3~5줄) 보여준다.
- **카드 테두리**: 각 카드는 반드시 `border:1px solid #d7dbe0`로 영역을 구분한다(`overflow:hidden`으로 이미지 모서리 정리). 박스섀도만으로는 구분이 약하므로 테두리를 함께 둔다.
- **이미지**: 각 기사·자료의 **실제 대표 이미지**를 최대한 넣는다. `image_url`이 있으면 `<img>`로 삽입(폭 100%, 최대 높이 제한, `alt`=제목). 비어 있을 때만 **폴백 배지**(소스별 이모지 + 색 블록)를 쓰되, 폴백은 최후 수단이다:
  - global 🌐 / aitimes 📰 / huggingface 🤗 / github 🐙 / arxiv 📄 / policy 🏛️
- **요약**: `summary_ko`. 글로벌 뉴스는 3~5줄, 그 외는 2~4줄.
- 카드 하단: `🔗 원문 보기` 링크 + `published` 날짜 + 출처 라벨(글로벌은 `media`, 기술 동향은 하위 출처명).

## 헤더
- 제목 `🗞️ AI 뉴스 브리핑` + 날짜(한국시간, 예: `2026년 6월 7일 (토)`)
- 오늘의 하이라이트 1~2문장(가장 큰 소식 요약)
- 전체 카드 수

## 이메일 제목(subject)
`[AI 브리핑] YYYY-MM-DD · 오늘의 AI 소식 N건` 형식. 가장 큰 헤드라인을 덧붙여도 좋다.

## HTML 작성 규칙 (중요)
- **인라인 CSS만 사용.** 네이버/Gmail 웹메일은 `<style>` 블록·외부 CSS를 제거하므로 모든 스타일은 `style="..."` 속성으로.
- 레이아웃은 `<table>` 기반(이메일 클라이언트 호환). flex/grid 지양.
- 폭은 600px 컨테이너 권장, 모바일에서 width:100%.
- 이미지에 `style="max-width:100%;height:auto;max-height:280px;border-radius:8px"`, 깨짐 대비 `alt`.
- 색/폰트는 템플릿(`assets/email-template.html`)의 토큰을 따른다.

## 빈 섹션
- 0건 섹션은 삭제하지 말고 "오늘은 새 소식이 없습니다"로 짧게 표기.

## 출력
- `{workspace_dir}/02_brief.html`, `{workspace_dir}/02_brief.md`
- 반환: 두 경로 + 총 카드 수 + subject 문자열.
- 읽을 JSON이 0개거나 전체 0건이면 발송 보류 신호를 반환(빈 메일 방지).
