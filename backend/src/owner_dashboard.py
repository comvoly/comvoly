"""Run with: py backend/src/owner_dashboard.py"""
from __future__ import annotations

import html
import re
import sqlite3
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from community_qa import GroundedAnswer, answer_question

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "comvoly.db"


def date(value: str | None) -> str:
    if not value:
        return "Not synced yet"
    try:
        return datetime.fromisoformat(value).strftime("%d %b %Y, %H:%M")
    except ValueError:
        return value


def data():
    if not DB.exists():
        return [], 0, 0, None, []
    with sqlite3.connect(DB) as con:
        con.row_factory = sqlite3.Row
        groups = con.execute("SELECT title, source_type, imported_at FROM communities ORDER BY title").fetchall()
        messages, media, last_message_import = con.execute(
            "SELECT COUNT(*), COALESCE(SUM(has_media), 0), MAX(imported_at) FROM messages"
        ).fetchone()
        tables = {row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "sync_runs" in tables:
            last_sync = con.execute(
                "SELECT MAX(finished_at) FROM sync_runs WHERE status = 'success'"
            ).fetchone()[0]
            syncs = con.execute("""SELECT communities.title, sync_runs.finished_at, sync_runs.status,
                sync_runs.imported_count, sync_runs.error FROM sync_runs
                LEFT JOIN communities ON communities.id = sync_runs.community_id
                ORDER BY sync_runs.id DESC LIMIT 5""").fetchall()
        else:
            last_sync = last_message_import
            syncs = []
    return groups, messages, media, last_sync, syncs


def find(query: str):
    if not query or not DB.exists():
        return []
    with sqlite3.connect(DB) as con:
        con.row_factory = sqlite3.Row
        return con.execute("""SELECT communities.title, messages.sent_at, messages.telegram_message_id,
            COALESCE(messages.text, '[media]') text FROM messages JOIN communities ON communities.id=messages.community_id
            WHERE messages.text LIKE ? COLLATE NOCASE ORDER BY messages.sent_at DESC LIMIT 50""", (f"%{query}%",)).fetchall()


def card(label, value, detail):
    return f"<div class='card'><span>{html.escape(label)}</span><strong>{html.escape(str(value))}</strong><small>{html.escape(detail)}</small></div>"


def answer_html(answer: GroundedAnswer) -> str:
    safe = html.escape(answer.text)
    safe = re.sub(r"\[M(\d+)\]", r"<a class='cite' href='#message-\1'>[M\1]</a>", safe)
    safe = safe.replace("\n\n", "</p><p>").replace("\n", "<br>")
    citations = "".join(
        f"<article id='message-{item.id}'><div><b>[M{item.id}] {html.escape(item.community)}</b> | "
        f"{html.escape(date(item.sent_at))} | Member {html.escape(item.sender)}</div>"
        f"<p>{html.escape(item.text)}</p></article>"
        for item in answer.citations
    )
    if not citations:
        citations = "<div class='notice'>No message citations were returned for this answer.</div>"
    return (
        "<section class='panel answer'><h2>Comvoly answer</h2>"
        f"<p>{safe}</p><small>Interpreted {answer.evidence_count} archived messages. "
        "AI can make mistakes; check the cited community evidence.</small>"
        f"<h3>Supporting community evidence</h3>{citations}</section>"
    )


def page(query: str, question: str = "", answer: GroundedAnswer | None = None, error: str = ""):
    groups, messages, media, last, syncs = data()
    q = html.escape(query)
    group_html = "".join(f"<li><b>{html.escape(g['title'])}</b><span>Telegram | last import {html.escape(date(g['imported_at']))}</span></li>" for g in groups) or "<li>No community connected yet.</li>"
    results = find(query)
    result_html = ""
    if query:
        items = "".join(f"<article><div><b>{html.escape(r['title'])}</b> | {html.escape(date(r['sent_at']))} | Message #{r['telegram_message_id']}</div><p>{html.escape(r['text'])}</p></article>" for r in results) or "<div class='notice'>No messages matched that search.</div>"
        result_html = f"<section class='panel'><h2>Results for &quot;{q}&quot;</h2>{items}</section>"
    sync_html = "".join(
        f"<li><b>{html.escape(row['title'] or 'Community')}</b><span>{html.escape(date(row['finished_at']))} | {html.escape(row['status'])} | {row['imported_count']} imported</span></li>"
        for row in syncs
    ) or "<li>Sync history will appear after the next Comvoly import.</li>"
    ai_result = answer_html(answer) if answer else (
        f"<section class='notice error'>{html.escape(error)}</section>" if error else ""
    )
    asked = html.escape(question)
    return f"""<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Comvoly Owner Dashboard</title><style>
*{{box-sizing:border-box}}body{{margin:0;background:#07152d;color:#eef4ff;font:16px Arial,sans-serif}}main{{max-width:1100px;margin:auto;padding:28px 24px 64px}}header{{display:flex;gap:12px;align-items:center}}.logo{{display:grid;place-items:center;width:42px;height:42px;border-radius:12px;background:#f7c843;color:#07152d;font-weight:900;font-size:19px}}h1{{margin:0;font-size:22px}}.role{{margin-left:auto;border:1px solid #f7c84355;border-radius:20px;padding:7px 11px;color:#f7c843;font-size:12px;font-weight:bold}}.intro{{padding:42px 0 24px}}.eyebrow{{color:#f7c843;font-size:12px;font-weight:bold;letter-spacing:.18em;text-transform:uppercase}}.intro h2{{max-width:720px;margin:14px 0;font-size:42px;line-height:1.08}}.intro p{{max-width:720px;color:#bdc9db;line-height:1.6}}.grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}}.card,.panel,.notice,article{{border:1px solid #ffffff1a;background:#ffffff0a;border-radius:16px}}.card{{padding:17px}}.card span,.card small,li span,article div,.answer small{{display:block;color:#9aabc3;font-size:12px}}.card strong{{display:block;margin:10px 0 6px;font-size:24px;color:#f7c843}}.panel,.notice{{margin-top:18px;padding:20px}}.panel h2{{margin:0 0 14px;font-size:18px}}.panel h3{{margin:24px 0 10px;font-size:15px}}ul{{margin:0;padding:0;list-style:none}}li{{padding:14px 0;border-top:1px solid #ffffff14}}li:first-child{{border:0}}li span{{margin-top:5px}}form{{display:flex;gap:8px;padding:8px;border:1px solid #ffffff1f;border-radius:15px;background:#02081799}}input,textarea{{flex:1;min-width:0;padding:12px;border:0;outline:0;background:transparent;color:#fff;font:16px Arial,sans-serif}}textarea{{resize:vertical;min-height:74px}}button{{border:0;border-radius:10px;background:#f7c843;color:#07152d;padding:0 18px;font-weight:bold;cursor:pointer}}article{{margin-top:10px;padding:16px}}article b,.cite{{color:#f7c843}}article p,.answer>p{{margin:11px 0 0;white-space:pre-wrap;line-height:1.55}}.ask{{border-color:#f7c84355}}.ask button{{min-width:130px}}.error{{border-color:#ff7d7d66;color:#ffd7d7}}@media(max-width:700px){{.grid{{grid-template-columns:repeat(2,1fr)}}.intro h2{{font-size:34px}}}}@media(max-width:440px){{.grid{{grid-template-columns:1fr}}form{{flex-direction:column}}button{{padding:12px}}}}
</style></head><body><main><header><span class='logo'>K</span><h1>Comvoly</h1><span class='role'>OWNER PREVIEW</span></header><section class='intro'><p class='eyebrow'>Community intelligence</p><h2>Ask what your community knows.</h2><p>Comvoly interprets the authorised archive and answers with evidence from the original conversations. Review the cited excerpts before relying on an answer.</p></section><section class='grid'>{card('Connected communities',len(groups),'Telegram pilot')}{card('Messages stored',messages,'Local archive')}{card('Media references',media,'Storage not enabled yet')}{card('Last successful sync',date(last),'Check sync agent terminal')}</section><section class='panel ask'><h2>Ask Comvoly</h2><form method='post' action='/ask'><textarea name='question' maxlength='1000' required placeholder='What has the community said about HGH?'>{asked}</textarea><button>Generate answer</button></form></section>{ai_result}<section class='panel'><h2>Connected community</h2><ul>{group_html}</ul></section><section class='panel'><h2>Recent sync checks</h2><ul>{sync_html}</ul></section><section class='panel'><h2>Search individual messages</h2><form method='get'><input name='q' value='{q}' placeholder='Search exact archive wording...'><button>Search</button></form></section>{result_html}<section class='notice'><b>MVP security boundary:</b> archive evidence is sent to the configured AI provider when you ask a question. This local owner preview is not yet an authenticated member portal.</section></main></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        request = urlparse(self.path)
        if request.path != "/":
            self.send_error(404); return
        content = page(parse_qs(request.query).get("q", [""])[0].strip()).encode()
        self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Content-Length", str(len(content))); self.end_headers(); self.wfile.write(content)

    def do_POST(self):
        request = urlparse(self.path)
        if request.path != "/ask":
            self.send_error(404); return
        try:
            length = min(int(self.headers.get("Content-Length", "0")), 20_000)
            form = parse_qs(self.rfile.read(length).decode("utf-8"))
            question = form.get("question", [""])[0].strip()[:1000]
            answer = answer_question(question)
            content = page("", question, answer=answer).encode()
        except Exception as error:
            question = locals().get("question", "")
            content = page("", question, error=f"Comvoly could not answer: {error}").encode()
        self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Content-Length", str(len(content))); self.end_headers(); self.wfile.write(content)


if __name__ == "__main__":
    print("Comvoly owner dashboard: http://127.0.0.1:8000")
    ThreadingHTTPServer(("127.0.0.1", 8000), Handler).serve_forever()
