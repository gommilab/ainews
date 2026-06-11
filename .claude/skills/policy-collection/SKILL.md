---
name: policy-collection
description: 미국·EU·중국·일본·영국의 최신 AI 정책·규제·거버넌스 동향을 국가별로 1~2건 수집해 한글 요약 JSON으로 만드는 절차. policy-collector 에이전트가 정책 동향을 모을 때, AI 브리핑의 정책 섹션을 채울 때 반드시 사용한다.
---

# policy-collection — 글로벌 AI 정책 동향 수집 절차

5개국(미국·EU·중국·일본·영국)의 **최근 1~2주** AI 정책 소식을 국가별 **1~2건**씩 모은다.

## 절차
1. 국가별로 아래 핵심 출처 + 검색 키워드로 최신 동향을 찾는다(WebSearch + WebFetch).
2. 정부·규제기관 1차 출처 또는 신뢰도 높은 통신사 보도를 우선한다.
3. 국가별 1~2건 선별 → 한글 요약(출처 기관명 포함) 작성.
4. 미국→EU→중국→일본→영국 순으로 JSON 저장.

## 국가별 핵심 출처·키워드
- **미국**: White House(OSTP), NIST(AI RMF), Congress 입법, 상무부/FTC. 키워드: "US AI policy", "NIST AI", "executive order AI", "AI regulation Congress".
- **EU**: European Commission, EU AI Act 시행/가이드라인, AI Office. 키워드: "EU AI Act", "European Commission AI", "GPAI code of practice".
- **중국**: CAC(网信办), MIIT(工信部), 생성형 AI 관리규정, 표준. 키워드: "China AI regulation", "CAC generative AI", "China AI standards".
- **일본**: METI, 内閣府(AI戦略), AISI Japan, AI事業者ガイドライン. 키워드: "Japan AI policy", "METI AI", "Japan AI guidelines".
- **영국**: DSIT, AI Safety Institute(AISI), 규제 프레임워크. 키워드: "UK AI policy", "AI Safety Institute", "DSIT AI regulation".

## 선별 기준
- 새 법·규정·가이드라인·국가전략·예산·국제협약 등 **실질 변화** 우선.
- 단순 컨퍼런스 발언보다 공식 발표·문서를 우선.
- 해당 기간 의미 있는 소식이 없으면 그 국가는 건너뛰고 반환 메시지에 명시.

## 이미지 (실제 대표 이미지를 적극 시도)
폴백 배지는 최후 수단이다. 순서대로 시도한다:
1. 출처 페이지의 `og:image` → 없으면 `twitter:image` → 본문 첫 대표 이미지.
2. 정부 발표문에 이미지가 없으면, 같은 사안을 보도한 신뢰도 높은 기사(로이터/블룸버그 등)의 og:image를 사용(단 url은 1차 출처 우선, image_url만 기사에서 가져와도 됨).
3. WebFetch로 못 얻으면 `../news-collection/scripts/extract_og_image.sh {url}` 실행.
4. 모두 실패 시에만 `""` (editor가 🏛️ 배지로 폴백). 가짜 URL 금지.

## 출력 스키마
```json
{
  "source": "policy",
  "label_ko": "글로벌 AI 정책 동향",
  "collected_at": "<UTC ISO8601>",
  "items": [
    { "country": "미국", "title_ko": "...", "url": "...",
      "image_url": "... 또는 \"\"", "summary_ko": "...(출처 기관명 포함)",
      "published": "YYYY-MM-DD", "tag": "policy" }
  ]
}
```

## 품질 체크
- [ ] 가능한 국가를 모두 시도했는가
- [ ] 요약에 출처 기관명과 시행 시점/대상이 있는가
- [ ] 논평이 아니라 사실 중심인가
