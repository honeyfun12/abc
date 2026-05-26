"""Text → ogg/opus voice for Telegram sendVoice.

Uses Microsoft Edge TTS — completely free, no API key, very natural
Korean voices. Returns a path to a temp .ogg file; caller is responsible
for cleanup."""

from __future__ import annotations
import logging
import subprocess
import tempfile
from pathlib import Path

log = logging.getLogger(__name__)


class TTS:
    def __init__(self, cfg: dict):
        self.enabled = bool(cfg.get("enabled", False))
        self.voice = cfg.get("voice", "ko-KR-SunHiNeural")
        self.rate = cfg.get("rate", "+0%")
        self.pitch = cfg.get("pitch", "+0Hz")
        self.min_chars = cfg.get("min_chars_for_voice", 80)

        if self.enabled:
            try:
                import edge_tts  # noqa: F401
            except ImportError:
                log.warning("edge_tts not installed; disabling voice.")
                self.enabled = False

    def should_voice(self, text: str, voice_friendly_hint: bool) -> bool:
        if not self.enabled:
            return False
        if not voice_friendly_hint:
            return False
        return len(text.strip()) >= self.min_chars

    async def synth(self, text: str) -> Path | None:
        """Synthesize Korean speech to a Telegram-friendly ogg/opus file.
        Returns None on failure (caller falls back to text-only)."""
        if not self.enabled:
            return None

        import edge_tts

        try:
            mp3_path = Path(tempfile.mkstemp(suffix=".mp3")[1])
            communicate = edge_tts.Communicate(
                text=text,
                voice=self.voice,
                rate=self.rate,
                pitch=self.pitch,
            )
            await communicate.save(str(mp3_path))

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
