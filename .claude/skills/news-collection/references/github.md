# GitHub 수집 가이드

AI/ML 분야에서 급부상하는 오픈소스 프로젝트를 추적한다.

## 수집 경로
- 트렌딩(오늘): `https://github.com/trending?since=daily`
- 언어 필터: `https://github.com/trending/python?since=daily`, `https://github.com/trending/jupyter-notebook?since=daily`
- WebFetch로 가져와 AI/ML 관련 레포(LLM, 에이전트, 추론, 학습, RAG, 멀티모달 등)를 우선 추출.

## 선별
- **AI/ML 관련성 필수** — 일반 웹/툴 레포는 제외하고 AI 관련만 3건.
- 당일 스타 증가폭이 큰 것, 새로 등장한 것 우선.
- 단순 awesome-list보다 실제 도구/모델/프레임워크 우선(단, 의미 있는 큐레이션은 허용).

## 이미지
- 레포의 소셜 프리뷰 이미지(`https://opengraph.githubassets.com/...` 형태가 og:image로 노출됨) 추출.
- 없으면 README 상단 로고/배너, 그래도 없으면 `""`.

## 작성
- `title_ko` = `소유자/레포명` + 한 줄 한글 설명 형태(예: `xxx/yyy — 경량 LLM 추론 엔진`).
- `summary_ko` = 무엇을 하는 프로젝트인지, 왜 화제인지(스타 추이 등) 3~5문장.
