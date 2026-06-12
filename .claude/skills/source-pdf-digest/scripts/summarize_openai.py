#!/usr/bin/env python3
"""OpenAI(ChatGPT) 본문 서술기 — dossier → 04_analysis.json.

역할 분담: Claude collector가 스캔·선별·교차검증(1차 출처)해 03_dossier.json을
만들면, 이 스크립트가 OpenAI Chat Completions로 그 검증된 사실만 근거로
'개요·주요내용·시사점' 본문을 한글 서술한다(없는 사실 창작 금지).

설계 원칙:
- 외부 의존성 0 (표준 라이브러리 urllib만). pip 설치 불필요.
- URL·출처·단신 링크는 LLM에 맡기지 않고 dossier/selection에서 그대로 옮겨
  넣어 정확성을 보장한다(환각 링크 차단). LLM은 서술 텍스트만 생성.
- 키 부재/네트워크/JSON 오류 시 비정상 종료(exit!=0)해 오케스트레이터가
  Claude 폴백 작성으로 전환할 수 있게 한다.

키·모델 해석 순서(클라우드는 Bash 호출마다 새 셸이라 export가 유지되지 않으므로
파일 폴백을 둔다):
  1) 환경변수 OPENAI_API_KEY / OPENAI_MODEL
  2) `.claude/settings.local.json`의 `env` 블록 (gitignore됨 → 커밋 안 됨)
키가 어디에도 없으면 exit 3 (Claude 폴백 신호). 모델 기본값 gpt-4o.
  OPENAI_BASE_URL (선택, 기본 https://api.openai.com/v1)

실행:  python3 summarize_openai.py {workdir}
출력:  {workdir}/04_analysis.json
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request

BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")


def _settings_env():
    """`.claude/settings.local.json`의 env 블록을 찾아 반환(cwd·스크립트 경로 상향 탐색)."""
    seen = set()
    roots = [os.getcwd(), os.path.dirname(os.path.abspath(__file__))]
    for start in roots:
        d = start
        for _ in range(8):
            p = os.path.join(d, ".claude", "settings.local.json")
            if p not in seen:
                seen.add(p)
                if os.path.exists(p):
                    try:
                        return json.load(open(p, encoding="utf-8")).get("env") or {}
                    except Exception:  # noqa: BLE001
                        return {}
            nd = os.path.dirname(d)
            if nd == d:
                break
            d = nd
    return {}


def resolve_credentials():
    """(api_key, model) — env 우선, 없으면 settings.local.json 폴백."""
    key = (os.environ.get("OPENAI_API_KEY") or "").strip()
    model = (os.environ.get("OPENAI_MODEL") or "").strip()
    if not key or not model:
        env = _settings_env()
        if not key:
            key = (env.get("OPENAI_API_KEY") or "").strip()
        if not model:
            model = (env.get("OPENAI_MODEL") or "").strip()
    return key, (model or "gpt-4o")


def die(msg, code):
    print(f"[summarize_openai] {msg}", file=sys.stderr)
    sys.exit(code)


def load_json(path, required=True):
    if not os.path.exists(path):
        if required:
            die(f"필수 입력 없음: {path}", 2)
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def parse_date_round(workdir, selection):
    if selection and selection.get("date") and selection.get("round"):
        return selection["date"], selection["round"]
    # _workspace/{YYYY-MM-DD}/digest-{am|pm}
    m_round = re.search(r"digest-(am|pm)", workdir)
    m_date = re.search(r"(\d{4}-\d{2}-\d{2})", workdir)
    return (m_date.group(1) if m_date else ""), (m_round.group(1) if m_round else "")


SYSTEM_PROMPT = (
    "당신은 과학기술 연구자·정책자를 독자로 하는 한글 AI 동향 브리프의 편집자다. "
    "주어진 dossier(이미 1차 출처로 교차검증된 사실·수치·맥락)만을 근거로 본문을 서술한다. "
    "dossier에 없는 사실·수치·고유명사를 새로 만들지 마라. 과장·홍보 문구를 피하고 분석적으로 쓴다. "
    "반드시 아래 키를 가진 JSON 하나만 출력한다(코드블록·설명 금지):\n"
    "{\n"
    '  "headline_ko": "한 줄 제목(dossier 제목을 다듬어도 됨)",\n'
    '  "topic_kind": "model|tech|research|policy|regulation|standard|investment|infra|chip|mixed 중 하나",\n'
    '  "perspective": "research|policy|both(주관점 명시) — 시사점의 무게중심",\n'
    '  "keynote": ["핵심 요지 3~4개. 각 1~2문장. 무슨 일·왜 중요한지 바쁜 독자가 이것만 봐도 되게"],\n'
    '  "overview": "개요 — 무슨 일이 일어났고 왜 중요한지를 한 문단(3~5문장)으로. 도입부 성격.",\n'
    '  "main_content_html": "주요내용 — 사실관계와 기술·수치·벤치마크를 연구자 수준 디테일로. 순수 HTML 조각으로: <p>…</p>와 필요 시 <ul class=\\"tight\\"><li>…</li></ul>, 강조는 <b>. 핵심 수치·모델명·사양은 그대로 인용.",\n'
    '  "implications": "시사점 — topic_kind에 맞는 관점(모델/기술/논문→연구·개발, 규제/표준/투자→정책, 경계→둘 다)으로 \'무엇이 어떻게 바뀌는지\'. 전망·한계(한계·미해결 쟁점)도 이 안에 녹인다. 한 문단 또는 2~3문장 단위. 순수 텍스트(필요 시 <b>만).",\n'
    "}\n"
    "분량 가이드: 전체가 A4 1~2페이지에 들어가도록 간결하게. 주요내용이 가장 두껍고, 개요·시사점은 압축적으로."
)


def build_user_payload(dossier, selection):
    related = dossier.get("related_sources") or []
    # 토큰 절약: excerpt는 앞부분만
    related_trim = [
        {"title": r.get("title"), "url": r.get("url"), "stance": r.get("stance"),
         "excerpt": (r.get("excerpt") or "")[:400]}
        for r in related
    ]
    payload = {
        "headline_ko": dossier.get("headline_ko"),
        "headline_orig": dossier.get("headline_orig"),
        "primary_source": dossier.get("primary_source"),
        "topic_kind_hint": dossier.get("topic_kind"),
        "facts": dossier.get("facts"),
        "key_details": dossier.get("key_details"),
        "context_notes": dossier.get("context_notes"),
        "related_sources": related_trim,
    }
    return payload


def call_openai(api_key, model, messages):
    url = f"{BASE_URL}/chat/completions"
    body = json.dumps({
        "model": model,
        "messages": messages,
        "temperature": 0.3,
        "response_format": {"type": "json_object"},
    }).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Authorization": f"Bearer {api_key}",
                 "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:500]
        die(f"OpenAI HTTP {e.code}: {detail}", 4)
    except Exception as e:  # noqa: BLE001
        die(f"OpenAI 호출 실패: {e}", 4)
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        die(f"예상치 못한 응답 형식: {json.dumps(data)[:400]}", 4)


def assemble_sources(dossier):
    """출처 목록을 dossier에서 정확히 구성(LLM 미경유)."""
    out = []
    ps = dossier.get("primary_source") or {}
    if ps.get("url"):
        out.append({"title": ps.get("name") or ps.get("url"),
                    "url": ps["url"], "note": "1차 원천"})
    for r in (dossier.get("related_sources") or []):
        if r.get("url"):
            out.append({"title": r.get("title") or r["url"],
                        "url": r["url"], "note": r.get("stance") or "관련"})
    return out


def main():
    if len(sys.argv) < 2:
        die("usage: summarize_openai.py {workdir}", 2)
    workdir = sys.argv[1].rstrip("/")
    api_key, model = resolve_credentials()
    if not api_key:
        die("OPENAI_API_KEY 미설정(env·settings.local.json 모두 없음) — Claude 폴백으로 전환하세요.", 3)

    dossier = load_json(os.path.join(workdir, "03_dossier.json"), required=True)
    selection = load_json(os.path.join(workdir, "02_selection.json"), required=False)
    date, rnd = parse_date_round(workdir, selection)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content":
            "다음 dossier를 근거로 JSON을 작성하라.\n\n"
            + json.dumps(build_user_payload(dossier, selection), ensure_ascii=False)},
    ]
    raw = call_openai(api_key, model, messages)
    try:
        gen = json.loads(raw)
    except json.JSONDecodeError:
        die(f"LLM이 JSON이 아닌 응답 반환: {raw[:300]}", 4)

    # LLM 생성 텍스트 + 결정적 메타/링크 병합
    analysis = {
        "date": date,
        "round": rnd,
        "generator": f"openai:{model}",
        "headline_ko": gen.get("headline_ko") or dossier.get("headline_ko"),
        "primary_source": dossier.get("primary_source"),
        "image_url": dossier.get("image_url"),
        "topic_kind": gen.get("topic_kind") or dossier.get("topic_kind"),
        "perspective": gen.get("perspective") or "research",
        "keynote": gen.get("keynote") or [],
        "overview": gen.get("overview") or "",
        "main_content_html": gen.get("main_content_html") or "",
        "implications": gen.get("implications") or "",
        "sources": assemble_sources(dossier),
        "also_notable": (selection or {}).get("also_notable", [])[:3],
    }

    missing = [k for k in ("keynote", "overview", "main_content_html", "implications")
               if not analysis[k]]
    if missing:
        die(f"LLM 출력에 필수 본문 누락: {missing}", 4)

    out_path = os.path.join(workdir, "04_analysis.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)
    print(f"[ok] OpenAI({model}) 본문 서술 → {out_path} "
          f"(keynote {len(analysis['keynote'])}항, 출처 {len(analysis['sources'])}건)")


if __name__ == "__main__":
    main()
