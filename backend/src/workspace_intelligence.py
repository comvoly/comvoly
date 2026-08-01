"""Safe workspace-scoped retrieval and deterministic cited pilot answers."""

from __future__ import annotations

import re
from typing import Any

from authorization import WorkspaceContext
from database import query


def _terms(value: str) -> list[str]:
    return [term for term in re.findall(r"[a-z0-9']{3,}", value.lower())
            if term not in {"about", "have", "what", "when", "where", "which", "with", "from", "that", "this"}]


class WorkspaceIntelligence:
    def __init__(self, connection: Any):
        self.connection = connection

    def retrieve(self, context: WorkspaceContext, question: str, limit: int = 12) -> list[dict[str, Any]]:
        context.require("use_intelligence")
        terms = _terms(question)
        if not terms:
            return []
        clauses = " OR ".join("LOWER(COALESCE(c.body_text, '')) LIKE LOWER(?)" for _ in terms)
        rows = self.connection.execute(query(f"""SELECT c.id, c.body_text, c.source_created_at,
            c.author_display_name, c.external_item_id, c.source_connection_id,
            c.ingestion_method, s.display_name AS source_name, s.provider
            FROM content_items c JOIN source_connections s
              ON s.id=c.source_connection_id AND s.workspace_id=c.workspace_id
            WHERE c.workspace_id=? AND c.source_deleted_at IS NULL AND c.review_state='active'
              AND ({clauses})
            ORDER BY c.source_created_at DESC LIMIT ?"""),
            (context.workspace_id, *(f"%{term}%" for term in terms), min(max(limit, 1), 30))).fetchall()
        return [dict(row) for row in rows]

    def answer(self, context: WorkspaceContext, question: str) -> dict[str, Any]:
        evidence = self.retrieve(context, question)
        citations = [{
            "content_id": row["id"], "source_name": row["source_name"],
            "provider": row["provider"], "external_item_id": row["external_item_id"],
            "ingestion_method": row["ingestion_method"],
            "author": row["author_display_name"] or "Community member",
            "source_created_at": row["source_created_at"], "excerpt": str(row["body_text"] or "")[:800],
        } for row in evidence[:5]]
        if not citations:
            answer = "I could not find enough authorised community evidence to answer that yet."
        else:
            excerpts = " ".join(str(item["excerpt"]).strip() for item in citations[:3])
            answer = (f"I found {len(evidence)} relevant community message"
                      f"{'s' if len(evidence) != 1 else ''}. The strongest evidence says: {excerpts}")
        return {"question": question, "answer": answer, "evidence_count": len(evidence),
                "citations": citations, "mode": "extractive_pilot"}
