"""SQLite-backed memory. Keeps every Telegram message (in/out), Claude's
internal notes, and a tiny to-do log Claude writes to itself."""

from __future__ import annotations
import sqlite3
import json
import threading
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Iterator


_SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    direction TEXT NOT NULL,   -- 'in' (user → bot) | 'out' (bot → user)
    kind TEXT,                 -- morning_brief, reply, etc.
    text TEXT NOT NULL,
    voice_path TEXT,
    meta TEXT                  -- json blob
);

CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    note TEXT NOT NULL,
    consumed INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS todos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts_created TEXT NOT NULL,
    ts_due TEXT,
    text TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open'  -- open | done | dropped
);

CREATE INDEX IF NOT EXISTS idx_messages_ts ON messages(ts);
CREATE INDEX IF NOT EXISTS idx_notes_ts ON notes(ts);
"""


class Memory:
    def __init__(self, db_path: str | Path = "./assistant.db"):
        self.path = Path(db_path)
        self._lock = threading.Lock()
        with self._conn() as c:
            c.executescript(_SCHEMA)

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        with self._lock:
            conn = sqlite3.connect(self.path, isolation_level=None)
            conn.row_factory = sqlite3.Row
            try:
                yield conn
            finally:
                conn.close()

    # ---- messages ----

    def log_message(
        self,
        *,
        direction: str,
        text: str,
        kind: str | None = None,
        voice_path: str | None = None,
        meta: dict | None = None,
    ) -> None:
        with self._conn() as c:
            c.execute(
                "INSERT INTO messages (ts, direction, kind, text, voice_path, meta) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    datetime.now(timezone.utc).isoformat(),
                    direction,
                    kind,
                    text,
                    voice_path,
                    json.dumps(meta, ensure_ascii=False) if meta else None,
                ),
            )

    def recent_messages(self, limit: int = 20) -> list[dict]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT ts, direction, kind, text FROM messages "
                "ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in reversed(rows)]

    # ---- notes (Claude → Claude) ----

    def add_note(self, note: str) -> None:
        if not note.strip():
            return
        with self._conn() as c:
            c.execute(
                "INSERT INTO notes (ts, note) VALUES (?, ?)",
                (datetime.now(timezone.utc).isoformat(), note.strip()),
            )

    def unconsumed_notes(self, max_age_hours: int = 72) -> list[str]:
        cutoff = (
            datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        ).isoformat()
        with self._conn() as c:
            rows = c.execute(
                "SELECT id, ts, note FROM notes "
                "WHERE consumed = 0 AND ts >= ? ORDER BY id ASC",
                (cutoff,),
            ).fetchall()
        return [f"[{r['ts'][:16]}] {r['note']}" for r in rows]

    def consume_notes_older_than(self, hours: int = 72) -> None:
        cutoff = (
            datetime.now(timezone.utc) - timedelta(hours=hours)
        ).isoformat()
        with self._conn() as c:
            c.execute(
                "UPDATE notes SET consumed = 1 WHERE ts < ?", (cutoff,)
            )

    # ---- todos ----

    def add_todo(self, text: str, due: datetime | None = None) -> int:
        with self._conn() as c:
            cur = c.execute(
                "INSERT INTO todos (ts_created, ts_due, text) VALUES (?, ?, ?)",
                (
                    datetime.now(timezone.utc).isoformat(),
                    due.isoformat() if due else None,
                    text.strip(),
                ),
            )
            return cur.lastrowid

    def open_todos(self) -> list[dict]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT id, ts_created, ts_due, text FROM todos "
                "WHERE status = 'open' ORDER BY id DESC LIMIT 20"
            ).fetchall()
        return [dict(r) for r in rows]
