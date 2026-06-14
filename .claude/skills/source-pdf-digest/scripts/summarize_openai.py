#!/usr/bin/env python3
"""OpenAI(ChatGPT) 본문 서술기 — dossier → 04_analysis.json.

역할 분담: Claude collector가 스캔·선별·교차검증(1차 출처)해 03_dossier.json을
만들면, 이 스크립트가 OpenAI Chat Completions로 그 검증된 사실만 근거로
'무엇이 달라졌나·사실과 쟁점·왜 중요한가' 본문을 한글 서술한다(없는 사실 창작 금지).

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
키가 어디에도 없으면 exit 3 (Claude 폴백 신호). 모델 기본값 gpt-5.5.
  OPENAI_BASE_URL (선택, 기본 https://api.openai.com/v1)

실행:
  python3 summarize_openai.py {workdir}            # 본문 서술(GPT-5.5 드래프트) → 04_analysis.json
  python3 summarize_openai.py {workdir} --verify   # GPT-5.5 교차검증 → 04_crosscheck_openai.json
교차검증: GPT-5.5가 작성한 04_analysis.json을 Claude(Opus 4.8) analyst가 dossier와
대조해 교정하고, 그 교정본을 다시 이 --verify(GPT-5.5)가 사실성·가독성으로 재검증한다.
analyst는 GPT-5.5 지적사항을 반영해 최종 04_analysis.json을 확정한다(상호 교차검증).
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
    return key, (model or "gpt-5.5")


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
    "신뢰성 원칙: ① 핵심 수치·주장에는 출처(누가 발표·측정했는지)를 함께 밝힌다(예: \"OpenAI 자체 측정\", \"Epoch AI 분석\"). "
    "② 기업이 자체 발표한 벤치마크·성능치는 \'자체 보고\'·\'독립 검증 전\'임을 명시하고 단정하지 않는다. "
    "③ 추정·전망과 확정된 사실을 문장에서 구분한다(\'~로 보인다/추정된다\' vs \'~다\'). "
    "④ dossier에 근거가 약하면 단정 대신 한계를 적는다. 형용사·수식어를 줄이고 검증 가능한 사실 위주로 쓴다. "
    "반드시 아래 키를 가진 JSON 하나만 출력한다(코드블록·설명 금지):\n"
    "{\n"
    '  "headline_ko": "제목 — **원천(1차 출처) 제목 기반으로 간결하게**. 핵심 주체·대상만 담아 한 절로(예: \'앤스로픽, 프런티어 모델 Claude Fable 5·Mythos 5 공개\'). 군더더기 수식·평가어 금지. 부연 설명은 subhead로 분리하고 제목에 \'—\'로 덧붙이지 않는다. 35자 이내 권장",\n'
    '  "subhead": "부제 — 제목을 보완하는 한 줄 설명(선택). 제목에 다 못 담은 핵심 포인트 한 가지를 짧게. 불필요하면 빈 문자열. 40자 이내",\n'
    '  "topic_kind": "model|tech|research|policy|regulation|standard|investment|infra|chip|mixed 중 하나",\n'
    '  "perspective": "research|policy|both(주관점 명시) — \'왜 중요한가\' 섹션의 무게중심",\n'
    '  "keywords": ["제목 아래 배지로 노출할 주요 키워드 5개 이내. 기업·모델명·핵심 고유명사 위주(예: Anthropic, Mythos5, Fable5, Opus4.8). dossier에 등장한 표기 그대로, 일반어·관점명 금지"],\n'
    '  "stat_cards": [{"num": "핵심 수치 한 덩어리(예: 80.3%, $10/$50, <5%, 2×, 78.0%)", "label": "그 수치가 무엇인지 짧게(예: SWE-bench Pro 코딩, 입력/출력 100만 토큰 가격)"}],  // 그날 이슈를 한눈에 보여줄 KPI 3~4개. dossier에 있는 수치만. 비교·성능·가격·규모·점유율 등. 수치 이슈가 없으면 빈 배열\n'
    '  "chart": {"title": "비교 차트 제목(예: SWE-bench Pro — 에이전트 코딩 정확도)", "unit": "단위·각주(예: % · 높을수록 우수)", "series": [{"name": "항목명(모델/대상)", "value": 80.3, "highlight": true}]},  // 한 벤치마크/지표에서 대상들을 비교. 2~5개 항목, value는 숫자(단위 제외). 이번 이슈의 주인공 항목 하나에 highlight:true. 비교 수치가 없는 이슈(정책·투자 등)면 series를 빈 배열로\n'
    '  "keynote": ["\'한눈에 보기\' 핵심 요지 3~4개. 각 1~2문장. 무슨 일·왜 중요한지 + 가장 중요한 수치 1개를 포함해 바쁜 독자가 이것만 봐도 되게"],\n'
    '  "overview": "무엇이 달라졌나 — 이전과 비교해 무엇이 새로워졌고 무슨 변화가 생겼는지를 한 문단(3~5문장)으로. 도입부 성격. 세부 수치는 \'사실과 쟁점\'에 넘기고 변화의 큰 그림만.",\n'
    '  "main_content_html": "사실과 쟁점 — 이 섹션이 브리프의 깊이를 좌우한다. ① 검증된 사실관계를 연구자 수준으로 촘촘하게: dossier의 key_details에 있는 **수치·벤치마크·경쟁모델 비교값을 가능한 한 모두** 담고, 핵심 메커니즘·아키텍처·사양·가격·접근정책을 구체적으로 서술한다(모델명·수치·고유명사는 원문 그대로 인용). ② 이어 이 사안의 **쟁점·논란·미해결 질문**(예: 자체보고 벤치마크의 검증 여부, 비공개 수치, 상충하는 주장)을 사실과 구분해 짚는다. 분량은 충분히 길게(최소 4~6개 문장 단락 + 핵심 수치 불릿 4개 이상). 순수 HTML 조각: <p>…</p> 여러 개와 <ul class=\\"tight\\"><li>…</li></ul>, 강조는 <b>.",\n'
    '  "image_caption": "대표 이미지 설명 한 줄(무엇을 보여주는 이미지인지 + 출처사). dossier 이미지가 무엇인지 모르면 \'출처: {primary_source}\'로",\n'
    '  "implications": "왜 중요한가 — topic_kind에 맞는 관점(모델/기술/논문→연구·개발, 규제/표준/투자→정책, 경계→둘 다)으로 이 사안이 왜 중요한지를 분석한다. \'중요하다/새로운 기준이다\' 같은 일반론은 금지하고, **무엇이 구체적으로 어떻게 바뀌는지**(연구 방향·재현성·벤치마크 신뢰성, 또는 규제·표준·산업·안보)를 dossier 근거로 짚는다. 이어 **향후 관전 포인트**를 명시한다. 충분히 길게(4~6문장 이상). 순수 텍스트(필요 시 <b>만).",\n'
    "}\n"
    "분량 가이드: 전체가 A4 1~2페이지를 채우는 깊이로 쓴다(빈약하면 실패). \'사실과 쟁점\'을 가장 두껍게, \'무엇이 달라졌나\'는 압축적으로, \'왜 중요한가\'는 분석적으로. 피상적 요약·동어반복을 피하고 dossier의 디테일을 최대한 활용한다."
)


VERIFY_SYSTEM_PROMPT = (
    "당신은 과학기술 AI 동향 브리프의 엄정한 팩트체커이자 한글 에디터다. "
    "Claude(Opus 4.8)가 교정한 분석본(analysis)을, 검증된 1차 출처 dossier와 한 문장씩 대조해 검증한다. "
    "목표는 ① 정확성(모든 수치·고유명사·인과 주장이 dossier에 근거가 있는가), "
    "② 신뢰성(자체보고 벤치마크를 단정하지 않는가·출처 불명 단정이 없는가·추정과 사실을 구분하는가), "
    "③ 가독성(논리 흐름·문장 명료성·중복 제거)을 높은 수준으로 끌어올리는 것이다. "
    "dossier에 근거가 없는 진술(환각), 수치 불일치, 과장·홍보 표현을 반드시 찾아낸다. "
    "근거가 충분하면 통과시키고, 사소한 트집은 잡지 않는다. "
    "JSON 하나만 출력한다(코드블록·설명 금지):\n"
    "{\n"
    '  "overall_ok": true,            // 중대한 사실오류가 없으면 true\n'
    '  "confidence": 0.0,             // 검증 확신도 0~1\n'
    '  "issues": [                    // 발견한 문제(없으면 빈 배열). 심각도 high=사실오류/환각, medium=출처·단정 문제, low=표현\n'
    '    {"field": "overview|main_content_html|implications|keynote|stat_cards|chart|keywords|headline_ko|subhead",\n'
    '     "severity": "high|medium|low",\n'
    '     "problem": "무엇이 dossier와 어긋나는지/왜 문제인지 구체적으로",\n'
    '     "suggested_fix": "어떻게 고쳐야 하는지(대체 문구 또는 삭제 제안)"}\n'
    "  ],\n"
    '  "readability_notes": ["가독성·흐름 개선 제안(있으면)"],\n'
    '  "verdict_summary": "한두 문장 총평"\n'
    "}\n"
    "issues의 모든 지적은 dossier 근거에 입각해야 하며, 추측으로 새 사실을 만들지 마라."
)


def build_verify_payload(dossier, analysis):
    """검증용 페이로드 — dossier 근거 + 검증 대상 analysis 본문 필드."""
    return {
        "dossier_evidence": {
            "headline": dossier.get("headline_ko") or dossier.get("headline_orig"),
            "primary_source": dossier.get("primary_source"),
            "facts": dossier.get("facts"),
            "key_details": dossier.get("key_details"),
            "context_notes": dossier.get("context_notes"),
        },
        "analysis_to_verify": {
            "headline_ko": analysis.get("headline_ko"),
            "subhead": analysis.get("subhead"),
            "keywords": analysis.get("keywords"),
            "stat_cards": analysis.get("stat_cards"),
            "chart": analysis.get("chart"),
            "keynote": analysis.get("keynote"),
            "overview": analysis.get("overview"),
            "main_content_html": analysis.get("main_content_html"),
            "implications": analysis.get("implications"),
        },
    }


def verify_main(workdir, api_key, model):
    """GPT-5.5 교차검증 — 04_analysis.json을 dossier와 대조해 04_crosscheck_openai.json 생성."""
    dossier = load_json(os.path.join(workdir, "03_dossier.json"), required=True)
    analysis = load_json(os.path.join(workdir, "04_analysis.json"), required=True)
    messages = [
        {"role": "system", "content": VERIFY_SYSTEM_PROMPT},
        {"role": "user", "content":
            "다음 dossier 근거로 analysis_to_verify를 검증하고 JSON으로 보고하라.\n\n"
            + json.dumps(build_verify_payload(dossier, analysis), ensure_ascii=False)},
    ]
    raw = call_openai(api_key, model, messages)
    try:
        verdict = json.loads(raw)
    except json.JSONDecodeError:
        die(f"검증 LLM이 JSON이 아닌 응답 반환: {raw[:300]}", 4)
    verdict["verifier"] = f"openai:{model}"
    out_path = os.path.join(workdir, "04_crosscheck_openai.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(verdict, f, ensure_ascii=False, indent=2)
    issues = verdict.get("issues") or []
    highs = sum(1 for i in issues if isinstance(i, dict) and i.get("severity") == "high")
    print(f"[ok] GPT-5.5 교차검증 → {out_path} "
          f"(overall_ok={verdict.get('overall_ok')}, issues {len(issues)}건·high {highs})")


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
    # 일부 신모델(gpt-5.x)은 temperature 커스텀을 막고 기본값(1)만 허용 → 1로 고정(호환).
    body = json.dumps({
        "model": model,
        "messages": messages,
        "temperature": 1,
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


def normalize_chart(chart):
    """차트 series의 pct(막대 폭 %)를 최댓값=100 기준으로 결정적으로 계산(LLM 산술 미신뢰)."""
    if not isinstance(chart, dict):
        return None
    series = [s for s in (chart.get("series") or []) if isinstance(s, dict)]
    vals = []
    for s in series:
        try:
            vals.append(float(s.get("value")))
        except (TypeError, ValueError):
            vals.append(None)
    nums = [v for v in vals if v is not None]
    if len(nums) < 2:  # 비교 대상이 2개 미만이면 차트 의미 없음
        return None
    mx = max(nums) or 1.0
    out = []
    for s, v in zip(series, vals):
        if v is None:
            continue
        out.append({
            "name": str(s.get("name") or ""),
            "value": s.get("value"),
            "pct": round(max(2.0, v / mx * 100.0), 1),  # 최소 2%는 보여 막대가 사라지지 않게
            "highlight": bool(s.get("highlight")),
        })
    if not any(s["highlight"] for s in out):  # 강조 미지정 시 최댓값 항목 강조
        top = max(range(len(out)), key=lambda i: float(out[i]["value"] or 0))
        out[top]["highlight"] = True
    return {"title": str(chart.get("title") or ""),
            "unit": str(chart.get("unit") or ""),
            "series": out[:5]}


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
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    if not args:
        die("usage: summarize_openai.py {workdir} [--verify]", 2)
    workdir = args[0].rstrip("/")
    api_key, model = resolve_credentials()
    if not api_key:
        die("OPENAI_API_KEY 미설정(env·settings.local.json 모두 없음) — Claude 폴백으로 전환하세요.", 3)

    if "--verify" in flags:
        verify_main(workdir, api_key, model)
        return

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
        "subhead": (gen.get("subhead") or "").strip(),
        "primary_source": dossier.get("primary_source"),
        "image_url": dossier.get("image_url"),
        "topic_kind": gen.get("topic_kind") or dossier.get("topic_kind"),
        "perspective": gen.get("perspective") or "research",
        "keywords": (gen.get("keywords") or [])[:5],
        "stat_cards": [s for s in (gen.get("stat_cards") or [])
                       if isinstance(s, dict) and s.get("num")][:4],
        "chart": normalize_chart(gen.get("chart")),
        "image_caption": (gen.get("image_caption") or "").strip(),
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
