"""Import one authorised Telegram community into a local SQLite database."""

from __future__ import annotations

import argparse
import asyncio
import os
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.sessions import StringSession
from database import connect_database, create_schema, inserted_id, query, uses_postgres


PROJECT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_DIR / ".env")


def require_setting(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} is missing. Add it to backend/.env before importing.")
    return value


def utc_iso(value: datetime | None = None) -> str:
    return (value or datetime.now(UTC)).astimezone(UTC).isoformat()


async def import_messages(limit: int | None, full_history: bool = False) -> int:
    api_id = int(require_setting("TELEGRAM_API_ID"))
    api_hash = require_setting("TELEGRAM_API_HASH")
    phone = require_setting("TELEGRAM_PHONE")
    group_reference = require_setting("TELEGRAM_GROUP")
    database_path = PROJECT_DIR / os.getenv("DATABASE_PATH", "data/comvoly.db")
    session_path = PROJECT_DIR / "data" / "telegram"
    session = StringSession(os.environ["TELEGRAM_SESSION_STRING"]) if os.getenv("TELEGRAM_SESSION_STRING") else str(session_path)
    with connect_database(database_path) as database:
        create_schema(database)
        client = TelegramClient(session, api_id, api_hash)
        await client.start(phone=phone)
        run_id: int | None = None
        title = str(group_reference)
        try:
            community = await client.get_entity(group_reference)
            title = getattr(community, "title", None) or str(group_reference)
            imported_at = utc_iso()
            database.execute(
                query("""INSERT INTO communities (telegram_id, title, source_type, imported_at)
                VALUES (?, ?, ?, ?) ON CONFLICT(telegram_id) DO UPDATE SET
                title=excluded.title, source_type=excluded.source_type, imported_at=excluded.imported_at"""),
                (str(community.id), title, community.__class__.__name__, imported_at),
            )
            community_row = database.execute(
                query("SELECT id FROM communities WHERE telegram_id = ?"), (str(community.id),)
            ).fetchone()
            community_id = community_row["id"] if uses_postgres() else community_row[0]
            mode = "full history" if full_history else "new messages"
            run_sql = "INSERT INTO sync_runs (community_id, started_at, status, mode) VALUES (?, ?, 'running', ?)"
            if uses_postgres():
                run_sql += " RETURNING id"
            run_id = inserted_id(database.execute(query(run_sql), (community_id, utc_iso(), mode)))
            latest_row = None if full_history else database.execute(
                query("SELECT COALESCE(MAX(telegram_message_id), 0) AS latest_id FROM messages WHERE community_id = ?"), (community_id,)
            ).fetchone()
            latest_id = 0 if full_history else (latest_row["latest_id"] if uses_postgres() else latest_row[0])
            imported = 0
            async for message in client.iter_messages(community, reverse=True, min_id=latest_id, limit=limit):
                database.execute(
                    query("""INSERT INTO messages (community_id, telegram_message_id, sender_telegram_id, sent_at,
                    edited_at, text, reply_to_telegram_message_id, has_media, imported_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(community_id, telegram_message_id) DO UPDATE SET
                    sender_telegram_id=excluded.sender_telegram_id, sent_at=excluded.sent_at,
                    edited_at=excluded.edited_at, text=excluded.text,
                    reply_to_telegram_message_id=excluded.reply_to_telegram_message_id,
                    has_media=excluded.has_media, imported_at=excluded.imported_at"""),
                    (community_id, message.id, str(message.sender_id) if message.sender_id else None,
                     utc_iso(message.date), utc_iso(message.edit_date) if message.edit_date else None,
                     message.message, message.reply_to_msg_id, int(message.media is not None), imported_at),
                )
                imported += 1
            database.execute(
                query("UPDATE sync_runs SET finished_at=?, status='success', imported_count=? WHERE id=?"),
                (utc_iso(), imported, run_id),
            )
            database.commit()
        except Exception as error:
            if run_id is not None:
                database.execute(query("UPDATE sync_runs SET finished_at=?, status='failed', error=? WHERE id=?"), (utc_iso(), str(error), run_id))
                database.commit()
            raise
        finally:
            await client.disconnect()
    target = "configured PostgreSQL database" if uses_postgres() else str(database_path)
    print(f"Imported {imported} {mode} from {title} into {target}.")
    return imported


async def watch_for_messages(interval_seconds: int, limit: int | None) -> None:
    print(f"Comvoly sync agent started. Checking for new messages every {interval_seconds} seconds.")
    print("Press Ctrl+C to stop it.")
    while True:
        try:
            await import_messages(limit)
        except Exception as error:
            print(f"Sync check failed: {error}")
        await asyncio.sleep(interval_seconds)


def main() -> None:
    parser = argparse.ArgumentParser(description="Import one authorised Telegram community.")
    parser.add_argument("--limit", type=int, default=100, help="Maximum messages per run. Use 0 for no limit.")
    parser.add_argument("--full", action="store_true", help="Import all history, not only newer messages.")
    parser.add_argument("--watch", action="store_true", help="Keep running and sync at a regular interval.")
    parser.add_argument("--interval", type=int, default=120, help="Seconds between sync checks (default: 120).")
    args = parser.parse_args()
    if args.interval < 30:
        parser.error("--interval must be at least 30 seconds.")
    limit = None if args.limit == 0 else args.limit
    if args.watch:
        asyncio.run(watch_for_messages(args.interval, limit))
    else:
        asyncio.run(import_messages(limit, args.full))


if __name__ == "__main__":
    main()
