"""Read upcoming Calendar events. Returns a short text block ready to drop
into the model context. All Google sources share the same OAuth token."""

from __future__ import annotations
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytz

_SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]


def _load_creds():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow

    token_path = Path(os.environ.get("GOOGLE_TOKEN_PATH", "./.google_token.json"))
    client_secret = Path(
        os.environ.get("GOOGLE_CLIENT_SECRET_PATH", "./client_secret.json")
    )

    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), _SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not client_secret.exists():
                raise RuntimeError(
                    f"Google OAuth: {client_secret} not found. "
                    "Download from console.cloud.google.com and place it here, "
                    "or set google_calendar.enabled / google_drive.enabled to false."
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                str(client_secret), _SCOPES
            )
            creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json())

    return creds


def fetch_calendar_block(lookahead_days: int = 2, tz_name: str = "Asia/Seoul") -> str:
    from googleapiclient.discovery import build

    creds = _load_creds()
    service = build("calendar", "v3", credentials=creds, cache_discovery=False)

    tz = pytz.timezone(tz_name)
    now = datetime.now(timezone.utc)
    end = now + timedelta(days=lookahead_days)

    events_result = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=now.isoformat(),
            timeMax=end.isoformat(),
            singleEvents=True,
            orderBy="startTime",
            maxResults=20,
        )
        .execute()
    )

    events = events_result.get("items", [])
    if not events:
        return "## 캘린더 (앞으로 2일)\n예정된 일정 없음."

    lines = ["## 캘린더 (앞으로 2일)"]
    for e in events:
        start = e["start"].get("dateTime") or e["start"].get("date")
        # parse and localize
        try:
            if "T" in start:
                dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
                local = dt.astimezone(tz)
                stamp = local.strftime("%m/%d %H:%M")
            else:
                stamp = f"{start} (종일)"
        except Exception:
            stamp = start

        summary = e.get("summary", "(제목 없음)")
        location = e.get("location", "")
        loc = f" @ {location}" if location else ""
        lines.append(f"- {stamp} — {summary}{loc}")

    return "\n".join(lines)
