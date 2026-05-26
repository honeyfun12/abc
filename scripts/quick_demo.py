"""한 번 동작 확인용. 깔 거 없음 — Python 표준 라이브러리만 씀.

사용법:
    1. 텔레그램에서 너 봇 (예: @Secretary_is_not_funny_bot) 한테
       아무 메시지나 한 번 보내. (이걸 안 하면 chat_id 못 찾음)
    2. 터미널:
       export TG_TOKEN=너_봇토큰
       python3 scripts/quick_demo.py

샘플 morning brief 한 발 도착하면 — 시스템이 너 전화기까지 닿는 게
확인된 거. 그다음 README 6단계 따라서 실 가동.
"""

from __future__ import annotations
import json
import os
import sys
import urllib.parse
import urllib.request


def main() -> None:
    token = os.environ.get("TG_TOKEN")
    if not token:
        sys.exit("환경변수 TG_TOKEN 안 잡혔어. 예: export TG_TOKEN=123456:ABC...")

    api = f"https://api.telegram.org/bot{token}"

    # 1) bot 확인
    me = json.loads(urllib.request.urlopen(f"{api}/getMe", timeout=10).read())
    if not me.get("ok"):
        sys.exit(f"봇 토큰이 이상해: {me}")
    print(f"봇 확인됨: @{me['result']['username']}")

    # 2) chat_id 찾기
    updates = json.loads(
        urllib.request.urlopen(f"{api}/getUpdates", timeout=10).read()
    )
    if not updates.get("result"):
        sys.exit(
            "아직 봇한테 메시지가 안 와 있어.\n"
            f"  텔레그램에서 @{me['result']['username']} 한테 '안녕' 같은 거 한 번 보내고\n"
            "  다시 이 스크립트 실행해줘."
        )
    chat_id = updates["result"][-1]["message"]["chat"]["id"]
    sender_name = updates["result"][-1]["message"]["from"].get("first_name", "?")
    print(f"chat_id={chat_id} ({sender_name})")

    # 3) 비서 톤 샘플 메시지
    msg = (
        "좋은 아침. 일어났네.\n\n"
        "오늘 가장 중요한 거 하나만 골라보자. 거창한 거 말고 — "
        "끝내고 나면 \"오늘 하긴 했네\" 싶을 그런 거 한 줄로.\n\n"
        "떠오르는 거 있으면 그냥 여기 답장으로 줘. 없으면 \"없음\"이라고 해도 돼."
    )

    resp = urllib.request.urlopen(
        urllib.request.Request(
            f"{api}/sendMessage",
            data=urllib.parse.urlencode({"chat_id": chat_id, "text": msg}).encode(),
        ),
        timeout=10,
    )
    print(f"\n전송: {resp.status}. 텔레그램 확인해봐.")


if __name__ == "__main__":
    main()
