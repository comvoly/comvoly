"""Transport-neutral account/workspace API for verified server principals."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from authorization import AccessDenied, Principal
from database import query
from invitations import InvitationService
from v2_store import ComvolyStore, new_id, utc_now


class ApplicationError(Exception):
    def __init__(self, status: int, detail: str):
        super().__init__(detail)
        self.status = status
        self.detail = detail


class WorkspaceApplication:
    def __init__(self, connection: Any):
        self.store = ComvolyStore(connection)
        self.invitations = InvitationService(connection)

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

    def overview(self, principal: Principal, workspace_id: str) -> dict[str, Any]:
        context = self._context(principal, workspace_id, "use_intelligence")
        workspace = next((item for item in self.store.list_workspaces(principal) if item["id"] == workspace_id), None)
        setup_steps = self.store.connection.execute(query("""SELECT step_key, state, completed_at
            FROM workspace_setup_steps WHERE workspace_id=? ORDER BY CASE step_key
            WHEN 'community_details' THEN 1 WHEN 'connect_source' THEN 2 WHEN 'import_history' THEN 3
            WHEN 'review_knowledge' THEN 4 WHEN 'invite_members' THEN 5 ELSE 6 END"""),
            (workspace_id,)).fetchall()
        sources = self.store.connection.execute(query("""SELECT id, provider, display_name, state, health,
            created_at, updated_at FROM source_connections WHERE workspace_id=? ORDER BY created_at"""),
            (workspace_id,)).fetchall()
        imports = self.store.connection.execute(query("""SELECT id, source_connection_id, job_type, state,
            stage, progress_current, progress_total, warning_count, failure_count, updated_at
            FROM import_jobs WHERE workspace_id=? ORDER BY created_at DESC LIMIT 20"""),
            (workspace_id,)).fetchall()
        return {"workspace": workspace, "role": context.role, "capabilities": sorted(context.capabilities),
                "setup_steps": [dict(row) for row in setup_steps],
                "sources": [dict(row) for row in sources], "imports": [dict(row) for row in imports]}

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
