"""Ground an AI answer in messages from the local Comvoly archive."""

from __future__ import annotations

import os
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from openai import APIConnectionError, APIStatusError, AuthenticationError, OpenAI, RateLimitError


BACKEND_DIR = Path(__file__).resolve().parents[1]
DATABASE = BACKEND_DIR / "data" / "comvoly.db"
MAX_ARCHIVE_CHARACTERS = 180_000

load_dotenv(BACKEND_DIR / ".env")
MODEL = os.getenv("COMVOLY_AI_MODEL", "gpt-5.6-terra")


@dataclass(frozen=True)
class Evidence:
    id: int
    community: str
    sent_at: str
    sender: str
    text: str


@dataclass(frozen=True)
class GroundedAnswer:
    text: str
    citations: list[Evidence]
    evidence_count: int


def archive_messages() -> list[Evidence]:
    if not DATABASE.exists():
        return []
    with sqlite3.connect(DATABASE) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """SELECT messages.id, communities.title, messages.sent_at,
                messages.sender_telegram_id, messages.text, messages.has_media
            FROM messages
            JOIN communities ON communities.id = messages.community_id
            ORDER BY messages.sent_at"""
        ).fetchall()
    return [
        Evidence(
            id=row["id"],
            community=row["title"],
            sent_at=row["sent_at"],
            sender=row["sender_telegram_id"] or "Unknown member",
            text=row["text"] or ("[Media attachment]" if row["has_media"] else "[Empty message]"),
        )
        for row in rows
    ]


def evidence_prompt(messages: list[Evidence]) -> str:
    lines: list[str] = []
    characters = 0
    for message in messages:
        line = (
            f"[M{message.id}] Community: {message.community} | Date: {message.sent_at} | "
            f"Member: {message.sender}\n{message.text.strip()}"
        )
        if characters + len(line) > MAX_ARCHIVE_CHARACTERS:
            break
        lines.append(line)
        characters += len(line)
    return "\n\n".join(lines)


def answer_question(question: str) -> GroundedAnswer:
    question = question.strip()
    if not question:
        raise ValueError("Enter a question for Comvoly.")
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is missing from backend/.env.")

    messages = archive_messages()
    if not messages:
        raise RuntimeError("The archive has no messages to answer from yet.")

    archive = evidence_prompt(messages)
    included_ids = {int(value) for value in re.findall(r"\[M(\d+)\]", archive)}
    try:
        response = OpenAI().responses.create(
            model=MODEL,
            store=False,
            instructions=(
                "You are Comvoly, an assistant for an authorised private community archive. "
                "Answer only from the supplied archive messages. Synthesize the community's useful "
                "knowledge instead of listing every keyword match. Cite every substantive claim with "
                "one or more message IDs exactly like [M12]. Distinguish consensus, individual "
                "experiences, disagreement, and uncertainty. Never invent names, facts, or citations. "
                "If the archive cannot answer the question, say so plainly. For health, legal, or "
                "financial topics, summarize the discussion without presenting it as professional advice."
            ),
            input=f"QUESTION:\n{question}\n\nAUTHORISED ARCHIVE MESSAGES:\n{archive}",
        )
    except AuthenticationError as error:
        raise RuntimeError("The OpenAI API key was not accepted. Check OPENAI_API_KEY in backend/.env.") from error
    except RateLimitError as error:
        if getattr(error, "code", None) == "insufficient_quota" or "insufficient_quota" in str(error):
            raise RuntimeError("The OpenAI API project has no available quota. Add billing or credits, then try again.") from error
        raise RuntimeError("The AI service is busy or rate-limited. Wait briefly and try again.") from error
    except APIConnectionError as error:
        raise RuntimeError("Comvoly could not connect to the AI service. Check the internet connection.") from error
    except APIStatusError as error:
        raise RuntimeError(f"The AI service returned an error ({error.status_code}). Try again shortly.") from error
    text = response.output_text.strip()
    cited_ids = []
    for value in re.findall(r"\[M(\d+)\]", text):
        message_id = int(value)
        if message_id in included_ids and message_id not in cited_ids:
            cited_ids.append(message_id)
    by_id = {message.id: message for message in messages}
    return GroundedAnswer(
        text=text,
        citations=[by_id[message_id] for message_id in cited_ids],
        evidence_count=len(included_ids),
    )
