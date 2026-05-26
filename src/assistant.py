"""The Claude-powered assistant brain. Builds context, calls Opus 4.7
with adaptive thinking + prompt caching, parses the JSON response.

The system prompt (stable_system_prompt) is cached so we only pay full
price the first time per 5-minute window — see shared/prompt-caching.md."""

from __future__ import annotations
import json
import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import anthropic

from .prompts import stable_system_prompt, render_user_turn
from .memory import Memory
from .sources import local_notes

log = logging.getLogger(__name__)


@dataclass
class AssistantReply:
    message: str
    voice_friendly: bool
    internal_note: str | None
    raw: str
    usage: dict


class Assistant:
    def __init__(self, cfg: dict[str, Any], memory: Memory):
        self.cfg = cfg
        self.memory = memory
        self.client = anthropic.Anthropic()  # uses ANTHROPIC_API_KEY
        self.model_id = cfg["model"]["id"]
        self.effort = cfg["model"]["effort"]
        self.tz = os.environ.get("TIMEZONE", "Asia/Seoul")

    # ---------- context assembly ----------

    def _gather_context(self) -> list[str]:
        """Pull from every enabled source. Order from most-stable to most-
        volatile so we can cache more later if it pays off."""
        blocks: list[str] = []
        sources = self.cfg["sources"]

        # 1) Local notes (always cheap, no auth)
        if sources["local_notes"]["enabled"]:
            block = local_notes.fetch_notes_block(sources["local_notes"]["path"])
            if block:
                blocks.append(block)

        # 2) Google Calendar
        if sources["google_calendar"]["enabled"]:
            try:
                from .sources.google_calendar import fetch_calendar_block

                blocks.append(
                    fetch_calendar_block(
                        lookahead_days=sources["google_calendar"]["lookahead_days"],
                        tz_name=self.tz,
                    )
                )
            except Exception as e:
                log.warning("calendar fetch failed: %s", e)

        # 3) Google Drive
        if sources["google_drive"]["enabled"]:
            try:
                from .sources.google_drive import fetch_drive_block

                block = fetch_drive_block(
                    folder_ids=sources["google_drive"]["folder_ids"],
                    lookback_days=sources["google_drive"]["lookback_days"],
                )
                if block:
                    blocks.append(block)
            except Exception as e:
                log.warning("drive fetch failed: %s", e)

        # 4) Recent telegram dialogue (last ~12 turns)
        recent = self.memory.recent_messages(limit=12)
        if recent:
            lines = ["## 최근 텔레그램 대화"]
            for r in recent:
                who = "나" if r["direction"] == "in" else "비서"
                stamp = r["ts"][:16].replace("T", " ")
                text = r["text"].replace("\n", " ")[:200]
                lines.append(f"- [{stamp}] {who}: {text}")
            blocks.append("\n".join(lines))

        # 5) Open todos
        todos = self.memory.open_todos()
        if todos:
            lines = ["## 열린 할 일"]
            for t in todos:
                lines.append(f"- {t['text']}")
            blocks.append("\n".join(lines))

        # 6) Internal notes the model left for itself
        notes = self.memory.unconsumed_notes()
        if notes:
            blocks.append("## 비서 메모 (지난 호출에서 남긴 것)\n" + "\n".join(notes))

        return blocks

    # ---------- model call ----------

    def generate(self, kind: str) -> AssistantReply:
        now = datetime.now(timezone.utc)
        ctx_blocks = self._gather_context()
        user_turn = render_user_turn(
            kind=kind, now=now, tz=self.tz, context_blocks=ctx_blocks
        )

        # The stable system prompt is cached. cache_control on its last
        # block ⇒ the whole system + tools prefix gets cache-read on
        # subsequent calls within the TTL.
        system_blocks = [
            {
                "type": "text",
                "text": stable_system_prompt(self.cfg),
                "cache_control": {"type": "ephemeral"},
            }
        ]

        resp = self.client.messages.create(
            model=self.model_id,
            max_tokens=2000,
            system=system_blocks,
            thinking={"type": "adaptive"},
            output_config={"effort": self.effort},
            messages=[{"role": "user", "content": user_turn}],
        )

        # Extract final text block
        text = ""
        for block in resp.content:
            if block.type == "text":
                text = block.text
                break

        parsed = _parse_json_envelope(text)
        usage = {
            "input_tokens": resp.usage.input_tokens,
            "output_tokens": resp.usage.output_tokens,
            "cache_read": getattr(resp.usage, "cache_read_input_tokens", 0),
            "cache_create": getattr(resp.usage, "cache_creation_input_tokens", 0),
        }
        log.info("usage: %s", usage)

        reply = AssistantReply(
            message=parsed.get("message", text).strip(),
            voice_friendly=bool(parsed.get("voice_friendly", True)),
            internal_note=parsed.get("internal_note"),
            raw=text,
            usage=usage,
        )

        if reply.internal_note:
            self.memory.add_note(reply.internal_note)

        return reply


def _parse_json_envelope(text: str) -> dict:
    """Claude wraps its JSON in a fence sometimes; tolerate either."""
    text = text.strip()

    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        candidate = fence.group(1)
    else:
        first = text.find("{")
        last = text.rfind("}")
        if first == -1 or last == -1:
            return {"message": text}
        candidate = text[first : last + 1]

    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return {"message": text}
