"""Telegram interface.

Two responsibilities:
1. Receive whatever the user types/voice-notes → log → ask Claude for a reply.
2. Send proactive nudges from the scheduler.

The scheduler calls `send_proactive(kind)`; the bot's polling loop handles
inbound user messages."""

from __future__ import annotations
import asyncio
import logging
import os
from pathlib import Path

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from .assistant import Assistant
from .memory import Memory
from .tts import TTS

log = logging.getLogger(__name__)


class Bot:
    def __init__(
        self,
        cfg: dict,
        assistant: Assistant,
        memory: Memory,
        tts: TTS,
    ):
        self.cfg = cfg
        self.assistant = assistant
        self.memory = memory
        self.tts = tts
        self.chat_id = int(os.environ["TELEGRAM_CHAT_ID"])

        token = os.environ["TELEGRAM_BOT_TOKEN"]
        self.app: Application = Application.builder().token(token).build()
        self._wire()

    def _wire(self) -> None:
        self.app.add_handler(CommandHandler("start", self._cmd_start))
        self.app.add_handler(CommandHandler("brief", self._cmd_brief))
        self.app.add_handler(CommandHandler("pulse", self._cmd_pulse))
        self.app.add_handler(CommandHandler("reflect", self._cmd_reflect))
        self.app.add_handler(CommandHandler("todos", self._cmd_todos))
        self.app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self._on_text)
        )
        self.app.add_handler(MessageHandler(filters.VOICE, self._on_voice))

    # ---- commands ----

    async def _cmd_start(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if update.effective_chat.id != self.chat_id:
            return
        await update.message.reply_text(
            "안녕. 비서야. 그냥 평소처럼 얘기해 — 다 듣고 기억하고 있을게.\n\n"
            "/brief — 아침 브리프 강제 호출\n"
            "/pulse — 지금 컨디션 체크\n"
            "/reflect — 저녁 회고\n"
            "/todos — 열린 할 일"
        )

    async def _cmd_brief(self, u, c):
        await self._send_proactive("morning_brief")

    async def _cmd_pulse(self, u, c):
        await self._send_proactive("pulse_check")

    async def _cmd_reflect(self, u, c):
        await self._send_proactive("evening_reflection")

    async def _cmd_todos(self, update, ctx):
        if update.effective_chat.id != self.chat_id:
            return
        todos = self.memory.open_todos()
        if not todos:
            await update.message.reply_text("열린 할 일 없어. 깨끗하다.")
            return
        lines = ["열린 할 일:"]
        for t in todos:
            lines.append(f"- {t['text']}")
        await update.message.reply_text("\n".join(lines))

    # ---- inbound ----

    async def _on_text(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if update.effective_chat.id != self.chat_id:
            return
        text = update.message.text
        self.memory.log_message(direction="in", text=text)
        await self._reply_to_user(text)

    async def _on_voice(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if update.effective_chat.id != self.chat_id:
            return
        # Transcribe via OpenAI Whisper if available, otherwise just log presence
        transcript = await self._transcribe_voice(update)
        if not transcript:
            self.memory.log_message(direction="in", text="(음성 메시지 — 전사 실패)")
            return
        self.memory.log_message(direction="in", text=f"(음성) {transcript}")
        await self._reply_to_user(transcript)

    async def _transcribe_voice(self, update: Update) -> str | None:
        if not os.environ.get("OPENAI_API_KEY"):
            return None
        try:
            file = await update.message.voice.get_file()
            tmp = Path("/tmp") / f"tg_{update.message.voice.file_unique_id}.ogg"
            await file.download_to_drive(custom_path=str(tmp))

            from openai import OpenAI

            client = OpenAI()
            with open(tmp, "rb") as f:
                result = client.audio.transcriptions.create(
                    model="whisper-1", file=f, language="ko"
                )
            tmp.unlink(missing_ok=True)
            return result.text
        except Exception as e:
            log.warning("voice transcription failed: %s", e)
            return None

    async def _reply_to_user(self, user_text: str) -> None:
        await self.app.bot.send_chat_action(self.chat_id, ChatAction.TYPING)
        # Run blocking Anthropic call in a thread.
        reply = await asyncio.to_thread(self.assistant.generate, "reply")
        await self._dispatch(reply, kind="reply")

    # ---- outbound ----

    async def send_proactive_async(self, kind: str) -> None:
        await self._send_proactive(kind)

    async def _send_proactive(self, kind: str) -> None:
        reply = await asyncio.to_thread(self.assistant.generate, kind)
        await self._dispatch(reply, kind=kind)

    async def _dispatch(self, reply, *, kind: str) -> None:
        text = reply.message
        voice_path = None

        if self.tts.should_voice(text, reply.voice_friendly):
            await self.app.bot.send_chat_action(self.chat_id, ChatAction.RECORD_VOICE)
            voice_path = await asyncio.to_thread(self.tts.synth, text)

        await self.app.bot.send_message(chat_id=self.chat_id, text=text)

        if voice_path:
            try:
                with open(voice_path, "rb") as f:
                    await self.app.bot.send_voice(chat_id=self.chat_id, voice=f)
            except Exception as e:
                log.warning("send_voice failed: %s", e)
            finally:
                try:
                    Path(voice_path).unlink(missing_ok=True)
                except Exception:
                    pass

        self.memory.log_message(
            direction="out",
            kind=kind,
            text=text,
            voice_path=str(voice_path) if voice_path else None,
        )

    # ---- lifecycle ----

    async def start(self) -> None:
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling(drop_pending_updates=True)
        log.info("Telegram bot started.")

    async def stop(self) -> None:
        await self.app.updater.stop()
        await self.app.stop()
        await self.app.shutdown()
