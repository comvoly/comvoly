"""Local JSON API for the Comvoly owner MVP."""

from __future__ import annotations

import json
import os
import asyncio
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from community_qa import answer_question
from database import connect_database, create_schema, query as db_query, uses_postgres
from auth import (
    authentication_configured,
    create_session,
    expired_session_cookie,
    session_cookie,
    session_from_cookie,
    verify_password,
    verify_session,
)


PROJECT_DIR = Path(__file__).resolve().parents[1]
DATABASE_PATH = PROJECT_DIR / "data" / "comvoly.db"
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))
ALLOWED_ORIGIN = os.getenv("COMVOLY_WEB_ORIGIN", "http://localhost:3000")


def status_summary() -> dict[str, object]:
    summary: dict[str, object] = {
        "database_found": DATABASE_PATH.exists() or bool(os.getenv("DATABASE_URL")),
        "communities": [],
        "community_count": 0,
        "message_count": 0,
        "media_count": 0,
        "last_successful_sync": None,
    }
    if not DATABASE_PATH.exists() and not os.getenv("DATABASE_URL"):
        return summary

    with connect_database(DATABASE_PATH) as database:
        communities = database.execute(
            "SELECT title, source_type, imported_at FROM communities ORDER BY title"
        ).fetchall()
        count_row = database.execute(
            "SELECT COUNT(*) AS message_count, COALESCE(SUM(has_media), 0) AS media_count FROM messages"
        ).fetchone()
        message_count = count_row["message_count"] if uses_postgres() else count_row[0]
        media_count = count_row["media_count"] if uses_postgres() else count_row[1]
        if uses_postgres():
            tables = {row["name"] for row in database.execute("SELECT tablename AS name FROM pg_tables WHERE schemaname='public'")}
        else:
            tables = {row[0] for row in database.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        last_sync = None
        if "sync_runs" in tables:
            sync_row = database.execute(
                "SELECT MAX(finished_at) AS last_sync FROM sync_runs WHERE status = 'success'"
            ).fetchone()
            last_sync = sync_row["last_sync"] if uses_postgres() else sync_row[0]

    summary.update(
        communities=[dict(row) for row in communities],
        community_count=len(communities),
        message_count=message_count,
        media_count=media_count,
        last_successful_sync=last_sync,
    )
    return summary


def search_messages(query: str) -> list[dict[str, object]]:
    if not DATABASE_PATH.exists() and not os.getenv("DATABASE_URL"):
        return []

    with connect_database(DATABASE_PATH) as database:
        rows = database.execute(
            db_query("""
            SELECT messages.id, messages.telegram_message_id, messages.sent_at,
                   COALESCE(messages.sender_telegram_id, 'Unknown member') AS sender,
                   COALESCE(messages.text, '[Media attachment]') AS text,
                   communities.title AS community_title
            FROM messages
            JOIN communities ON communities.id = messages.community_id
            WHERE LOWER(COALESCE(messages.text, '')) LIKE LOWER(?)
            ORDER BY messages.sent_at DESC
            LIMIT 50
            """),
            (f"%{query}%",),
        ).fetchall()
    return [dict(row) for row in rows]


def get_message(message_id: int) -> dict[str, object] | None:
    if not DATABASE_PATH.exists() and not os.getenv("DATABASE_URL"):
        return None
    with connect_database(DATABASE_PATH) as database:
        row = database.execute(
            db_query("""SELECT messages.id, messages.telegram_message_id, messages.sent_at,
                      COALESCE(messages.sender_telegram_id, 'Unknown member') AS sender,
                      COALESCE(messages.text, '[Media attachment]') AS text,
                      communities.title AS community_title
               FROM messages JOIN communities ON communities.id = messages.community_id
               WHERE messages.id = ?"""),
            (message_id,),
        ).fetchone()
    return dict(row) if row else None


class ComvolyAPIHandler(BaseHTTPRequestHandler):
    def send_json(self, status: HTTPStatus, payload: object, extra_headers: dict[str, str] | None = None) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", ALLOWED_ORIGIN)
        self.send_header("Access-Control-Allow-Credentials", "true")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Cache-Control", "no-store")
        for name, value in (extra_headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def authenticated(self) -> bool:
        return verify_session(session_from_cookie(self.headers.get("Cookie")))

    def require_authentication(self) -> bool:
        if self.authenticated():
            return True
        self.send_json(HTTPStatus.UNAUTHORIZED, {"detail": "Sign in to access this community archive."})
        return False

    def read_json(self) -> dict[str, object]:
        length = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(length) or b"{}")

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_json(HTTPStatus.NO_CONTENT, {})

    def do_GET(self) -> None:  # noqa: N802
        request = urlparse(self.path)
        if request.path == "/health":
            self.send_json(HTTPStatus.OK, {"status": "ok", "authentication_configured": authentication_configured()})
            return
        if request.path == "/auth/session":
            self.send_json(HTTPStatus.OK, {"authenticated": self.authenticated(), "setup_required": not authentication_configured()})
            return
        if not self.require_authentication():
            return
        if request.path == "/status":
            self.send_json(HTTPStatus.OK, status_summary())
            return
        if request.path.startswith("/messages/"):
            try:
                message_id = int(request.path.rsplit("/", 1)[1])
            except ValueError:
                self.send_json(HTTPStatus.BAD_REQUEST, {"detail": "Invalid message ID."})
                return
            message = get_message(message_id)
            self.send_json(HTTPStatus.OK, message) if message else self.send_json(
                HTTPStatus.NOT_FOUND, {"detail": "Message not found."}
            )
            return
        if request.path == "/search":
            query = parse_qs(request.query).get("q", [""])[0].strip()
            if not query:
                self.send_json(HTTPStatus.BAD_REQUEST, {"detail": "A search query is required."})
                return
            self.send_json(HTTPStatus.OK, {"query": query, "results": search_messages(query)})
            return
        self.send_json(HTTPStatus.NOT_FOUND, {"detail": "Not found."})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/auth/login":
            self.login()
            return
        if path == "/auth/logout":
            self.send_json(HTTPStatus.OK, {"authenticated": False}, {"Set-Cookie": expired_session_cookie(self.secure_cookies())})
            return
        if path != "/ask":
            self.send_json(HTTPStatus.NOT_FOUND, {"detail": "Not found."})
            return
        if not self.require_authentication():
            return
        try:
            payload = self.read_json()
            question = str(payload.get("question", "")).strip()
            if not question:
                self.send_json(HTTPStatus.BAD_REQUEST, {"detail": "A question is required."})
                return
            if len(question) > 1000:
                self.send_json(HTTPStatus.BAD_REQUEST, {"detail": "The question is too long."})
                return
            answer = answer_question(question)
            self.send_json(
                HTTPStatus.OK,
                {
                    "question": question,
                    "answer": answer.text,
                    "evidence_count": answer.evidence_count,
                    "citations": [
                        {
                            "id": item.id,
                            "community_title": item.community,
                            "sent_at": item.sent_at,
                            "sender": item.sender,
                            "text": item.text,
                        }
                        for item in answer.citations
                    ],
                },
            )
        except (json.JSONDecodeError, UnicodeDecodeError):
            self.send_json(HTTPStatus.BAD_REQUEST, {"detail": "Invalid JSON request."})
        except Exception as error:
            self.send_json(HTTPStatus.SERVICE_UNAVAILABLE, {"detail": str(error)})

    def secure_cookies(self) -> bool:
        return os.getenv("COMVOLY_SECURE_COOKIES", "false").lower() == "true"

    def login(self) -> None:
        try:
            if not authentication_configured():
                self.send_json(HTTPStatus.SERVICE_UNAVAILABLE, {"detail": "Owner sign-in has not been configured yet.", "setup_required": True})
                return
            payload = self.read_json()
            password = str(payload.get("password", ""))
            if not verify_password(password):
                self.send_json(HTTPStatus.UNAUTHORIZED, {"detail": "The owner password was not accepted."})
                return
            token = create_session()
            self.send_json(HTTPStatus.OK, {"authenticated": True}, {"Set-Cookie": session_cookie(token, self.secure_cookies())})
        except (json.JSONDecodeError, UnicodeDecodeError):
            self.send_json(HTTPStatus.BAD_REQUEST, {"detail": "Invalid JSON request."})

    def log_message(self, format: str, *args: object) -> None:
        print(f"Comvoly API - {format % args}")


def main() -> None:
    with connect_database(DATABASE_PATH) as database:
        create_schema(database)
        database.execute("SELECT 1").fetchone()
    print("Database connection and schema verified.")

    if os.getenv("COMVOLY_RUN_SYNC", "false").lower() == "true":
        from telegram_import import watch_for_messages

        interval = int(os.getenv("COMVOLY_SYNC_INTERVAL", "120"))
        threading.Thread(
            target=lambda: asyncio.run(watch_for_messages(interval, 100)),
            name="comvoly-telegram-sync",
            daemon=True,
        ).start()
        print(f"Telegram sync enabled every {interval} seconds.")
    server = ThreadingHTTPServer((HOST, PORT), ComvolyAPIHandler)
    print(f"Comvoly API running at http://{HOST}:{PORT}")
    print("Press Ctrl+C to stop it.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nComvoly API stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
