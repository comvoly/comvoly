"""A lightweight, single-process local Comvoly search page.

Run with: py backend/src/lite_app.py
Then visit: http://127.0.0.1:8000
"""

from __future__ import annotations

import html
import sqlite3
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


PROJECT_DIR = Path(__file__).resolve().parents[1]
DATABASE_PATH = PROJECT_DIR / "data" / "comvoly.db"
HOST = "127.0.0.1"
PORT = 8000


def search_messages(query: str) -> list[sqlite3.Row]:
    if not DATABASE_PATH.exists() or not query:
        return []

    with sqlite3.connect(DATABASE_PATH) as database:
        database.row_factory = sqlite3.Row
        return database.execute(
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


def archive_stats() -> tuple[int, str | None]:
    if not DATABASE_PATH.exists():
        return 0, None

    with sqlite3.connect(DATABASE_PATH) as database:
        message_count, last_sync = database.execute(
            "SELECT COUNT(*), MAX(imported_at) FROM messages"
        ).fetchone()
    return message_count, last_sync


def display_date(value: str) -> str:
    try:
        return datetime.fromisoformat(value).strftime("%d %b %Y, %H:%M")
    except ValueError:
        return value


def render_page(query: str, results: list[sqlite3.Row]) -> str:
    escaped_query = html.escape(query)
    message_count, last_sync = archive_stats()
    last_sync_label = display_date(last_sync) if last_sync else "Not synced yet"
    if query:
        if results:
            result_html = "".join(
                f"""
                <article class=\"result\">
                  <div class=\"metadata\">
                    <strong>{html.escape(row['community_title'])}</strong>
                    <span>{html.escape(display_date(row['sent_at']))}</span>
                    <span>Message #{row['telegram_message_id']}</span>
                  </div>
                  <p>{html.escape(row['text'])}</p>
                </article>
                """
                for row in results
            )
        else:
            result_html = "<div class=\"empty\">No imported messages contain that phrase yet. Try another word.</div>"

        results_section = f"""
          <section class=\"results\">
            <div class=\"results-heading\">
              <h2>Results for “{escaped_query}”</h2>
              <span>{len(results)} found</span>
            </div>
            {result_html}
          </section>
        """
    else:
        results_section = ""

    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>Comvoly — Local Search</title>
  <style>
    :root {{ color-scheme: dark; }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; min-height: 100vh; color: #f8fafc; background: radial-gradient(circle at 80% 10%, #173e7e 0, transparent 31%), #07152d; font-family: Arial, sans-serif; }}
    main {{ max-width: 920px; margin: 0 auto; padding: 28px 24px 72px; }}
    header {{ display: flex; align-items: center; gap: 12px; font-size: 20px; font-weight: 700; }}
    .mark {{ display: grid; place-items: center; width: 40px; height: 40px; border-radius: 12px; color: #07152d; background: #f7c843; font-weight: 900; }}
    .tag {{ margin-left: auto; padding: 6px 10px; border: 1px solid #7dd3a833; border-radius: 999px; color: #a7f3d0; background: #6ee7b715; font-size: 12px; }}
    .hero {{ padding: 86px 0 42px; }}
    .eyebrow {{ color: #f7c843; font-size: 12px; font-weight: 700; letter-spacing: .2em; text-transform: uppercase; }}
    h1 {{ max-width: 740px; margin: 16px 0; font-size: clamp(38px, 6vw, 60px); line-height: 1.05; letter-spacing: -.04em; }}
    .intro {{ max-width: 680px; color: #cbd5e1; font-size: 18px; line-height: 1.65; }}
    form {{ display: flex; gap: 8px; margin-top: 34px; padding: 8px; border: 1px solid #ffffff1f; border-radius: 16px; background: #02081799; }}
    input {{ min-width: 0; flex: 1; border: 0; outline: 0; padding: 13px 14px; color: white; background: transparent; font-size: 16px; }}
    button {{ border: 0; border-radius: 11px; padding: 0 20px; color: #07152d; background: #f7c843; font-weight: 700; cursor: pointer; }}
    .results {{ margin-top: 18px; }}
    .results-heading {{ display: flex; justify-content: space-between; align-items: baseline; margin: 28px 0 14px; }}
    h2 {{ margin: 0; font-size: 20px; }}
    .results-heading span, .metadata {{ color: #94a3b8; font-size: 13px; }}
    .result, .empty {{ margin-top: 12px; padding: 20px; border: 1px solid #ffffff1a; border-radius: 16px; background: #ffffff0c; }}
    .metadata {{ display: flex; flex-wrap: wrap; gap: 8px 14px; }}
    .metadata strong {{ color: #f7c843; }}
    .result p {{ margin: 14px 0 0; line-height: 1.6; white-space: pre-wrap; }}
    .stats {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; max-width: 520px; margin-top: 18px; }}
    .stat {{ padding: 13px 15px; border: 1px solid #ffffff16; border-radius: 12px; background: #ffffff08; }}
    .stat-label {{ display: block; color: #94a3b8; font-size: 12px; }}
    .stat-value {{ display: block; margin-top: 4px; font-weight: 700; }}
    @media (max-width: 600px) {{ .hero {{ padding-top: 56px; }} form {{ flex-direction: column; }} button {{ padding: 13px; }} }}
  </style>
</head>
<body>
  <main>
    <header><span class=\"mark\">K</span> Comvoly <span class=\"tag\">Local prototype</span></header>
    <section class=\"hero\">
      <div class=\"eyebrow\">Community intelligence</div>
      <h1>Find the knowledge buried in your community.</h1>
      <p class=\"intro\">Search the Telegram messages you have imported into Comvoly. This local prototype stays on your computer.</p>
      <form method=\"get\">
        <input name=\"q\" value=\"{escaped_query}\" placeholder=\"Search your imported messages…\" autofocus>
        <button type=\"submit\">Search</button>
      </form>
      <div class=\"stats\">
        <div class=\"stat\"><span class=\"stat-label\">Messages stored</span><span class=\"stat-value\">{message_count}</span></div>
        <div class=\"stat\"><span class=\"stat-label\">Last sync</span><span class=\"stat-value\">{html.escape(last_sync_label)}</span></div>
      </div>
    </section>
    {results_section}
  </main>
</body>
</html>"""


class ComvolyHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        request = urlparse(self.path)
        if request.path != "/":
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return

        query = parse_qs(request.query).get("q", [""])[0].strip()
        page = render_page(query, search_messages(query)).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(page)))
        self.end_headers()
        self.wfile.write(page)

    def log_message(self, format: str, *args: object) -> None:
        print(f"Comvoly — {format % args}")


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), ComvolyHandler)
    print(f"Comvoly is running at http://{HOST}:{PORT}")
    print("Press Ctrl+C to stop it.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nComvoly stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
