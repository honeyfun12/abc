"""The Claude-powered assistant brain.

Calls Claude via the local `claude` CLI (Claude Code) using the
claude-agent-sdk. This goes against your Max subscription quota — NO
additional API charges.

Prerequisites:
  - `claude` CLI installed (https://claude.ai/code)
  - `claude /login` completed with your Max account
"""

from __future__ import annotations
import json
import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from claude_agent_sdk import (
    query,
    ClaudeAgentOptions,
    AssistantMessage,
    TextBlock,
)

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


class Assistant:
    def __init__(self, cfg: dict[str, Any], memory: Memory):
        self.cfg = cfg
        self.memory = memory
        self.model_id = cfg["model"]["id"]
        self.tz = os.environ.get("TIMEZONE", "Asia/Seoul")

    # ---------- context assembly ----------

    def _gather_context(self) -> list[str]:
        blocks: list[str] = []
        sources = self.cfg["sources"]

        if sources["local_notes"]["enabled"]:
            block = local_notes.fetch_notes_block(sources["local_notes"]["path"])
            if block:
                blocks.append(block)

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

        recent = self.memory.recent_messages(limit=12)
        if recent:
            lines = ["## 최근 텔레그램 대화"]
            for r in recent:
                who = "나" if r["direction"] == "in" else "비서"
                stamp = r["ts"][:16].replace("T", " ")
                text = r["text"].replace("\n", " ")[:200]
                lines.append(f"- [{stamp}] {who}: {text}")
            blocks.append("\n".join(lines))

        todos = self.memory.open_todos()
        if todos:
            lines = ["## 열린 할 일"]
            for t in todos:
                lines.append(f"- {t['text']}")
            blocks.append("\n".join(lines))

        notes = self.memory.unconsumed_notes()
        if notes:
            blocks.append("## 비서 메모 (지난 호출에서 남긴 것)\n" + "\n".join(notes))

        return blocks

    # ---------- model call ----------

    async def generate(self, kind: str) -> AssistantReply:
        now = datetime.now(timezone.utc)
        ctx_blocks = self._gather_context()
        user_turn = render_user_turn(
            kind=kind, now=now, tz=self.tz, context_blocks=ctx_blocks
        )

        options = ClaudeAgentOptions(
            system_prompt=stable_system_prompt(self.cfg),
            model=self.model_id,
            max_turns=1,
            allowed_tools=[],          # 도구 호출 X — 텍스트만
            setting_sources=[],        # 사용자 CLAUDE.md 등 외부 설정 미로드
            permission_mode="default",
        )

        cli_path = os.environ.get("CLAUDE_CLI_PATH")
        if cli_path:
            options.path_to_claude_code_executable = cli_path  # 일부 버전에서 지원

        text_parts: list[str] = []
        try:
            async for msg in query(prompt=user_turn, options=options):
                if isinstance(msg, AssistantMessage):
                    for block in msg.content:
                        if isinstance(block, TextBlock):
                            text_parts.append(block.text)
        except Exception as e:
            log.exception("claude-agent-sdk query failed: %s", e)
            return AssistantReply(
                message="(비서가 잠깐 막혔어요. 잠시 후 다시 시도해주세요.)",
                voice_friendly=False,
                internal_note=None,
                raw=str(e),
            )

        text = "\n".join(text_parts).strip()
        parsed = _parse_json_envelope(text)

        reply = AssistantReply(
            message=parsed.get("message", text).strip(),
            voice_friendly=bool(parsed.get("voice_friendly", True)),
            internal_note=parsed.get("internal_note"),
            raw=text,
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
