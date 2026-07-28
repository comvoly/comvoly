"""Identity boundary for a future managed OpenID Connect provider."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Protocol

from authorization import Principal


@dataclass(frozen=True)
class VerifiedIdentity:
    provider: str
    subject: str
    display_name: str
    claims: Mapping[str, object]


class IdentityProvider(Protocol):
    def verify_session(self, token: str) -> VerifiedIdentity | None: ...


class LocalTestIdentityProvider:
    """Explicit test adapter; never accepts tokens unless pre-registered in memory."""

    def __init__(self, sessions: Mapping[str, VerifiedIdentity] | None = None):
        self._sessions = dict(sessions or {})

    def verify_session(self, token: str) -> VerifiedIdentity | None:
        return self._sessions.get(token)


class AccountResolver(Protocol):
    def resolve_account(self, identity: VerifiedIdentity) -> Principal: ...

