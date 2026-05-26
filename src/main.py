"""Entry point. Wires Memory → Assistant → Bot → Scheduler and runs until
SIGINT/SIGTERM. Run with: python -m src.main"""

from __future__ import annotations
import asyncio
import logging
import os
import signal
from pathlib import Path

import yaml
from dotenv import load_dotenv

from .memory import Memory
from .assistant import Assistant
from .tts import TTS
from .telegram_bot import Bot
from .scheduler import Scheduler


def _load_config() -> dict:
    load_dotenv()
    cfg_path = Path(os.environ.get("ASSISTANT_CONFIG", "./config.yaml"))
    with open(cfg_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    )
    # Quiet down noisy libs
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.WARNING)


async def _amain() -> None:
    _setup_logging()
    cfg = _load_config()
    log = logging.getLogger("main")

    # Required env vars (fail loud, fail early)
    for var in ("ANTHROPIC_API_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"):
        if not os.environ.get(var):
            raise SystemExit(f"Missing required env var: {var}. See .env.example.")

    memory = Memory("./assistant.db")
    assistant = Assistant(cfg, memory)
    tts = TTS(cfg["tts"])
    bot = Bot(cfg, assistant, memory, tts)
    scheduler = Scheduler(cfg, bot, tz_name=os.environ.get("TIMEZONE", "Asia/Seoul"))

    await bot.start()
    scheduler.start()

    log.info("Assistant running. Send /start to the bot to verify.")

    stop = asyncio.Event()

    def _shutdown(*_):
        stop.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _shutdown)
        except NotImplementedError:
            pass  # Windows

    try:
        await stop.wait()
    finally:
        log.info("Shutting down…")
        scheduler.scheduler.shutdown(wait=False)
        await bot.stop()
        # Consume old internal notes so they don't accumulate forever
        memory.consume_notes_older_than(hours=72)


def main() -> None:
    asyncio.run(_amain())


if __name__ == "__main__":
    main()
