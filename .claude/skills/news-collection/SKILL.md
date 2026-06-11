---
name: news-collection
description: aitimes / HuggingFace / GitHub / arXiv 한 소스에서 최신 AI 뉴스 3건을 수집해 한글 제목·대표 이미지·요약 JSON으로 만드는 절차. news-collector 에이전트가 소스를 배정받아 수집할 때, AI 뉴스 브리핑의 콘텐츠 소스를 모을 때 반드시 사용한다.
---

# news-collection — 콘텐츠 소스 수집 절차

aitimes / HuggingFace / GitHub / arXiv 각각에서 **최근 24~48시간**의 중요 소식 **3건**을 뽑아 구조화한다. 한 번의 호출은 한 소스만 다룬다.

## 공통 절차
1. 배정된 `source`에 맞는 `references/{source}.md`를 읽는다 — 수집 URL·선별 기준·이미지 추출법이 거기에 있다.
2. WebSearch / WebFetch로 해당 소스의 최신 목록을 가져온다.
3. 최신성·중요도 기준으로 상위 3건을 선별한다.
4. 각 건의 원문 페이지를 열어 `og:image`(대표 이미지)와 핵심 내용을 확보한다.
5. 한글 제목과 한글 요약(3~5문장)을 작성한다. 원문이 영어면 자연스러운 한국어로 번역하되 고유명사·모델명은 원문 병기.
6. `out_path`에 JSON으로 저장한다(스키마는 아래).

## 선별 기준 (공통)
- 영향력: 업계가 주목할 발표/출시/연구인가
- 신규성: 오늘/어제 새로 등장했는가
- 구체성: 막연한 전망보다 구체적 사건·수치·릴리스 우선
- 다양성: 같은 주제 3건보다 서로 다른 주제 3건

## 이미지 추출 (각 기사·자료의 실제 대표 이미지를 반드시 시도)
폴백 배지는 최후 수단이다. 아래 체인을 **순서대로** 끝까지 시도해 실제 이미지를 확보한다.
1. 원문 페이지의 `<meta property="og:image">`
2. `<meta name="twitter:image">` (og:image가 없을 때 자주 존재)
3. 기사 본문 상단의 대표 `<img>` / 썸네일 / 대표 도표
4. (소스별 보강) GitHub=`https://opengraph.githubassets.com/1/{owner}/{repo}`, HuggingFace 모델/데이터셋=리포 카드 이미지, arXiv=아래 references/arxiv.md의 그림 추출법
5. 위 모두 실패 시에만 `image_url=""` (editor가 폴백 배지 처리). **가짜·추측 URL 금지.**

**추출 방법:** WebFetch 프롬프트에 "이 페이지의 og:image와 twitter:image 메타태그 URL, 그리고 본문 첫 대표 이미지 URL을 모두 알려달라"를 명시하면 신뢰도 높게 얻을 수 있다. WebFetch로 못 얻으면 `scripts/extract_og_image.sh {url}` 을 실행해 메타 이미지 URL을 추출한다(Bash 권한 필요). 추출한 URL은 실제로 열리는지 확인한다.

## 출력 스키마
```json
{
  "source": "<source>",
  "label_ko": "<섹션 한글명>",
  "collected_at": "<UTC ISO8601>",
  "items": [
    {
      "title_ko": "...", "title_orig": "...",
      "url": "...", "image_url": "... 또는 \"\"",
      "summary_ko": "...", "published": "YYYY-MM-DD", "tag": "<source>"
    }
  ]
}
```
`label_ko` 값: aitimes=`AI타임스`, huggingface=`HuggingFace`, github=`GitHub 트렌딩`, arxiv=`arXiv 신규 논문`.

## 품질 체크 (저장 전)
- [ ] 3건인가(부족 시 사유를 반환에 기록)
- [ ] 모든 url이 실제 원문인가
- [ ] 요약이 제목 반복이 아니라 내용을 담는가
- [ ] published 날짜가 최근인가
