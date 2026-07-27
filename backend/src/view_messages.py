"""Print messages imported by the local Comvoly Telegram proof of concept."""

from __future__ import annotations

import sqlite3
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
DATABASE_PATH = PROJECT_DIR / "data" / "comvoly.db"


def main() -> None:
    if not DATABASE_PATH.exists():
        raise SystemExit(
            "No local Comvoly database was found. Run telegram_import.py before viewing messages."
        )

    with sqlite3.connect(DATABASE_PATH) as database:
        rows = database.execute(
            """
            SELECT sent_at, COALESCE(text, '[media]')
            FROM messages
            ORDER BY sent_at
            """
        ).fetchall()

    if not rows:
        print("Comvoly found the database, but it contains no messages yet.")
        return

    print(f"Comvoly has imported {len(rows)} message(s):\n")
    for sent_at, text in rows:
        print(f"{sent_at}  {text}")


if __name__ == "__main__":
    main()
