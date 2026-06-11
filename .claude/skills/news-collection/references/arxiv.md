# arXiv 신규 논문 수집 가이드

**새로 등록된** AI 논문을 추적한다. 핵심은 "최신 제출(new submissions)"이다.

## 수집 경로
- 신규 목록(최우선): `https://arxiv.org/list/cs.AI/new`, `https://arxiv.org/list/cs.LG/new`, `https://arxiv.org/list/cs.CL/new`, `https://arxiv.org/list/cs.CV/new`
  - `/new`는 가장 최근 제출분을 보여준다. 여기서 3건을 고른다.
- 보조: `https://huggingface.co/papers` 와 겹치지 않게(겹치면 다른 걸로) 선택.

## 선별
- **신규성(오늘 등록) 최우선.** 개정(replaced)이 아닌 신규 제출 우선.
- 주목 기관/저자, 새 방법론·새 SOTA·흥미로운 문제설정 우선.
- cs.AI/LG/CL/CV에 걸쳐 주제 다양성 확보.

## 이미지 (실제 대표 이미지를 적극 시도)
arXiv 초록 페이지 자체엔 대표 이미지가 없지만, 아래 순서로 실제 그림을 확보한다:
1. **HuggingFace Papers 썸네일**: 해당 논문이 `https://huggingface.co/papers/{arxiv_id}` 에 있으면 그 페이지의 og:image(논문 대표 figure 썸네일)를 사용. 많은 신규 논문이 등재돼 있어 1순위로 시도.
2. **ar5iv 첫 figure**: `https://ar5iv.org/abs/{arxiv_id}` 를 열어 본문 첫 번째 그림(figure 1) 이미지 URL 추출.
3. 둘 다 실패 시에만 `""` (editor가 논문 배지 📄 로 폴백).
- 추출한 URL은 실제로 열리는지 확인하고, 가짜 URL은 절대 넣지 않는다.

## 작성
- `title_orig` = 논문 영문 제목, `title_ko` = 한글 번역 제목(핵심 용어 원문 병기).
- `url` = arXiv 초록 페이지(`https://arxiv.org/abs/XXXX.XXXXX`).
- `summary_ko` = 무엇을 풀었고 어떤 방법·결과인지 초록 기반 3~5문장. 과장 없이.
- `published` = 제출일.
