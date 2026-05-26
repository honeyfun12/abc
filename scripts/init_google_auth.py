"""One-time helper: opens a browser to authorize Calendar+Drive read access,
saves the token. Run after enabling sources.google_calendar / google_drive."""

from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from src.sources.google_calendar import _load_creds  # noqa: E402


def main() -> None:
    creds = _load_creds()
    print("Google OAuth complete.")
    print(f"Token has scopes: {creds.scopes}")


if __name__ == "__main__":
    main()
