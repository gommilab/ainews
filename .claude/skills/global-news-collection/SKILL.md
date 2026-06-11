---
name: global-news-collection
description: 글로벌 AI 뉴스 매체(Reuters/AP·Financial Times·Wall Street Journal·The Information·TechCrunch·Semafor)를 한 번에 훑어 선별 기준을 통과한 핵심 AI 뉴스 5건을 3단계 검증(매체 발견→공식 원문 확인→해석)으로 큐레이션해 한글 JSON으로 만드는 절차. global-news-collector 에이전트가 글로벌 매체 뉴스를 모을 때, AI 브리핑의 글로벌 뉴스 섹션을 채울 때 반드시 사용한다.
---

# global-news-collection — 글로벌 AI 뉴스 큐레이션 절차

6개 글로벌 매체의 **최근 24~48시간** AI 보도를 훑어, 선별 기준을 통과한 **5건**을 골라 한글로 정리한다. 단일 소스 수집(`news-collection`)과 달리 여러 매체를 **교차 검증**하고 중복을 합치는 것이 핵심이다.

## 3단계 검증 (모든 항목에 적용)
1. **발견** — 6개 매체의 헤드라인/검색 결과로 "오늘의 큰 이슈"를 찾는다.
2. **확인** — 그 이슈를 **기업 공식 발표·규제기관 문서·Reuters/AP 등 1차/무료 출처**로 교차 확인한다. 유료 매체 본문 대신 이 1차 출처에서 사실·수치를 가져온다.
3. **해석** — 왜 중요한지(투자 규모, 규제 파급, 한국 기업/공급망 연관 등)를 요약에 한 줄 담는다.

## 절차
1. `references/outlets.md`를 읽어 매체별 접근 경로·검색 쿼리·페이월 처리법을 확인한다.
2. WebSearch로 6개 매체 + 핵심 키워드(아래)를 훑어 후보 헤드라인을 모은다.
3. **선별 기준**으로 거르고 **제외 기준**으로 버린다(아래).
4. 같은 사건을 여러 매체가 다루면 **하나로 합치고** `media`에 발견 매체를 적는다(예: "FT·Reuters").
5. 각 후보의 1차 출처(기업 공식/규제기관/Reuters·AP)를 열어 사실·수치·`og:image`를 확보한다.
6. 한글 제목·요약(3~5문장)을 작성한다. 고유명사·기업명·모델명·금액은 원문 병기.
7. 최종 5건을 `out_path`에 JSON으로 저장한다.

## 선별 기준 (이 중 하나라도 해당하면 포함 후보)
- 새 모델 출시 / 대규모 투자·인수합병 / 반도체·데이터센터·전력 이슈
- 정부 규제 / 소송 / 안전성 사고 / 주요 논문
- 기업 도입 사례 / 노동시장 영향 / **한국 기업과 연결되는 글로벌 공급망**

## 제외 기준 (해당하면 버림)
- 단순 기능 업데이트 / 출처 없는 루머 / "AI가 세상을 바꾼다"식 과장 칼럼
- 특정 서비스 홍보성 기사 / 벤치마크 숫자만 있고 실사용성 불분명한 기사

## 검색 키워드 (예시)
`AI funding round`, `AI acquisition`, `OpenAI`, `Anthropic`, `Nvidia chips`, `AI data center power`, `AI regulation lawsuit`, `AI safety incident`, `enterprise AI adoption`, `AI semiconductor Korea Samsung SK hynix`. 매체별 `site:` 검색은 `references/outlets.md` 참조.

## 유료 매체 처리 (FT·WSJ·The Information)
- 제목·검색 스니펫으로 **이슈 발견만** 한다. 본문 추측 금지.
- 실제 내용·수치·요약은 **무료 1차 출처**로 확보: 기업 보도자료/블로그, 규제기관 발표, Reuters/AP/TechCrunch/Semafor의 같은 사건 보도.
- 1차 출처를 못 찾으면 그 항목은 "(유료 매체 단독, 미확인)"으로 표기하거나 후순위로 내린다.

## 이미지 추출 (실제 대표 이미지를 적극 시도)
폴백 배지는 최후 수단이다. 순서대로:
1. 1차 출처(또는 기사) 페이지의 `og:image` → 없으면 `twitter:image` → 본문 첫 대표 이미지.
2. 기업 공식 발표에 이미지가 없으면 같은 사건을 보도한 신뢰도 높은 기사의 og:image 사용(url은 1차 출처 유지, image_url만 기사에서 가져와도 됨).
3. WebFetch로 못 얻으면 `../news-collection/scripts/extract_og_image.sh {url}` 실행(Bash 권한 필요). 추출 URL은 실제로 열리는지 확인.
4. 모두 실패 시에만 `image_url=""` (editor가 🌐 배지로 폴백). **가짜·추측 URL 금지.**

## 출력 스키마
```json
{
  "source": "global",
  "label_ko": "글로벌 AI 뉴스",
  "collected_at": "<UTC ISO8601>",
  "items": [
    {
      "title_ko": "...", "title_orig": "...",
      "url": "1차 출처/공식 발표 URL",
      "media": "Reuters",
      "category": "투자/M&A | 모델출시 | 반도체·인프라 | 규제 | 소송 | 안전 | 논문 | 도입사례 | 노동시장 | 공급망",
      "image_url": "... 또는 \"\"",
      "summary_ko": "...(무엇이/왜 중요한지)",
      "published": "YYYY-MM-DD", "tag": "global"
    }
  ]
}
```

## 품질 체크 (저장 전)
- [ ] 5건인가(부족 시 사유를 반환에 기록 — 억지로 채우지 않음)
- [ ] 각 항목이 선별 기준 중 하나에 해당하고 제외 기준에 안 걸리는가
- [ ] `url`이 가능한 한 1차/무료 출처인가, 실제로 열리는가
- [ ] 유료 매체 항목은 무료 출처로 교차 확인했는가
- [ ] 요약이 제목 반복이 아니라 "왜 중요한지"를 담는가
- [ ] 같은 사건 중복이 합쳐졌는가
