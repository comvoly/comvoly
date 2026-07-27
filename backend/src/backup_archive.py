"""Create a safe local copy of the Comvoly archive database."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
SOURCE_DATABASE = BACKEND_DIR / "data" / "comvoly.db"
BACKUP_DIRECTORY = BACKEND_DIR / "backups"


def main() -> None:
    if not SOURCE_DATABASE.exists():
        raise SystemExit("No Comvoly archive exists yet. Import a community before creating a backup.")
    BACKUP_DIRECTORY.mkdir(exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y-%m-%d_%H-%M-%S_UTC")
    destination = BACKUP_DIRECTORY / f"comvoly_archive_{stamp}.db"
    with sqlite3.connect(SOURCE_DATABASE) as source, sqlite3.connect(destination) as backup:
        source.backup(backup)
    print("Comvoly archive backup created:")
    print(destination)
    print("This contains archive data only. Telegram credentials are not included.")


if __name__ == "__main__":
    main()
