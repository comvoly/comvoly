"""Transport-neutral account/workspace API for verified server principals."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from authorization import AccessDenied, Principal
from database import query
from invitations import InvitationService
from v2_store import ComvolyStore


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
        if not name or not handle or not handle.replace("-", "").isalnum():
            raise ApplicationError(400, "Enter a workspace name and a simple letter, number, or hyphen handle.")
        workspace_id = self.store.create_workspace(principal, name, handle)
        return {"workspace_id": workspace_id}

    def overview(self, principal: Principal, workspace_id: str) -> dict[str, Any]:
        context = self._context(principal, workspace_id, "use_intelligence")
        workspace = next((item for item in self.store.list_workspaces(principal) if item["id"] == workspace_id), None)
        return {"workspace": workspace, "role": context.role, "capabilities": sorted(context.capabilities)}

    def invite(self, principal: Principal, workspace_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        context = self._context(principal, workspace_id, "invite_members")
        invitation = self.invitations.create(context, str(payload.get("role", "member")),
                                             str(payload.get("email_hint") or "") or None)
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
