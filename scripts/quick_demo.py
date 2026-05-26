r"""한 번 동작 확인용. 깔 거 없음 — Python 표준 라이브러리만 씀.

세 가지 방법으로 실행 가능:

방법 1) PowerShell:
    $env:TG_TOKEN="너_봇토큰"
    python scripts\quick_demo.py

방법 2) .env 파일 만들기 (한 번만):
    abc 폴더 안에 .env 라는 파일 만들고 그 안에 한 줄:
        TG_TOKEN=너_봇토큰
    그 후 scripts\quick_demo.py 더블클릭

방법 3) 그냥 더블클릭:
    창이 토큰 물어봄. 거기 붙여넣기.

어떤 방법이든 끝나면 창에 "엔터 누르면 닫힘" 떠서 출력 확인 가능.
"""

from __future__ import annotations
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path


def get_token() -> str | None:
    # 1. 환경변수
    t = os.environ.get("TG_TOKEN")
    if t and t.strip():
        return t.strip()

    # 2. abc 폴더의 .env 파일
    env_file = Path(__file__).resolve().parent.parent / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("TG_TOKEN=") or line.startswith("TELEGRAM_BOT_TOKEN="):
                val = line.split("=", 1)[1].strip().strip('"').strip("'")
                if val:
                    return val

    # 3. 사용자에게 물어보기
    print()
    print("토큰을 못 찾았어. BotFather에서 받은 봇 토큰을 붙여넣고 엔터:")
    print("(예: 123456789:ABCdefGhIjKlMnOpQrStUvWxYz)")
    try:
        token = input("TG_TOKEN: ").strip()
        return token or None
    except EOFError:
        return None


def run() -> None:
    print("=" * 60)
    print(" 텔레그램 비서 데모 — 한 발 쏘기")
    print("=" * 60)
    print()

    token = get_token()
    if not token:
        print("[오류] 토큰을 못 받았어.")
        return

    api = f"https://api.telegram.org/bot{token}"

    print("[1/3] 봇 토큰 확인 중...")
    try:
        with urllib.request.urlopen(f"{api}/getMe", timeout=15) as resp:
            me = json.loads(resp.read())
    except Exception as e:
        print(f"[오류] 텔레그램 API 호출 실패: {e}")
        print("   인터넷 연결 확인해보고, 토큰이 맞는지 확인해줘.")
        return

    if not me.get("ok"):
        print(f"[오류] 봇 토큰이 이상해: {me}")
        return
    print(f"   봇: @{me['result']['username']}")
    print()

    print("[2/3] 너 chat_id 찾는 중...")
    try:
        with urllib.request.urlopen(f"{api}/getUpdates", timeout=15) as resp:
            updates = json.loads(resp.read())
    except Exception as e:
        print(f"[오류] getUpdates 실패: {e}")
        return

    msgs = [u for u in updates.get("result", []) if u.get("message")]
    if not msgs:
        print("   아직 봇한테 받은 메시지가 없어.")
        print()
        print(f"   📱 텔레그램 열어서 @{me['result']['username']} 찾아서")
        print("      'START' 누르거나 '안녕' 같은 거 한 번 보내고")
        print("      이 스크립트 다시 실행해줘.")
        return

    chat_id = msgs[-1]["message"]["chat"]["id"]
    sender_name = msgs[-1]["message"]["from"].get("first_name", "?")
    print(f"   chat_id={chat_id} ({sender_name})")
    print()

    print("[3/3] 샘플 메시지 전송 중...")
    msg = (
        "좋은 아침. 일어났네.\n\n"
        "오늘 가장 중요한 거 하나만 골라보자. 거창한 거 말고 — "
        "끝내고 나면 '오늘 하긴 했네' 싶을 그런 거 한 줄로.\n\n"
        "떠오르는 거 있으면 그냥 여기 답장으로 줘. 없으면 '없음'이라고 해도 돼."
    )

    try:
        resp = urllib.request.urlopen(
            urllib.request.Request(
                f"{api}/sendMessage",
                data=urllib.parse.urlencode(
                    {"chat_id": chat_id, "text": msg}
                ).encode("utf-8"),
            ),
            timeout=15,
        )
        result = json.loads(resp.read())
    except Exception as e:
        print(f"[오류] sendMessage 실패: {e}")
        return

    if result.get("ok"):
        print("   ✓ 전송 성공!")
        print()
        print(f"   📱 텔레그램 열어서 @{me['result']['username']} 확인해봐.")
    else:
        print(f"[오류] 전송 실패: {result}")


def main() -> int:
    try:
        run()
    except KeyboardInterrupt:
        print("\n[중단됨]")
    except Exception as e:
        print(f"\n[예기치 못한 오류] {e}")
        import traceback
        traceback.print_exc()
    finally:
        print()
        print("=" * 60)
        try:
            input(" 엔터 누르면 닫힘...")
        except EOFError:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
