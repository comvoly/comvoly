"""Workspace invitation lifecycle without selecting an email or identity vendor."""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from authorization import Principal, WorkspaceContext
from database import query
from v2_store import ComvolyStore, new_id, utc_now


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


@dataclass(frozen=True)
class CreatedInvitation:
    invitation_id: str
    token: str
    expires_at: str


class InvitationService:
    def __init__(self, connection: Any):
        self.connection = connection
        self.store = ComvolyStore(connection)

    def create(self, context: WorkspaceContext, intended_role: str = "member",
               email_hint: str | None = None, lifetime_hours: int = 72) -> CreatedInvitation:
        context.require("invite_members")
        if intended_role not in {"administrator", "moderator", "member"}:
            raise ValueError("Invitations cannot grant workspace ownership.")
        if not 1 <= lifetime_hours <= 168:
            raise ValueError("Invitation lifetime must be between 1 and 168 hours.")
        invitation_id = new_id("invite")
        token = secrets.token_urlsafe(32)
        now = datetime.now(UTC)
        expires = now + timedelta(hours=lifetime_hours)
        self.connection.execute(query("""INSERT INTO workspace_invitations
            (id, workspace_id, invited_by_account_id, email_hint, intended_role, admission_method,
             token_hash, state, expires_at, created_at, updated_at)
             VALUES (?, ?, ?, ?, ?, 'invitation', ?, 'pending', ?, ?, ?)"""),
            (invitation_id, context.workspace_id, context.account_id, email_hint, intended_role,
             token_hash(token), expires.isoformat(), now.isoformat(), now.isoformat()))
        self.store._audit(context.workspace_id, context.account_id, "invitation.created", "invitation", invitation_id)
        return CreatedInvitation(invitation_id, token, expires.isoformat())

    def accept(self, principal: Principal, token: str) -> str:
        now = utc_now()
        row = self.connection.execute(query("""SELECT id, workspace_id, intended_role, expires_at
            FROM workspace_invitations WHERE token_hash = ? AND state = 'pending'"""),
            (token_hash(token),)).fetchone()
        if row is None or str(row["expires_at"]) < now:
            raise ValueError("The invitation is invalid or expired.")
        workspace_id = str(row["workspace_id"])
        owner_row = self.connection.execute(query("""SELECT account_id FROM memberships
            WHERE workspace_id = ? AND role = 'owner' AND state = 'active' ORDER BY created_at LIMIT 1"""),
            (workspace_id,)).fetchone()
        if owner_row is None:
            raise RuntimeError("The workspace has no active owner.")
        owner = Principal(str(owner_row["account_id"]))
        owner_context = self.store.context(owner, workspace_id, "invite_members")
        existing = self.connection.execute(query(
            "SELECT state FROM memberships WHERE workspace_id = ? AND account_id = ?"),
            (workspace_id, principal.account_id)).fetchone()
        if existing is None:
            self.store.add_membership(owner_context, principal.account_id, str(row["intended_role"]), "invitation")
        else:
            self.connection.execute(query("""UPDATE memberships SET state='active', role=?, admission_method='invitation',
                joined_at=?, updated_at=? WHERE workspace_id=? AND account_id=?"""),
                (str(row["intended_role"]), now, now, workspace_id, principal.account_id))
        self.connection.execute(query("""UPDATE workspace_invitations SET state='accepted',
            accepted_by_account_id=?, accepted_at=?, updated_at=? WHERE id=? AND workspace_id=?"""),
            (principal.account_id, now, now, str(row["id"]), workspace_id))
        self.store._audit(workspace_id, principal.account_id, "invitation.accepted", "invitation", str(row["id"]))
        return workspace_id

