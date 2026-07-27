"""Print the existing authorised Telegram session for a cloud secret."""

from pathlib import Path

from telethon.sessions import SQLiteSession, StringSession


BACKEND_DIR = Path(__file__).resolve().parents[1]
SESSION_PATH = BACKEND_DIR / "data" / "telegram"


def main() -> None:
    if not SESSION_PATH.with_suffix(".session").exists():
        raise SystemExit("No local Telegram session was found. Run an import locally first.")
    session = SQLiteSession(str(SESSION_PATH))
    try:
        value = StringSession.save(session)
    finally:
        session.close()
    print("Copy the following value directly into Railway as TELEGRAM_SESSION_STRING.")
    print("Treat it like a password; never commit or share it.")
    print(value)


if __name__ == "__main__":
    main()
