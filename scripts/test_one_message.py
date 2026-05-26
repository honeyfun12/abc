"""Smoke test — generate one message of a given kind and print it.
Doesn't touch Telegram. Useful for tuning the prompt.

Usage:
    python scripts/test_one_message.py morning_brief
    python scripts/test_one_message.py focus_nudge
    python scripts/test_one_message.py evening_reflection
"""

from __future__ import annotations
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import yaml
from dotenv import load_dotenv

from src.memory import Memory
from src.assistant import Assistant


async def amain() -> None:
    load_dotenv()

    kind = sys.argv[1] if len(sys.argv) > 1 else "morning_brief"
    valid = {
        "morning_brief",
        "focus_nudge",
        "pulse_check",
        "evening_reflection",
        "reply",
    }
    if kind not in valid:
        raise SystemExit(f"Unknown kind: {kind}. Pick one of {valid}.")

    with open("./config.yaml", "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    memory = Memory("./assistant.db")
    assistant = Assistant(cfg, memory)
    reply = await assistant.generate(kind)

    print("─" * 60)
    print(f"KIND: {kind}")
    print("─" * 60)
    print(reply.message)
    print("─" * 60)
    print(f"voice_friendly: {reply.voice_friendly}")
    if reply.internal_note:
        print(f"internal_note:  {reply.internal_note}")


if __name__ == "__main__":
    asyncio.run(amain())
