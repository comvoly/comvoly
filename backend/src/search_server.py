"""A dependency-free local HTTP API for searching imported Comvoly messages.

This is deliberately tiny: it gives the web prototype a real data source before
we introduce a full production backend.
"""

from __future__ import annotations

import json
import sqlite3
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


PROJECT_DIR = Path(__file__).resolve().parents[1]
DATABASE_PATH = PROJECT_DIR / "data" / "comvoly.db"
HOST = "127.0.0.1"
PORT = 8000


def search_messages(query: str) -> list[dict[str, object]]:
    if not DATABASE_PATH.exists():
        return []

    with sqlite3.connect(DATABASE_PATH) as database:
        database.row_factory = sqlite3.Row
        rows = database.execute(
            """
            SELECT messages.telegram_message_id, messages.sent_at,
                   COALESCE(messages.text, '[media]') AS text,
                   communities.title AS community_title
            FROM messages
            JOIN communities ON communities.id = messages.community_id
            WHERE messages.text LIKE ? COLLATE NOCASE
            ORDER BY messages.sent_at DESC
            LIMIT 50
            """,
            (f"%{query}%",),
        ).fetchall()

    return [dict(row) for row in rows]


class ComvolySearchHandler(BaseHTTPRequestHandler):
    def send_json(self, status: HTTPStatus, payload: object) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "http://localhost:3000")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        request = urlparse(self.path)
        if request.path == "/health":
            self.send_json(HTTPStatus.OK, {"status": "ok", "database_found": DATABASE_PATH.exists()})
            return

        if request.path != "/search":
            self.send_json(HTTPStatus.NOT_FOUND, {"detail": "Not found"})
            return

        query = parse_qs(request.query).get("q", [""])[0].strip()
        if not query:
            self.send_json(HTTPStatus.BAD_REQUEST, {"detail": "A search query is required."})
            return

        self.send_json(HTTPStatus.OK, {"query": query, "results": search_messages(query)})

    def log_message(self, format: str, *args: object) -> None:
        print(f"Comvoly search API — {format % args}")


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), ComvolySearchHandler)
    print(f"Comvoly search API running at http://{HOST}:{PORT}")
    print("Press Ctrl+C to stop it.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nComvoly search API stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
