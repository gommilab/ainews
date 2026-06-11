# HuggingFace 수집 가이드

오픈 AI 생태계의 최신 모델·데이터셋·연구를 추적한다.

## 수집 경로 (우선순위)
1. **Daily Papers**: `https://huggingface.co/papers` — 매일 큐레이션되는 화제의 논문. 최신 날짜의 상위 항목.
2. **Trending Models**: `https://huggingface.co/models?sort=trending` — 급상승 모델.
3. **Blog**: `https://huggingface.co/blog` — 공식 발표/튜토리얼.

WebFetch로 위 페이지를 가져와 최신·상위 항목을 추출한다. 셋을 섞어 다양성 있게 3건 구성 가능(예: 화제 논문 1 + 트렌딩 모델 1 + 블로그 1).

## 선별
- 좋아요/다운로드 급증, 큐레이션 상위, 새 SOTA·새 기능 우선.
- 동일 모델의 사소한 버전 업보다 새 계열/새 기능을 우선.

## 이미지
- 논문 카드: 첫 페이지 figure 썸네일이 노출되는 경우 사용.
- 모델/블로그: 페이지 `og:image` 또는 대표 썸네일.
- 없으면 `""`.

## 작성
- `title_orig` = 원문 영어 제목, `title_ko` = 자연스러운 한글 제목(모델명·논문명은 원문 병기).
- `summary_ko` = 무엇이며 왜 주목받는지 3~5문장.
