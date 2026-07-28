"""Server-side workspace authorisation for Comvoly v2."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from database import query, uses_postgres


class AccessDenied(PermissionError):
    """Raised without revealing whether another workspace's resource exists."""


CAPABILITIES = {
    "use_intelligence",
    "view_evidence",
    "save_personal_items",
    "curate_knowledge",
    "review_concerns",
    "invite_members",
    "change_roles",
    "manage_sources",
    "import_history",
    "change_processing_policy",
    "view_usage",
    "manage_billing",
    "export_workspace",
    "transfer_ownership",
    "delete_workspace",
}

ROLE_CAPABILITIES = {
    "owner": CAPABILITIES,
    "administrator": CAPABILITIES - {
        "change_roles", "change_processing_policy", "manage_billing", "export_workspace",
        "transfer_ownership", "delete_workspace",
    },
    "moderator": {"use_intelligence", "view_evidence", "save_personal_items", "curate_knowledge", "review_concerns"},
    "member": {"use_intelligence", "view_evidence", "save_personal_items"},
}


@dataclass(frozen=True)
class Principal:
    account_id: str
    session_id: str | None = None


@dataclass(frozen=True)
class WorkspaceContext:
    account_id: str
    workspace_id: str
    role: str
    capabilities: frozenset[str]

    def require(self, capability: str) -> None:
        if capability not in self.capabilities:
            raise AccessDenied("This account is not authorised for that workspace action.")


def authorise_workspace(connection: Any, principal: Principal, workspace_id: str, capability: str) -> WorkspaceContext:
    if capability not in CAPABILITIES:
        raise ValueError(f"Unknown capability: {capability}")
    row = connection.execute(
        query("""SELECT m.role FROM memberships m
                 JOIN accounts a ON a.id = m.account_id
                 JOIN workspaces w ON w.id = m.workspace_id
                 WHERE m.workspace_id = ? AND m.account_id = ? AND m.state = 'active'
                   AND a.status = 'active' AND w.lifecycle NOT IN ('deletion_pending','deleted')"""),
        (workspace_id, principal.account_id),
    ).fetchone()
    if row is None:
        raise AccessDenied("This account is not authorised for that workspace action.")
    role = str(row["role"] if uses_postgres() else row[0])
    capabilities = set(ROLE_CAPABILITIES[role])
    overrides = connection.execute(
        query("""SELECT capability, allowed FROM capability_overrides
                 WHERE workspace_id = ? AND account_id = ?"""),
        (workspace_id, principal.account_id),
    ).fetchall()
    for override in overrides:
        name = str(override["capability"] if uses_postgres() else override[0])
        allowed = bool(override["allowed"] if uses_postgres() else override[1])
        capabilities.add(name) if allowed else capabilities.discard(name)
    context = WorkspaceContext(principal.account_id, workspace_id, role, frozenset(capabilities))
    context.require(capability)
    return context
