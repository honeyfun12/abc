"""
British English analyzer — streams SSE events while Claude analyzes a script.

Each SSE event is one of:
  {"type": "progress", "msg": "..."}
  {"type": "done",     "items": [...]}
  {"type": "error",    "msg": "..."}
"""

import json
import os

import anthropic

_client = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY 환경 변수가 설정되지 않았습니다. "
                "터미널에서 'export ANTHROPIC_API_KEY=sk-ant-...' 를 실행하세요."
            )
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


# ── Prompt ────────────────────────────────────────────────────────────────────

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
영국식 요소를 **최대한 많이** 찾아주세요. 숫자보다 적게 찾으면 안 됩니다. \
의심스러우면 반드시 포함하세요.

【찾아야 할 항목 목록】
1. slang — 영국 속어/슬랭 (bloody, bloke, mate, knackered, gutted, cheeky, \
   proper(부사), well(부사), dodgy, rubbish, brilliant, cheers, ta, innit, \
   sorted, fancy(동사), bits and bobs, the nick, gobsmacked, minted 등)
2. idiom — 영국 숙어/관용 표현 (taking the mickey, over the moon, \
   Bob's your uncle, under the weather, on the pull, a bit of a do, \
   have a go, give someone a bell, cost a bomb, in a pickle, \
   the dog's bollocks, chuffed to bits, a bit of alright 등)
3. culture — 영국 문화 참조 (BBC, ITV, Channel 4, NHS, pub culture, \
   football(soccer), Premier League, Oxbridge, private school vs state school, \
   council estate, Sunday roast, fish and chips, Marmite, Greggs, \
   Bank Holiday, Guy Fawkes, Bonfire Night, Glastonbury 등)
4. person — 언급된 실존 인물 (유명인, 정치인, 역사 인물, 스포츠 스타 등) — \
   반드시 포함하고, 비슷한 한국 유명인으로 비유하거나 \
   "한국의 ___과 비슷한" 식으로 친숙하게 설명
5. company — 영국 기업·기관·브랜드 (Marks & Spencer(M&S), Tesco, Boots, \
   HSBC, Barclays, BT, Sky, Virgin, Royal Mail, Network Rail 등)
6. place — 영국 특유 지명/지역 표현 (the City(런던 금융 중심가), \
   up North/down South, the East End, Soho, Brixton, Coronation Street \
   같은 지역 함의, 스코틀랜드·웨일스·북아일랜드 관련 표현 등)
7. vocabulary — 영국식 단어(미국식과 다른 단어) \
   (lift=엘리베이터, boot=트렁크, bonnet=보닛, biscuit=쿠키, \
   queue=줄 서다, fortnight=2주, solicitor=변호사, \
   postcode=우편번호, mobile=휴대폰 등)
8. social — 영국 계층·사회 관련 표현 (posh, common, working-class, \
   upper-class, public school(사립 귀족 학교), grammar school, \
   comprehensive, council house, the gentry, old money 등)

【규칙】
- 스크립트에 실제로 등장한 **순서(대사가 나온 순서)** 대로 나열
- 각 항목에 원래 문장(original_line) 반드시 포함
- 단순한 영미 공통 표현(hello, thank you, let me know 등)은 제외
- 스크립트 앞뒤의 메타데이터(제작진·저작권·방영 정보)는 무시
- 숙어·관용 표현은 특히 절대 빠트리지 마세요
- 사람 이름이 나오면 반드시 포함하고, 한국인도 이해할 수 있도록 설명
- 맥락(왜 이 상황에서 이 표현을 썼는가)을 설명에 포함

아래 JSON 배열 형식으로만 응답하세요. 다른 텍스트 없이:
[
  {{
    "original_line": "스크립트에서 해당 표현이 포함된 원래 문장 그대로",
    "term": "분석할 표현·단어·이름",
    "type": "slang|idiom|culture|person|company|place|vocabulary|social",
    "explanation": "한국어로 자세한 설명. 뜻, 어떤 상황에서 쓰는지, 왜 이 맥락에서 나왔는지, 관련 배경지식 포함"
  }}
]"""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _sse(obj: dict) -> str:
    return "data: " + json.dumps(obj, ensure_ascii=False) + "\n\n"


def _extract_json(text: str) -> list:
    """Robustly extract a JSON array from Claude's response."""
    t = text.strip()
    # Strip markdown code fences if present
    if "```json" in t:
        t = t.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in t:
        t = t.split("```", 1)[1].split("```", 1)[0].strip()
    # Find outermost [ ... ]
    start = t.find("[")
    end = t.rfind("]")
    if start != -1 and end > start:
        t = t[start : end + 1]
    return json.loads(t)


# ── Public API ────────────────────────────────────────────────────────────────

MAX_SCRIPT_CHARS = 120_000  # ~30K tokens — well within 200K context window


def analyze_stream(script: str, show: str):
    """
    Generator that yields SSE-formatted strings.
    Call from a Flask route with stream_with_context().
    """
    if not script or not script.strip():
        yield _sse({"type": "error", "msg": "분석할 스크립트가 없습니다."})
        return

    # Trim if necessary
    if len(script) > MAX_SCRIPT_CHARS:
        script = script[:MAX_SCRIPT_CHARS] + "\n\n[스크립트가 길어 앞부분만 분석합니다]"

    yield _sse({"type": "progress", "msg": "Claude가 스크립트를 분석 중입니다. 에피소드 길이에 따라 1~2분 소요됩니다..."})

    try:
        client = _get_client()
    except RuntimeError as e:
        yield _sse({"type": "error", "msg": str(e)})
        return

    user_msg = _USER_TMPL.format(show=show or "알 수 없음", script=script)

    full_text = ""
    try:
        with client.messages.stream(
            model="claude-opus-4-6",
            max_tokens=16000,
            thinking={"type": "adaptive"},
            system=[
                {
                    "type": "text",
                    "text": _SYSTEM,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_msg}],
        ) as stream:
            heartbeat = 0
            for text in stream.text_stream:
                full_text += text
                heartbeat += 1
                if heartbeat % 300 == 0:
                    yield _sse({"type": "progress", "msg": "분석 중... (응답 생성 중)"})

        items = _extract_json(full_text)
        yield _sse({"type": "done", "items": items})

    except anthropic.AuthenticationError:
        yield _sse({"type": "error", "msg": "API 키가 잘못됐습니다. ANTHROPIC_API_KEY를 확인해 주세요."})
    except anthropic.RateLimitError:
        yield _sse({"type": "error", "msg": "API 요청 한도 초과입니다. 잠시 후 다시 시도해 주세요."})
    except json.JSONDecodeError as e:
        yield _sse({"type": "error", "msg": f"Claude 응답 파싱 오류: {e}\n\n원문 앞부분:\n{full_text[:500]}"})
    except Exception as e:
        yield _sse({"type": "error", "msg": f"분석 중 오류가 발생했습니다: {e}"})
