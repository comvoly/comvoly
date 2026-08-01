"""Transport-neutral account/workspace API for verified server principals."""

from __future__ import annotations

from dataclasses import asdict
import json
from typing import Any

from authorization import AccessDenied, Principal
from database import query
from invitations import InvitationService
from telegram_export import normalise_messages, preview_export, checksum_item
from telegram_live import TelegramLiveService
from v2_store import ComvolyStore, new_id, utc_now
from workspace_intelligence import WorkspaceIntelligence


class ApplicationError(Exception):
    def __init__(self, status: int, detail: str):
        super().__init__(detail)
        self.status = status
        self.detail = detail


class WorkspaceApplication:
    def __init__(self, connection: Any, telegram_live: TelegramLiveService | None = None):
        self.store = ComvolyStore(connection)
        self.invitations = InvitationService(connection)
        self.telegram_live = telegram_live
        self.intelligence = WorkspaceIntelligence(connection)

    def session(self, principal: Principal) -> dict[str, Any]:
        workspaces = self.store.list_workspaces(principal)
        return {"account_id": principal.account_id, "workspaces": workspaces}

    def create_workspace(self, principal: Principal, payload: dict[str, Any]) -> dict[str, Any]:
        name = str(payload.get("name", "")).strip()
        handle = str(payload.get("handle", "")).strip().lower()
        if not name or len(name) > 120 or not handle or len(handle) > 48 or not handle.replace("-", "").isalnum():
            raise ApplicationError(400, "Enter a workspace name and a simple letter, number, or hyphen handle.")
        if self.store.connection.execute(query(
                "SELECT 1 FROM workspaces WHERE handle=?"), (handle,)).fetchone() is not None:
            raise ApplicationError(409, "That community handle is already in use.")
        workspace_id = self.store.create_workspace(principal, name, handle)
        return {"workspace_id": workspace_id}

    def delete_workspace(self, principal: Principal, workspace_id: str,
                         payload: dict[str, Any]) -> dict[str, Any]:
        """Remove a workspace from every account while retaining recoverable pilot data."""
        context = self._context(principal, workspace_id, "delete_workspace")
        workspace = self.store.connection.execute(query(
            "SELECT name FROM workspaces WHERE id=?"), (workspace_id,)).fetchone()
        if workspace is None:
            raise ApplicationError(404, "Workspace not found.")
        name = str(workspace["name"])
        if str(payload.get("confirm_name", "")).strip() != name:
            raise ApplicationError(400, "Enter the community name exactly to confirm deletion.")
        now = utc_now()
        self.store._audit(workspace_id, context.account_id, "workspace.deleted",
                          "workspace", workspace_id,
                          metadata={"knowledge_retained_for_recovery": True})
        configs = self.store.connection.execute(query("""SELECT source_connection_id
            FROM telegram_connection_configs WHERE workspace_id=?"""), (workspace_id,)).fetchall()
        for config in configs:
            source_id = str(config["source_connection_id"])
            self.store.connection.execute(query("""UPDATE telegram_connection_configs
                SET activation_state='revoked', receives_messages=0, expected_chat_id=?, updated_at=?
                WHERE source_connection_id=? AND workspace_id=?"""),
                (f"revoked:{source_id}", now, source_id, workspace_id))
        self.store.connection.execute(query("""UPDATE source_connections
            SET state='revoked', health='unknown', updated_at=? WHERE workspace_id=?"""),
            (now, workspace_id))
        self.store.connection.execute(query("""UPDATE workspace_invitations
            SET state='revoked', updated_at=? WHERE workspace_id=? AND state='pending'"""),
            (now, workspace_id))
        self.store.connection.execute(query("""UPDATE memberships SET state='revoked',
            revoked_at=?, updated_at=? WHERE workspace_id=? AND state<>'revoked'"""),
            (now, now, workspace_id))
        self.store.connection.execute(query("""UPDATE workspaces SET lifecycle='deleted',
            deleted_at=?, updated_at=? WHERE id=?"""), (now, now, workspace_id))
        return {"workspace_id": workspace_id, "state": "deleted", "recoverable": True}

    def overview(self, principal: Principal, workspace_id: str) -> dict[str, Any]:
        context = self._context(principal, workspace_id, "use_intelligence")
        workspace = next((item for item in self.store.list_workspaces(principal) if item["id"] == workspace_id), None)
        setup_steps = self.store.connection.execute(query("""SELECT step_key, state, completed_at
            FROM workspace_setup_steps WHERE workspace_id=? ORDER BY CASE step_key
            WHEN 'community_details' THEN 1 WHEN 'connect_source' THEN 2 WHEN 'import_history' THEN 3
            WHEN 'review_knowledge' THEN 4 WHEN 'invite_members' THEN 5 ELSE 6 END"""),
            (workspace_id,)).fetchall()
        sources = self.store.connection.execute(query("""SELECT id, provider, display_name, state, health,
            created_at, updated_at FROM source_connections
            WHERE workspace_id=? AND state <> 'revoked' ORDER BY created_at"""),
            (workspace_id,)).fetchall()
        imports = self.store.connection.execute(query("""SELECT id, source_connection_id, job_type, state,
            stage, progress_current, progress_total, warning_count, failure_count, updated_at
            FROM import_jobs WHERE workspace_id=? ORDER BY created_at DESC LIMIT 20"""),
            (workspace_id,)).fetchall()
        return {"workspace": workspace, "role": context.role, "capabilities": sorted(context.capabilities),
                "setup_steps": [dict(row) for row in setup_steps] if "manage_sources" in context.capabilities else [],
                "sources": [dict(row) for row in sources],
                "imports": [dict(row) for row in imports] if "import_history" in context.capabilities else []}

    def create_source(self, principal: Principal, workspace_id: str,
                      payload: dict[str, Any]) -> dict[str, Any]:
        context = self._context(principal, workspace_id, "manage_sources")
        provider = str(payload.get("provider", "")).strip().lower()
        display_name = str(payload.get("display_name", "")).strip()
        if provider not in {"telegram", "discord", "skool"}:
            raise ApplicationError(400, "Choose Telegram, Discord, or Skool.")
        if not display_name or len(display_name) > 120:
            raise ApplicationError(400, "Enter a source name of 1 to 120 characters.")
        # No external credential is collected at this milestone. The draft ID is
        # deliberately local to Comvoly and cannot be mistaken for platform access.
        source_id = self.store.create_source(
            context, provider, f"pending:{new_id('external')}", display_name)
        self._mark_setup_step(context.account_id, workspace_id, "connect_source", "in_progress")
        return {"source_id": source_id, "state": "draft"}

    def update_setup_step(self, principal: Principal, workspace_id: str, step_key: str,
                          payload: dict[str, Any]) -> dict[str, Any]:
        context = self._context(principal, workspace_id, "manage_sources")
        allowed = {"community_details", "connect_source", "import_history",
                   "review_knowledge", "invite_members"}
        state = str(payload.get("state", "completed"))
        if step_key not in allowed or state not in {"not_started", "in_progress", "completed", "blocked", "skipped"}:
            raise ApplicationError(400, "Invalid setup step or state.")
        self._mark_setup_step(context.account_id, workspace_id, step_key, state)
        return {"step_key": step_key, "state": state}

    def preview_telegram_export(self, principal: Principal, workspace_id: str,
                                payload: dict[str, Any]) -> dict[str, Any]:
        self._context(principal, workspace_id, "import_history")
        document = payload.get("export")
        if not isinstance(document, dict):
            raise ApplicationError(400, "Choose Telegram Desktop's result.json file.")
        return preview_export(document).to_dict()

    def start_telegram_import(self, principal: Principal, workspace_id: str,
                              payload: dict[str, Any]) -> dict[str, Any]:
        context = self._context(principal, workspace_id, "import_history")
        summary = payload.get("summary")
        if not isinstance(summary, dict):
            raise ApplicationError(400, "Preview the Telegram export before importing it.")
        external_id = str(summary.get("external_community_id", "")).strip()
        display_name = str(summary.get("community_name", "Telegram community")).strip()[:120]
        total_value = summary.get("message_count")
        total = int(total_value) if total_value is not None else None
        if not external_id or (total is not None and total < 0):
            raise ApplicationError(400, "The Telegram export summary is invalid.")
        idempotency_key = str(payload.get("idempotency_key") or new_id("upload")).strip()
        if not idempotency_key or len(idempotency_key) > 200:
            raise ApplicationError(400, "The import resume key is invalid.")
        existing = self.store.connection.execute(query("""SELECT id FROM import_jobs
            WHERE workspace_id=? AND idempotency_key=?"""),
            (workspace_id, idempotency_key)).fetchone()
        if existing is not None:
            result = self._telegram_import_status(context, str(existing["id"]))
            result["resumed"] = True
            return result
        source_id = str(payload.get("source_id", "")).strip()
        source = self.store.connection.execute(query("""SELECT id, provider FROM source_connections
            WHERE id=? AND workspace_id=?"""), (source_id, workspace_id)).fetchone() if source_id else None
        if source is None:
            source_id = self.store.create_source(context, "telegram", external_id, display_name)
        elif str(source["provider"]) != "telegram":
            raise ApplicationError(400, "Choose a Telegram source for this export.")
        else:
            self.store.connection.execute(query("""UPDATE source_connections SET external_community_id=?,
                display_name=?, state=CASE WHEN state='connected' THEN state ELSE 'connecting' END,
                health=CASE WHEN state='connected' THEN health ELSE 'unknown' END, updated_at=?
                WHERE id=? AND workspace_id=?"""),
                (external_id, display_name, utc_now(), source_id, workspace_id))
        bytes_total_value = payload.get("bytes_total")
        bytes_total = int(bytes_total_value) if bytes_total_value is not None else None
        if bytes_total is not None and bytes_total < 0:
            raise ApplicationError(400, "The import file size is invalid.")
        job_id = self.store.create_import_job(context, source_id, "telegram_desktop_export", idempotency_key)
        self.store.connection.execute(query("""UPDATE import_jobs SET state='uploading', stage='uploading',
            progress_total=?, bytes_total=?, started_at=?, updated_at=? WHERE id=? AND workspace_id=?"""),
            (total, bytes_total, utc_now(), utc_now(), job_id, workspace_id))
        self.store.save_checkpoint(context, job_id, "preview", summary)
        self._mark_setup_step(context.account_id, workspace_id, "import_history", "in_progress")
        result = self._telegram_import_status(context, job_id)
        result["resumed"] = False
        return result

    def import_telegram_chunk(self, principal: Principal, workspace_id: str, job_id: str,
                              payload: dict[str, Any]) -> dict[str, Any]:
        context = self._context(principal, workspace_id, "import_history")
        chunk_index = int(payload.get("chunk_index", -1))
        messages = payload.get("messages")
        if chunk_index < 0 or not isinstance(messages, list) or len(messages) > 500:
            raise ApplicationError(400, "Import chunks must contain at most 500 messages and a valid index.")
        job = self.store.connection.execute(query("""SELECT source_connection_id, progress_current,
            progress_total, bytes_current, bytes_total, state FROM import_jobs WHERE id=? AND workspace_id=?"""),
            (job_id, workspace_id)).fetchone()
        if job is None:
            raise ApplicationError(404, "Import not found.")
        if str(job["state"]) not in {"uploading", "validating", "parsing", "storing"}:
            raise ApplicationError(409, "This import is not accepting message batches.")
        checkpoint_key = f"chunk:{chunk_index}"
        existing = self.store.connection.execute(query("""SELECT 1 FROM import_checkpoints
            WHERE job_id=? AND workspace_id=? AND checkpoint_key=?"""),
            (job_id, workspace_id, checkpoint_key)).fetchone()
        if existing is not None:
            return {"job_id": job_id, "duplicate": True,
                    "progress_current": int(job["progress_current"]), "progress_total": job["progress_total"]}
        source_id = str(job["source_connection_id"])
        source = self.store.connection.execute(query("""SELECT external_community_id FROM source_connections
            WHERE id=? AND workspace_id=? AND provider='telegram'"""), (source_id, workspace_id)).fetchone()
        if source is None:
            raise ApplicationError(404, "Telegram source not found.")
        external_id = str(source["external_community_id"])
        normalised = normalise_messages((item for item in messages if isinstance(item, dict)), external_id)
        space_id, conversation_id = self._ensure_telegram_scope(workspace_id, source_id, external_id)
        now = utc_now()
        for item in normalised:
            metadata = dict(item.metadata or {})
            if item.reply_to_external_id:
                metadata["reply_to_external_id"] = item.reply_to_external_id
            self.store.connection.execute(query("""INSERT INTO content_items
                (id, workspace_id, source_connection_id, source_space_id, conversation_id,
                 external_item_id, item_type, author_external_id, body_text, source_created_at,
                 source_checksum, ingestion_method, ingested_at, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'telegram_desktop_export', ?, ?)
                ON CONFLICT(source_connection_id, external_item_id) DO UPDATE SET
                author_external_id=excluded.author_external_id, body_text=excluded.body_text,
                source_created_at=excluded.source_created_at, source_checksum=excluded.source_checksum,
                ingested_at=excluded.ingested_at, metadata_json=excluded.metadata_json"""),
                (new_id("item"), workspace_id, source_id, space_id, conversation_id,
                 item.external_item_id, item.item_type, item.author_external_id, item.body_text,
                 item.source_created_at, checksum_item(item), now,
                 json.dumps(metadata, separators=(",", ":"), default=str)))
        current = int(job["progress_current"]) + len(normalised)
        supplied_bytes = int(payload.get("bytes_processed", 0) or 0)
        bytes_current = max(int(job["bytes_current"]), supplied_bytes)
        self.store.connection.execute(query("""UPDATE import_jobs SET state='storing', stage='storing',
            progress_current=?, bytes_current=?, updated_at=? WHERE id=? AND workspace_id=?"""),
            (current, bytes_current, now, job_id, workspace_id))
        self.store.save_checkpoint(context, job_id, checkpoint_key,
                                   {"message_count": len(messages), "stored_count": len(normalised),
                                    "bytes_processed": bytes_current})
        return {"job_id": job_id, "duplicate": False, "progress_current": current,
                "progress_total": job["progress_total"], "bytes_current": bytes_current,
                "bytes_total": job["bytes_total"]}

    def complete_telegram_import(self, principal: Principal, workspace_id: str,
                                 job_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        context = self._context(principal, workspace_id, "import_history")
        job = self.store.connection.execute(query("""SELECT source_connection_id, progress_current,
            progress_total FROM import_jobs WHERE id=? AND workspace_id=?"""),
            (job_id, workspace_id)).fetchone()
        if job is None:
            raise ApplicationError(404, "Import not found.")
        final_summary = (payload or {}).get("summary")
        final_total = int(final_summary.get("message_count", job["progress_current"])) \
            if isinstance(final_summary, dict) else int(job["progress_current"])
        if final_total < int(job["progress_current"]):
            final_total = int(job["progress_current"])
        warnings = final_summary.get("warnings", []) if isinstance(final_summary, dict) else []
        warning_count = min(len(warnings), 1000) if isinstance(warnings, list) else 0
        now = utc_now()
        self.store.connection.execute(query("""UPDATE import_jobs SET state='owner_review',
            stage='owner_review', progress_total=?, bytes_current=COALESCE(bytes_total, bytes_current),
            warning_count=?, finished_at=?, updated_at=? WHERE id=? AND workspace_id=?"""),
            (final_total, warning_count, now, now, job_id, workspace_id))
        if isinstance(final_summary, dict):
            self.store.save_checkpoint(context, job_id, "final_summary", final_summary)
        self.store.connection.execute(query("""UPDATE source_connections SET state='paused',
            health='unknown', updated_at=? WHERE id=? AND workspace_id=? AND state<>'connected'"""),
            (now, str(job["source_connection_id"]), workspace_id))
        self.store.connection.execute(query("UPDATE workspaces SET lifecycle='review', updated_at=? WHERE id=?"),
                                      (now, workspace_id))
        self._mark_setup_step(context.account_id, workspace_id, "import_history", "completed")
        self._mark_setup_step(context.account_id, workspace_id, "review_knowledge", "in_progress")
        self.store._audit(workspace_id, context.account_id, "telegram.import_ready_for_review",
                          "import_job", job_id, metadata={"stored": int(job["progress_current"])})
        return self._telegram_import_status(context, job_id)

    def telegram_import_status(self, principal: Principal, workspace_id: str,
                               job_id: str) -> dict[str, Any]:
        context = self._context(principal, workspace_id, "import_history")
        return self._telegram_import_status(context, job_id)

    def _telegram_import_status(self, context: Any, job_id: str) -> dict[str, Any]:
        job = self.store.get_import_job(context, job_id)
        if job is None:
            raise ApplicationError(404, "Import not found.")
        checkpoints = self.store.connection.execute(query("""SELECT checkpoint_key
            FROM import_checkpoints WHERE job_id=? AND workspace_id=?
            AND checkpoint_key LIKE 'chunk:%' ORDER BY checkpoint_key"""),
            (job_id, context.workspace_id)).fetchall()
        completed = sorted(int(str(row["checkpoint_key"]).split(":", 1)[1])
                           for row in checkpoints)
        result = dict(job)
        result["job_id"] = result.pop("id")
        result["completed_chunks"] = completed
        result["source_id"] = result.pop("source_connection_id")
        return result

    def ingestion_health(self, principal: Principal, workspace_id: str) -> dict[str, Any]:
        context = self._context(principal, workspace_id, "manage_sources")
        rows = self.store.connection.execute(query("""SELECT s.id, s.provider, s.display_name,
            s.state, s.health, s.created_at, s.updated_at,
            c.activation_state, c.membership_status, c.receives_messages, c.last_received_at,
            COUNT(i.id) AS stored_message_count,
            COALESCE(SUM(CASE WHEN i.ingestion_method='telegram_bot_webhook' THEN 1 ELSE 0 END),0)
                AS live_message_count,
            COALESCE(SUM(CASE WHEN i.ingestion_method='telegram_desktop_export' THEN 1 ELSE 0 END),0)
                AS historical_message_count,
            MIN(i.source_created_at) AS history_start, MAX(i.source_created_at) AS history_end,
            MAX(i.ingested_at) AS last_ingested_at
            FROM source_connections s
            LEFT JOIN telegram_connection_configs c ON c.source_connection_id=s.id
                AND c.workspace_id=s.workspace_id
            LEFT JOIN content_items i ON i.source_connection_id=s.id AND i.workspace_id=s.workspace_id
            WHERE s.workspace_id=? AND s.state<>'revoked'
            GROUP BY s.id, s.provider, s.display_name, s.state, s.health, s.created_at, s.updated_at,
                c.activation_state, c.membership_status, c.receives_messages, c.last_received_at
            ORDER BY s.created_at"""), (workspace_id,)).fetchall()
        sources = [dict(row) for row in rows]
        return {"workspace_id": context.workspace_id, "sources": sources,
                "stored_message_count": sum(int(row["stored_message_count"]) for row in sources),
                "last_ingested_at": max((str(row["last_ingested_at"]) for row in sources
                                         if row["last_ingested_at"]), default=None)}

    def prepare_telegram_live(self, principal: Principal, workspace_id: str,
                              payload: dict[str, Any]) -> dict[str, Any]:
        context = self._context(principal, workspace_id, "manage_sources")
        if self.telegram_live is None:
            raise ApplicationError(503, "The official Comvoly Telegram bot has not been configured yet.")
        return self.telegram_live.prepare(context, str(payload.get("source_id", "")))

    def connect_telegram(self, principal: Principal, workspace_id: str,
                         payload: dict[str, Any]) -> dict[str, Any]:
        """Create or reuse the Telegram source, then prepare it in one owner action."""
        context = self._context(principal, workspace_id, "manage_sources")
        if self.telegram_live is None:
            raise ApplicationError(503, "The official Comvoly Telegram bot has not been configured yet.")
        display_name = str(payload.get("display_name", "")).strip()
        if not display_name or len(display_name) > 120:
            raise ApplicationError(400, "Enter a Telegram group name of 1 to 120 characters.")
        source = self.store.connection.execute(query("""SELECT id FROM source_connections
            WHERE workspace_id=? AND provider='telegram' AND state <> 'revoked'
            ORDER BY created_at LIMIT 1"""),
            (workspace_id,)).fetchone()
        if source is None:
            source_id = self.store.create_source(
                context, "telegram", f"pending:{new_id('external')}", display_name)
        else:
            source_id = str(source["id"])
            self.store.connection.execute(query("""UPDATE source_connections SET display_name=?,
                updated_at=? WHERE id=? AND workspace_id=?"""),
                (display_name, utc_now(), source_id, workspace_id))
        self._mark_setup_step(context.account_id, workspace_id, "connect_source", "in_progress")
        return self.telegram_live.prepare(context, source_id)

    def disconnect_telegram(self, principal: Principal, workspace_id: str,
                            source_id: str) -> dict[str, Any]:
        """Revoke a Telegram binding while retaining its historical knowledge."""
        context = self._context(principal, workspace_id, "manage_sources")
        source = self.store.connection.execute(query("""SELECT id FROM source_connections
            WHERE id=? AND workspace_id=? AND provider='telegram' AND state <> 'revoked'"""),
            (source_id, workspace_id)).fetchone()
        if source is None:
            raise ApplicationError(404, "Telegram connection not found.")
        now = utc_now()
        self.store.connection.execute(query("""UPDATE telegram_connection_configs
            SET activation_state='revoked', receives_messages=0,
                expected_chat_id=?, updated_at=?
            WHERE source_connection_id=? AND workspace_id=?"""),
            (f"revoked:{source_id}", now, source_id, workspace_id))
        self.store.connection.execute(query("""UPDATE source_connections
            SET state='revoked', health='unknown', updated_at=?
            WHERE id=? AND workspace_id=?"""), (now, source_id, workspace_id))
        self.store._audit(workspace_id, context.account_id, "telegram.disconnected",
                          "source_connection", source_id,
                          metadata={"historical_knowledge_retained": True})
        return {"source_id": source_id, "state": "revoked", "knowledge_retained": True}

    def telegram_live_status(self, principal: Principal, workspace_id: str,
                             source_id: str) -> dict[str, Any]:
        context = self._context(principal, workspace_id, "manage_sources")
        if self.telegram_live is None:
            return {"source_id": source_id, "state": "not_prepared", "configured": False}
        return self.telegram_live.status(context, source_id)

    def ask(self, principal: Principal, workspace_id: str,
            payload: dict[str, Any]) -> dict[str, Any]:
        context = self._context(principal, workspace_id, "use_intelligence")
        question = str(payload.get("question", "")).strip()
        if not question or len(question) > 1000:
            raise ApplicationError(400, "Enter a question of up to 1,000 characters.")
        result = self.intelligence.answer(context, question)
        now = utc_now()
        period_start = now[:7] + "-01"
        self.store.connection.execute(query("""INSERT INTO usage_counters
            (workspace_id, metric, period_start, quantity, estimated_cost_minor, updated_at)
            VALUES (?, 'intelligence_questions', ?, 1, 0, ?)
            ON CONFLICT(workspace_id, metric, period_start) DO UPDATE SET
            quantity=usage_counters.quantity + 1, updated_at=excluded.updated_at"""),
            (workspace_id, period_start, now))
        self.store._audit(workspace_id, context.account_id, "intelligence.asked",
                          "workspace", workspace_id,
                          metadata={"evidence_count": result["evidence_count"], "mode": result["mode"]})
        return result

    def search(self, principal: Principal, workspace_id: str,
               payload: dict[str, Any]) -> dict[str, Any]:
        context = self._context(principal, workspace_id, "use_intelligence")
        term = str(payload.get("query", "")).strip()
        if not term or len(term) > 500:
            raise ApplicationError(400, "Enter a search query of up to 500 characters.")
        return {"query": term, "results": self.intelligence.retrieve(context, term, 30)}

    def _ensure_telegram_scope(self, workspace_id: str, source_id: str,
                               external_id: str) -> tuple[str, str]:
        row = self.store.connection.execute(query("""SELECT id FROM source_spaces
            WHERE source_connection_id=? AND external_space_id='main'"""), (source_id,)).fetchone()
        if row is None:
            space_id = new_id("space")
            now = utc_now()
            self.store.connection.execute(query("""INSERT INTO source_spaces
                (id, workspace_id, source_connection_id, external_space_id, name, space_type, created_at, updated_at)
                VALUES (?, ?, ?, 'main', 'Main chat', 'chat', ?, ?)"""),
                (space_id, workspace_id, source_id, now, now))
        else:
            space_id = str(row["id"])
        conversation = self.store.connection.execute(query("""SELECT id FROM conversations
            WHERE source_connection_id=? AND external_conversation_id=?"""),
            (source_id, external_id)).fetchone()
        if conversation is None:
            conversation_id = new_id("conversation")
            now = utc_now()
            self.store.connection.execute(query("""INSERT INTO conversations
                (id, workspace_id, source_connection_id, source_space_id, external_conversation_id,
                 conversation_type, title, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 'chat', 'Telegram chat', ?, ?)"""),
                (conversation_id, workspace_id, source_id, space_id, external_id, now, now))
        else:
            conversation_id = str(conversation["id"])
        return space_id, conversation_id

    def _mark_setup_step(self, account_id: str, workspace_id: str, step_key: str, state: str) -> None:
        now = utc_now()
        completed = now if state == "completed" else None
        self.store.connection.execute(query("""UPDATE workspace_setup_steps SET state=?,
            completed_by_account_id=?, completed_at=?, updated_at=?
            WHERE workspace_id=? AND step_key=?"""),
            (state, account_id if completed else None, completed, now, workspace_id, step_key))
        self.store._audit(workspace_id, account_id, "workspace.setup_step_updated",
                          "workspace_setup_step", step_key, metadata={"state": state})

    def invite(self, principal: Principal, workspace_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        context = self._context(principal, workspace_id, "invite_members")
        invitation = self.invitations.create(context, str(payload.get("role", "member")),
                                             str(payload.get("email_hint") or "") or None)
        self._mark_setup_step(context.account_id, workspace_id, "invite_members", "completed")
        return asdict(invitation)

    def accept_invitation(self, principal: Principal, token: str) -> dict[str, Any]:
        try:
            return {"workspace_id": self.invitations.accept(principal, token)}
        except ValueError as error:
            raise ApplicationError(400, str(error)) from error

    def members(self, principal: Principal, workspace_id: str) -> list[dict[str, Any]]:
        context = self._context(principal, workspace_id, "invite_members")
        rows = self.store.connection.execute(query("""SELECT a.id, a.display_name, a.avatar_url, m.role, m.state,
            m.admission_method, m.joined_at FROM memberships m JOIN accounts a ON a.id=m.account_id
            WHERE m.workspace_id=? ORDER BY m.role, a.display_name"""), (context.workspace_id,)).fetchall()
        return [dict(row) for row in rows]

    def _context(self, principal: Principal, workspace_id: str, capability: str):
        try:
            return self.store.context(principal, workspace_id, capability)
        except AccessDenied as error:
            raise ApplicationError(404, "Workspace not found.") from error
