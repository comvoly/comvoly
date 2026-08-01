"""Workspace-scoped persistence facade for the Comvoly v2 foundation."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any, Iterable

from authorization import Principal, WorkspaceContext, authorise_workspace
from database import query


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


class ComvolyStore:
    def __init__(self, connection: Any):
        self.connection = connection

    def create_account(self, display_name: str, account_id: str | None = None) -> str:
        account_id = account_id or new_id("acct")
        now = utc_now()
        self.connection.execute(query("""INSERT INTO accounts
            (id, display_name, status, created_at, last_active_at)
            VALUES (?, ?, 'active', ?, ?)"""), (account_id, display_name, now, now))
        return account_id

    def link_identity(self, account_id: str, provider: str, subject: str, method: str = "test_adapter") -> str:
        identity_id = new_id("ident")
        now = utc_now()
        self.connection.execute(query("""INSERT INTO linked_identities
            (id, account_id, provider, provider_subject, verification_method, verified_at,
             state, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, 'linked', ?, ?)"""),
            (identity_id, account_id, provider, subject, method, now, now, now))
        return identity_id

    def create_workspace(self, owner: Principal, name: str, handle: str, workspace_id: str | None = None) -> str:
        workspace_id = workspace_id or new_id("ws")
        now = utc_now()
        self.connection.execute(query("""INSERT INTO workspaces
            (id, owner_account_id, name, handle, lifecycle, created_at, updated_at)
            VALUES (?, ?, ?, ?, 'setup', ?, ?)"""), (workspace_id, owner.account_id, name, handle, now, now))
        self.connection.execute(query("""INSERT INTO memberships
            (workspace_id, account_id, role, state, admission_method, approved_by_account_id,
             joined_at, created_at, updated_at) VALUES (?, ?, 'owner', 'active', 'created', ?, ?, ?, ?)"""),
            (workspace_id, owner.account_id, owner.account_id, now, now, now))
        for step in ("community_details", "connect_source", "import_history", "review_knowledge", "invite_members"):
            self.connection.execute(query("""INSERT INTO workspace_setup_steps
                (workspace_id, step_key, state, updated_at) VALUES (?, ?, 'not_started', ?)"""),
                (workspace_id, step, now))
        self._audit(workspace_id, owner.account_id, "workspace.created", "workspace", workspace_id)
        return workspace_id

    def add_membership(self, context: WorkspaceContext, account_id: str, role: str, method: str = "admin_approved") -> None:
        context.require("invite_members")
        if role not in {"administrator", "moderator", "member"}:
            raise ValueError("Owners must be added through the ownership-transfer workflow.")
        now = utc_now()
        self.connection.execute(query("""INSERT INTO memberships
            (workspace_id, account_id, role, state, admission_method, approved_by_account_id,
             joined_at, created_at, updated_at) VALUES (?, ?, ?, 'active', ?, ?, ?, ?, ?)"""),
            (context.workspace_id, account_id, role, method, context.account_id, now, now, now))
        self._audit(context.workspace_id, context.account_id, "membership.activated", "account", account_id)

    def context(self, principal: Principal, workspace_id: str, capability: str) -> WorkspaceContext:
        return authorise_workspace(self.connection, principal, workspace_id, capability)

    def list_workspaces(self, principal: Principal) -> list[dict[str, Any]]:
        rows = self.connection.execute(query("""SELECT w.id, w.name, w.handle, w.lifecycle, m.role
            FROM workspaces w JOIN memberships m ON m.workspace_id = w.id
            WHERE m.account_id = ? AND m.state = 'active' AND w.lifecycle <> 'deleted'
            ORDER BY w.name"""), (principal.account_id,)).fetchall()
        return [dict(row) for row in rows]

    def create_source(self, context: WorkspaceContext, provider: str, external_community_id: str,
                      display_name: str, source_id: str | None = None) -> str:
        context.require("manage_sources")
        source_id = source_id or new_id("source")
        now = utc_now()
        self.connection.execute(query("""INSERT INTO source_connections
            (id, workspace_id, provider, external_community_id, display_name, state, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 'draft', ?, ?)"""),
            (source_id, context.workspace_id, provider, external_community_id, display_name, now, now))
        self._audit(context.workspace_id, context.account_id, "source.created", "source_connection", source_id)
        return source_id

    def add_content(self, context: WorkspaceContext, source_connection_id: str, external_item_id: str,
                    body_text: str, source_created_at: str, *, item_type: str = "message") -> str:
        context.require("import_history")
        source = self.connection.execute(query("""SELECT id FROM source_connections
            WHERE id = ? AND workspace_id = ?"""), (source_connection_id, context.workspace_id)).fetchone()
        if source is None:
            raise ValueError("The source connection is not part of the authorised workspace.")
        item_id = new_id("item")
        self.connection.execute(query("""INSERT INTO content_items
            (id, workspace_id, source_connection_id, external_item_id, item_type, body_text,
             source_created_at, ingestion_method, ingested_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'foundation_test', ?)"""),
            (item_id, context.workspace_id, source_connection_id, external_item_id, item_type,
             body_text, source_created_at, utc_now()))
        return item_id

    def search_content(self, context: WorkspaceContext, term: str, limit: int = 50) -> list[dict[str, Any]]:
        context.require("use_intelligence")
        rows = self.connection.execute(query("""SELECT id, body_text, source_created_at, source_connection_id
            FROM content_items WHERE workspace_id = ? AND LOWER(COALESCE(body_text, '')) LIKE LOWER(?)
            ORDER BY source_created_at DESC LIMIT ?"""), (context.workspace_id, f"%{term}%", limit)).fetchall()
        return [dict(row) for row in rows]

    def get_content(self, context: WorkspaceContext, content_id: str) -> dict[str, Any] | None:
        context.require("view_evidence")
        row = self.connection.execute(query("""SELECT id, body_text, source_created_at, source_connection_id
            FROM content_items WHERE workspace_id = ? AND id = ?"""), (context.workspace_id, content_id)).fetchone()
        return dict(row) if row else None

    def list_media(self, context: WorkspaceContext, content_id: str) -> list[dict[str, Any]]:
        context.require("view_evidence")
        rows = self.connection.execute(query("""SELECT m.id, m.original_name, m.media_type, m.byte_size,
            m.download_state, m.extraction_state FROM media_assets m
            JOIN content_items c ON c.id = m.content_item_id AND c.workspace_id = m.workspace_id
            WHERE m.workspace_id = ? AND m.content_item_id = ?"""),
            (context.workspace_id, content_id)).fetchall()
        return [dict(row) for row in rows]

    def create_import_job(self, context: WorkspaceContext, source_id: str | None, job_type: str,
                          idempotency_key: str) -> str:
        context.require("import_history")
        if source_id is not None:
            source = self.connection.execute(query(
                "SELECT id FROM source_connections WHERE id = ? AND workspace_id = ?"),
                (source_id, context.workspace_id)).fetchone()
            if source is None:
                raise ValueError("The source connection is not part of the authorised workspace.")
        job_id = new_id("job")
        now = utc_now()
        self.connection.execute(query("""INSERT INTO import_jobs
            (id, workspace_id, source_connection_id, requested_by_account_id, job_type, state, stage,
             idempotency_key, created_at, updated_at) VALUES (?, ?, ?, ?, ?, 'created', 'created', ?, ?, ?)"""),
            (job_id, context.workspace_id, source_id, context.account_id, job_type, idempotency_key, now, now))
        self._audit(context.workspace_id, context.account_id, "import.created", "import_job", job_id)
        return job_id

    def save_checkpoint(self, context: WorkspaceContext, job_id: str, key: str, cursor: dict[str, Any]) -> None:
        context.require("import_history")
        job = self.connection.execute(query(
            "SELECT id FROM import_jobs WHERE id = ? AND workspace_id = ?"),
            (job_id, context.workspace_id)).fetchone()
        if job is None:
            raise ValueError("The import job is not part of the authorised workspace.")
        now = utc_now()
        self.connection.execute(query("""INSERT INTO import_checkpoints
            (job_id, checkpoint_key, workspace_id, cursor_json, updated_at) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(job_id, checkpoint_key) DO UPDATE SET cursor_json=excluded.cursor_json,
            workspace_id=excluded.workspace_id, updated_at=excluded.updated_at"""),
            (job_id, key, context.workspace_id, json.dumps(cursor, separators=(",", ":")), now))

    def get_import_job(self, context: WorkspaceContext, job_id: str) -> dict[str, Any] | None:
        context.require("import_history")
        row = self.connection.execute(query("""SELECT id, source_connection_id, job_type, state, stage,
            attempt, progress_current, progress_total, bytes_current, bytes_total,
            warning_count, failure_count, error_code, error_detail,
            created_at, started_at, updated_at, finished_at FROM import_jobs
            WHERE workspace_id = ? AND id = ?"""), (context.workspace_id, job_id)).fetchone()
        return dict(row) if row else None

    def export_manifest(self, context: WorkspaceContext) -> dict[str, Any]:
        """Build a scoped export manifest; byte packaging belongs to a later worker."""
        context.require("export_workspace")
        workspace = self.connection.execute(query(
            "SELECT id, name, handle, lifecycle FROM workspaces WHERE id = ?"),
            (context.workspace_id,)).fetchone()
        sources = self.connection.execute(query("""SELECT id, provider, external_community_id, display_name
            FROM source_connections WHERE workspace_id = ? ORDER BY id"""), (context.workspace_id,)).fetchall()
        counts = self.connection.execute(query("""SELECT COUNT(*) AS content_count,
            COALESCE(SUM((SELECT COUNT(*) FROM media_assets m
              WHERE m.workspace_id = content_items.workspace_id AND m.content_item_id = content_items.id)), 0) AS media_count
            FROM content_items WHERE workspace_id = ?"""), (context.workspace_id,)).fetchone()
        return {
            "workspace": dict(workspace),
            "sources": [dict(row) for row in sources],
            "content_count": int(counts["content_count"]),
            "media_count": int(counts["media_count"]),
            "generated_at": utc_now(),
        }

    def increment_usage(self, context: WorkspaceContext, metric: str, period_start: str, quantity: int,
                        estimated_cost_minor: int = 0) -> None:
        context.require("view_usage")
        now = utc_now()
        self.connection.execute(query("""INSERT INTO usage_counters
            (workspace_id, metric, period_start, quantity, estimated_cost_minor, updated_at)
            VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(workspace_id, metric, period_start) DO UPDATE SET
            quantity=usage_counters.quantity + excluded.quantity,
            estimated_cost_minor=usage_counters.estimated_cost_minor + excluded.estimated_cost_minor,
            updated_at=excluded.updated_at"""),
            (context.workspace_id, metric, period_start, quantity, estimated_cost_minor, now))

    def get_usage(self, context: WorkspaceContext, period_start: str) -> list[dict[str, Any]]:
        context.require("view_usage")
        rows = self.connection.execute(query("""SELECT metric, quantity, estimated_cost_minor, updated_at
            FROM usage_counters WHERE workspace_id = ? AND period_start = ? ORDER BY metric"""),
            (context.workspace_id, period_start)).fetchall()
        return [dict(row) for row in rows]

    def list_audit_events(self, context: WorkspaceContext, limit: int = 100) -> list[dict[str, Any]]:
        context.require("review_concerns")
        rows = self.connection.execute(query("""SELECT id, actor_account_id, action, target_type,
            target_id, outcome, reason_code, occurred_at FROM audit_events
            WHERE workspace_id = ? ORDER BY occurred_at DESC LIMIT ?"""),
            (context.workspace_id, limit)).fetchall()
        return [dict(row) for row in rows]

    def _audit(self, workspace_id: str | None, actor_id: str | None, action: str,
               target_type: str | None = None, target_id: str | None = None,
               outcome: str = "success", metadata: dict[str, Any] | None = None) -> None:
        self.connection.execute(query("""INSERT INTO audit_events
            (id, workspace_id, actor_account_id, action, target_type, target_id, outcome, metadata_json, occurred_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"""),
            (new_id("audit"), workspace_id, actor_id, action, target_type, target_id,
             outcome, json.dumps(metadata or {}, separators=(",", ":")), utc_now()))
