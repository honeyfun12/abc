"""A plain folder of text/markdown files. Treat it like a personal journal —
write whatever you want into it (drag drop from Bear, Obsidian, etc.).

Claude reads the most recently modified ones for context. This also serves
as the "previous Claude chats" source: just dump exported transcripts here."""

from __future__ import annotations
from pathlib import Path
from datetime import datetime


def fetch_notes_block(
    path: str, max_files: int = 5, max_chars_per_file: int = 800
) -> str:
    folder = Path(path)
    if not folder.exists():
        folder.mkdir(parents=True, exist_ok=True)
        return ""

    candidates = []
    for p in folder.rglob("*"):
        if p.is_file() and p.suffix.lower() in {".md", ".txt"}:
            candidates.append((p.stat().st_mtime, p))

    if not candidates:
        return ""

    candidates.sort(reverse=True)
    lines = ["## 개인 노트 (최근 편집)"]

    for mtime, p in candidates[:max_files]:
        try:
            text = p.read_text(encoding="utf-8", errors="ignore").strip()
        except Exception:
            continue
        if not text:
            continue
        when = datetime.fromtimestamp(mtime).strftime("%m/%d %H:%M")
        excerpt = text[:max_chars_per_file]
        suffix = "…" if len(text) > max_chars_per_file else ""
        lines.append(f"\n### [{when}] {p.name}\n{excerpt}{suffix}")

    return "\n".join(lines)
