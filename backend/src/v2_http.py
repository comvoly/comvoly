"""Feature-gated HTTP adapter for the Comvoly v2 workspace application."""

from __future__ import annotations

import hmac
import os
from typing import Any, Mapping

from authorization import Principal
from identity_provider import (
    AccountNotProvisioned,
    AccountResolver,
    DatabaseAccountResolver,
    IdentityProvider,
    NeonJWTIdentityProvider,
)
from workspace_application import ApplicationError, WorkspaceApplication


def v2_api_enabled() -> bool:
    return (
        os.getenv("COMVOLY_ENABLE_V2_SCHEMA", "false").lower() == "true"
        and os.getenv("COMVOLY_ENABLE_V2_API", "false").lower() == "true"
    )


def development_principal(headers: Mapping[str, str]) -> Principal | None:
    """Local adapter only. Production must replace this with verified managed identity."""
    if os.getenv("COMVOLY_V2_DEV_AUTH", "false").lower() != "true":
        return None
    configured = os.getenv("COMVOLY_V2_DEV_SECRET", "")
    supplied = headers.get("Authorization", "").removeprefix("Bearer ")
    account_id = headers.get("X-Comvoly-Account-Id", "")
    if len(configured) < 24 or not account_id or not hmac.compare_digest(configured, supplied):
        return None
    return Principal(account_id)


class V2HTTPAdapter:
    def __init__(self, connection: Any, identity_provider: IdentityProvider | None = None,
                 account_resolver: AccountResolver | None = None):
        provider_name = os.getenv("COMVOLY_IDENTITY_PROVIDER", "").strip().lower()
        self.identity_provider = identity_provider
        if self.identity_provider is None and provider_name == "neon":
            self.identity_provider = NeonJWTIdentityProvider.from_environment()
        self.managed_identity_enabled = self.identity_provider is not None
        allow_registration = os.getenv("COMVOLY_V2_SELF_REGISTRATION", "false").lower() == "true"
        self.account_resolver = account_resolver or DatabaseAccountResolver(
            connection, allow_registration=allow_registration)
        self.application = WorkspaceApplication(connection)

    def _principal(self, headers: Mapping[str, str]) -> Principal | None:
        if self.identity_provider is not None:
            token = headers.get("Authorization", "").removeprefix("Bearer ").strip()
            identity = self.identity_provider.verify_session(token)
            if identity is None:
                return None
            return self.account_resolver.resolve_account(identity)
        return development_principal(headers)

    def dispatch(self, method: str, path: str, payload: dict[str, Any],
                 headers: Mapping[str, str]) -> tuple[int, object]:
        if not v2_api_enabled():
            return 404, {"detail": "Not found."}
        try:
            principal = self._principal(headers)
        except AccountNotProvisioned as error:
            return 403, {"detail": str(error)}
        if principal is None:
            return 401, {"detail": "A verified Comvoly account session is required."}
        try:
            parts = [part for part in path.split("/") if part]
            if method == "GET" and parts == ["v2", "session"]:
                return 200, self.application.session(principal)
            if method == "POST" and parts == ["v2", "workspaces"]:
                if (self.managed_identity_enabled and os.getenv(
                        "COMVOLY_V2_ALLOW_WORKSPACE_CREATION", "false").lower() != "true"):
                    return 403, {"detail": "Workspace creation requires Comvoly approval."}
                return 201, self.application.create_workspace(principal, payload)
            if method == "POST" and parts == ["v2", "invitations", "accept"]:
                return 200, self.application.accept_invitation(principal, str(payload.get("token", "")))
            if len(parts) >= 3 and parts[:2] == ["v2", "workspaces"]:
                workspace_id = parts[2]
                if method == "GET" and len(parts) == 3:
                    return 200, self.application.overview(principal, workspace_id)
                if method == "GET" and parts[3:] == ["members"]:
                    return 200, {"members": self.application.members(principal, workspace_id)}
                if method == "POST" and parts[3:] == ["invitations"]:
                    return 201, self.application.invite(principal, workspace_id, payload)
            return 404, {"detail": "Not found."}
        except ApplicationError as error:
            return error.status, {"detail": error.detail}
        except ValueError as error:
            return 400, {"detail": str(error)}
