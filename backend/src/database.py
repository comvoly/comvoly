"""Shared SQLite/PostgreSQL database access for Comvoly."""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


def uses_postgres() -> bool:
    return os.getenv("DATABASE_URL", "").startswith(("postgres://", "postgresql://"))


@contextmanager
def connect_database(sqlite_path: Path) -> Iterator[Any]:
    if uses_postgres():
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as error:
            raise RuntimeError("PostgreSQL support requires psycopg. Install backend requirements.") from error
        with psycopg.connect(os.environ["DATABASE_URL"], row_factory=dict_row) as connection:
            yield connection
        return

    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(sqlite_path)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def query(sql: str) -> str:
    return sql.replace("?", "%s") if uses_postgres() else sql


def create_schema(connection: Any) -> None:
    identity = "BIGSERIAL PRIMARY KEY" if uses_postgres() else "INTEGER PRIMARY KEY"
    statements = [
        f"""CREATE TABLE IF NOT EXISTS communities (
            id {identity}, telegram_id TEXT NOT NULL UNIQUE, title TEXT NOT NULL,
            source_type TEXT NOT NULL, imported_at TEXT NOT NULL)""",
        f"""CREATE TABLE IF NOT EXISTS messages (
            id {identity}, community_id BIGINT NOT NULL REFERENCES communities(id),
            telegram_message_id BIGINT NOT NULL, sender_telegram_id TEXT, sent_at TEXT NOT NULL,
            edited_at TEXT, text TEXT, reply_to_telegram_message_id BIGINT,
            has_media INTEGER NOT NULL DEFAULT 0, imported_at TEXT NOT NULL,
            UNIQUE(community_id, telegram_message_id))""",
        "CREATE INDEX IF NOT EXISTS messages_community_sent_at ON messages(community_id, sent_at)",
        f"""CREATE TABLE IF NOT EXISTS sync_runs (
            id {identity}, community_id BIGINT REFERENCES communities(id), started_at TEXT NOT NULL,
            finished_at TEXT, status TEXT NOT NULL, mode TEXT NOT NULL,
            imported_count INTEGER NOT NULL DEFAULT 0, error TEXT)""",
        "CREATE INDEX IF NOT EXISTS sync_runs_community_started_at ON sync_runs(community_id, started_at DESC)",
    ]
    if not uses_postgres():
        connection.execute("PRAGMA foreign_keys = ON")
    for statement in statements:
        connection.execute(statement)


def inserted_id(cursor: Any) -> int:
    if uses_postgres():
        return int(cursor.fetchone()["id"])
    return int(cursor.lastrowid)
