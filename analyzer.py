"""
British English analyzer — Gemini API version.
Streams SSE events while Gemini analyzes the script.

SSE event shapes:
  {"type": "progress", "msg": "..."}
  {"type": "done",     "items": [...]}
  {"type": "error",    "msg": "..."}
"""

import json
import os

import google.generativeai as genai

_model = None

MODEL_NAME = "gemini-2.5-flash-preview"   # 사용자 지정 모델


def _get_model():
    global _model
    if _model is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY 환경 변수가 설정되지 않았습니다. "
                "Render 대시보드 → Environment 탭에서 추가하세요."
            )
        genai.configure(api_key=api_key)
        _model = genai.GenerativeModel(
            model_name=MODEL_NAME,
            system_instruction=_SYSTEM,
        )
    return _model


# ── Prompts ───────────────────────────────────────────────────────────────────

_SYSTEM = """\
당신은 영국 드라마·문화·언어 전문가입니다.
미국식 영어(American English)를 배운 한국 고등학생이 영국 드라마를 볼 때
이해하기 어려운 영국 특유의 요소를 찾아 한국어로 설명합니다.

항상 JSON 배열만 출력하고, 마크다운이나 다른 텍스트는 절대 포함하지 마세요."""

_USER_TMPL = """\
"{show}" 드라마의 스크립트입니다:

{script}

---

위 스크립트 전체를 꼼꼼히 읽고, 미국식 영어만 배운 한국 고등학생이 모를 수 있는 \
영국식 요소를 **최대한 많이** 찾아주세요. 의심스러우면 반드시 포함하세요.

【찾아야 할 항목】
1. slang — 영국 속어/슬랭 (bloody, bloke, mate, knackered, gutted, cheeky, \
   proper(부사), well(부사), dodgy, rubbish, brilliant, cheers, ta, innit, \
   sorted, fancy(동사), gobsmacked, minted, the nick 등)
2. idiom — 영국 숙어/관용 표현 (taking the mickey, over the moon, \
   Bob's your uncle, on the pull, cost a bomb, chuffed to bits, \
   give someone a bell, in a pickle, have a go, a bit of a do 등)
3. culture — 영국 문화 참조 (BBC, ITV, Channel 4, NHS, pub culture, \
   football(soccer), Premier League, Oxbridge, Sunday roast, fish and chips, \
   Marmite, Greggs, Bank Holiday, Guy Fawkes, Glastonbury 등)
4. person — 언급된 실존 인물 — 반드시 포함하고, \
   비슷한 한국 유명인으로 비유해 설명 (예: "한국의 유재석 같은 국민 MC")
5. company — 영국 기업·기관·브랜드 (M&S, Tesco, Boots, BBC, Sky, BT, \
   Royal Mail, HSBC, Barclays 등)
6. place — 영국 특유 지명/지역 표현 (the City, up North, East End, \
   Soho, Brixton, council estate 지역 함의 등)
7. vocabulary — 영국식 단어 (lift, boot, bonnet, biscuit, queue, fortnight, \
   solicitor, postcode, mobile, flat, rubbish bin 등)
8. social — 영국 계층·사회 표현 (posh, common, working-class, public school, \
   grammar school, council house, the gentry, old money 등)

【규칙】
- 스크립트에 실제로 등장한 순서(대사 순서)대로 나열
- 원래 문장(original_line) 반드시 포함
- 미국/영국 공통 표현(hello, thank you 등)은 제외
- 스크립트 앞뒤 메타데이터(제작진·저작권)는 무시
- 숙어·관용 표현 절대 빠트리지 마세요
- 실존 인물은 반드시 포함하고 한국인도 이해하도록 설명
- 설명에 맥락(왜 이 상황에서 이 표현을 썼는가) 포함

아래 JSON 배열 형식으로만 응답하세요. 다른 텍스트 없이:
[
  {{
    "original_line": "스크립트에서 해당 표현이 포함된 원래 문장 그대로",
    "term": "분석할 표현·단어·이름",
    "type": "slang|idiom|culture|person|company|place|vocabulary|social",
    "explanation": "한국어로 자세한 설명. 뜻, 어떤 상황에서 쓰는지, 왜 이 맥락에서 나왔는지, 배경지식 포함"
  }}
]"""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _sse(obj: dict) -> str:
    return "data: " + json.dumps(obj, ensure_ascii=False) + "\n\n"


def _extract_json(text: str) -> list:
    t = text.strip()
    if "```json" in t:
        t = t.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in t:
        t = t.split("```", 1)[1].split("```", 1)[0].strip()
    start = t.find("[")
    end = t.rfind("]")
    if start != -1 and end > start:
        t = t[start : end + 1]
    return json.loads(t)


# ── Public API ────────────────────────────────────────────────────────────────

MAX_SCRIPT_CHARS = 120_000


def analyze_stream(script: str, show: str):
    """Generator that yields SSE-formatted strings."""
    if not script or not script.strip():
        yield _sse({"type": "error", "msg": "분석할 스크립트가 없습니다."})
        return

    if len(script) > MAX_SCRIPT_CHARS:
        script = script[:MAX_SCRIPT_CHARS] + "\n\n[스크립트가 길어 앞부분만 분석합니다]"

    yield _sse({"type": "progress", "msg": "Gemini가 스크립트를 분석 중입니다. 1~2분 소요됩니다..."})

    try:
        model = _get_model()
    except RuntimeError as e:
        yield _sse({"type": "error", "msg": str(e)})
        return

    user_msg = _USER_TMPL.format(show=show or "알 수 없음", script=script)

    full_text = ""
    try:
        response = model.generate_content(
            user_msg,
            stream=True,
            generation_config=genai.GenerationConfig(
                max_output_tokens=16000,
                temperature=0.3,
            ),
        )

        heartbeat = 0
        for chunk in response:
            if chunk.text:
                full_text += chunk.text
                heartbeat += 1
                if heartbeat % 100 == 0:
                    yield _sse({"type": "progress", "msg": "분석 중... (응답 생성 중)"})

        items = _extract_json(full_text)
        yield _sse({"type": "done", "items": items})

    except Exception as e:
        err = str(e)
        if "API_KEY" in err or "api key" in err.lower():
            yield _sse({"type": "error", "msg": "API 키가 잘못됐습니다. Render 환경 변수 GEMINI_API_KEY를 확인하세요."})
        elif "not found" in err.lower() or "model" in err.lower():
            yield _sse({"type": "error", "msg": f"모델 '{MODEL_NAME}'을 찾을 수 없습니다. Google AI Studio에서 사용 가능한 모델명을 확인하세요."})
        elif json.JSONDecodeError.__name__ in type(e).__name__:
            yield _sse({"type": "error", "msg": f"응답 파싱 오류. 앞부분: {full_text[:300]}"})
        else:
            yield _sse({"type": "error", "msg": f"오류: {err}"})
