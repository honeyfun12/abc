"""Text → ogg/opus voice for Telegram sendVoice.

OpenAI's gpt-4o-mini-tts handles Korean smoothly. Returns a path to a
temp .ogg file; caller is responsible for cleanup."""

from __future__ import annotations
import logging
import os
import subprocess
import tempfile
from pathlib import Path

log = logging.getLogger(__name__)


class TTS:
    def __init__(self, cfg: dict):
        self.enabled = bool(cfg.get("enabled", False)) and bool(
            os.environ.get("OPENAI_API_KEY")
        )
        self.voice = cfg.get("voice", "nova")
        self.model = cfg.get("model", "gpt-4o-mini-tts")
        self.min_chars = cfg.get("min_chars_for_voice", 80)
        self._client = None
        if self.enabled:
            try:
                from openai import OpenAI

                self._client = OpenAI()
            except Exception as e:
                log.warning("OpenAI TTS init failed, disabling voice: %s", e)
                self.enabled = False

    def should_voice(self, text: str, voice_friendly_hint: bool) -> bool:
        if not self.enabled:
            return False
        if not voice_friendly_hint:
            return False
        return len(text.strip()) >= self.min_chars

    def synth(self, text: str) -> Path | None:
        """Synthesize Korean speech to a Telegram-friendly ogg/opus file.
        Returns None on failure (caller falls back to text-only)."""
        if not self.enabled or not self._client:
            return None

        try:
            mp3_path = Path(tempfile.mkstemp(suffix=".mp3")[1])
            with self._client.audio.speech.with_streaming_response.create(
                model=self.model,
                voice=self.voice,
                input=text,
                instructions=(
                    "Speak in warm, calm, natural Korean. Slightly slower than "
                    "normal. Like a thoughtful executive assistant — caring but "
                    "not saccharine. Pause briefly between sentences."
                ),
            ) as response:
                response.stream_to_file(str(mp3_path))

            ogg_path = mp3_path.with_suffix(".ogg")
            # Telegram voice notes need opus in an ogg container.
            try:
                subprocess.run(
                    [
                        "ffmpeg",
                        "-y",
                        "-i",
                        str(mp3_path),
                        "-c:a",
                        "libopus",
                        "-b:a",
                        "48k",
                        "-vn",
                        str(ogg_path),
                    ],
                    check=True,
                    capture_output=True,
                )
                mp3_path.unlink(missing_ok=True)
                return ogg_path
            except FileNotFoundError:
                log.warning(
                    "ffmpeg not found; sending mp3 as audio (not as voice note)."
                )
                return mp3_path
            except subprocess.CalledProcessError as e:
                log.warning("ffmpeg failed: %s", e.stderr.decode("utf-8", "ignore"))
                mp3_path.unlink(missing_ok=True)
                return None
        except Exception as e:
            log.warning("TTS synth failed: %s", e)
            return None
