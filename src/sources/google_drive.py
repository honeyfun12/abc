"""Pull recently-modified Drive docs as context excerpts."""

from __future__ import annotations
from datetime import datetime, timedelta, timezone

from .google_calendar import _load_creds  # share OAuth flow


def fetch_drive_block(folder_ids: list[str], lookback_days: int = 7) -> str:
    if not folder_ids:
        return ""

    from googleapiclient.discovery import build

    creds = _load_creds()
    service = build("drive", "v3", credentials=creds, cache_discovery=False)

    since = (datetime.now(timezone.utc) - timedelta(days=lookback_days)).isoformat()
    lines = ["## 구글 드라이브 (최근 편집)"]

    for fid in folder_ids:
        q = f"'{fid}' in parents and modifiedTime > '{since}' and trashed = false"
        try:
            resp = (
                service.files()
                .list(
                    q=q,
                    fields="files(id,name,mimeType,modifiedTime)",
                    pageSize=15,
                    orderBy="modifiedTime desc",
                )
                .execute()
            )
        except Exception as e:
            lines.append(f"- (드라이브 조회 실패: {e})")
            continue

        files = resp.get("files", [])
        for f in files:
            mt = f.get("modifiedTime", "")[:10]
            lines.append(f"- [{mt}] {f['name']}")

            # For Google Docs/Sheets/text, pull a small excerpt
            if f["mimeType"] == "application/vnd.google-apps.document":
                try:
                    txt = (
                        service.files()
                        .export(fileId=f["id"], mimeType="text/plain")
                        .execute()
                        .decode("utf-8", errors="ignore")
                    )
                    excerpt = txt.strip().replace("\n", " ")[:300]
                    if excerpt:
                        lines.append(f"  · {excerpt}{'…' if len(txt) > 300 else ''}")
                except Exception:
                    pass

    return "\n".join(lines) if len(lines) > 1 else ""
