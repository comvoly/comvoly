"""Identity boundary for a future managed OpenID Connect provider."""

from __future__ import annotations

from dataclasses import dataclass
import json
import logging
import os
from typing import Any, Callable, Mapping, Protocol

from authorization import Principal
from database import query, uses_postgres
from v2_store import new_id, utc_now


LOGGER = logging.getLogger(__name__)


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


class NeonJWTIdentityProvider:
    """Verify Neon Auth JWTs with a branch-specific JWKS endpoint.

    The decoder injection keeps unit tests offline. Runtime verification is fail-closed
    and restricts accepted algorithms instead of trusting the token header.
    """

    def __init__(self, jwks_url: str, issuer: str, audience: str | None = None,
                 algorithms: tuple[str, ...] = ("EdDSA", "ES256", "RS256"),
                 decoder: Callable[[str], Mapping[str, Any]] | None = None):
        if not jwks_url.startswith("https://") or not issuer.startswith("https://"):
            raise ValueError("Neon Auth JWKS URL and issuer must use HTTPS.")
        self.jwks_url = jwks_url
        self.issuer = issuer.rstrip("/")
        self.audience = audience or None
        self.algorithms = algorithms
        self._decoder = decoder
        self._jwks_client: Any | None = None

    @classmethod
    def from_environment(cls) -> "NeonJWTIdentityProvider":
        jwks_url = os.getenv("NEON_AUTH_JWKS_URL", "").strip()
        issuer = os.getenv("NEON_AUTH_ISSUER", "").strip()
        if not jwks_url or not issuer:
            raise RuntimeError("Neon Auth requires NEON_AUTH_JWKS_URL and NEON_AUTH_ISSUER.")
        algorithms = tuple(item.strip() for item in os.getenv(
            "NEON_AUTH_JWT_ALGORITHMS", "EdDSA,ES256,RS256").split(",") if item.strip())
        return cls(jwks_url, issuer, os.getenv("NEON_AUTH_AUDIENCE", "").strip() or None,
                   algorithms)

    def _decode(self, token: str) -> Mapping[str, Any]:
        try:
            import jwt
        except ImportError as error:
            raise RuntimeError("Neon Auth verification requires PyJWT with cryptography.") from error
        if self._jwks_client is None:
            self._jwks_client = jwt.PyJWKClient(self.jwks_url, cache_jwk_set=True, lifespan=300)
        key = self._jwks_client.get_signing_key_from_jwt(token).key
        options = {
            "require": ["exp", "iat", "iss", "sub"],
            "verify_aud": self.audience is not None,
            # Neon currently emits the configured Auth URL with a trailing slash.
            # Verify the signed claim below after canonicalising that one benign
            # representation difference; every other issuer remains rejected.
            "verify_iss": False,
        }
        return jwt.decode(token, key, algorithms=list(self.algorithms),
                          audience=self.audience, options=options)

    def verify_session(self, token: str) -> VerifiedIdentity | None:
        if not token:
            return None
        try:
            claims = dict((self._decoder or self._decode)(token))
        except Exception as error:
            # Never log the bearer token or claims. The exception class is sufficient
            # to diagnose configuration/algorithm failures in an isolated rollout.
            LOGGER.warning("Managed identity verification failed (%s).", type(error).__name__)
            return None
        if str(claims.get("iss", "")).rstrip("/") != self.issuer:
            LOGGER.warning("Managed identity verification failed (InvalidIssuerError: %s).",
                           str(claims.get("iss", ""))[:300])
            return None
        subject = str(claims.get("sub", "")).strip()
        if not subject:
            return None
        display_name = str(claims.get("name") or claims.get("email") or "Comvoly member").strip()
        return VerifiedIdentity("neon", subject, display_name, claims)


class AccountResolver(Protocol):
    def resolve_account(self, identity: VerifiedIdentity) -> Principal: ...


class AccountNotProvisioned(PermissionError):
    """The identity is valid but is not allowed to create a Comvoly account."""


class DatabaseAccountResolver:
    """Map an external identity to one Comvoly account without granting membership."""

    def __init__(self, connection: Any, allow_registration: bool = False):
        self.connection = connection
        self.allow_registration = allow_registration

    def resolve_account(self, identity: VerifiedIdentity) -> Principal:
        row = self.connection.execute(query("""SELECT a.id, a.status FROM linked_identities i
            JOIN accounts a ON a.id = i.account_id
            WHERE i.provider = ? AND i.provider_subject = ? AND i.state = 'linked'"""),
            (identity.provider, identity.subject)).fetchone()
        if row is not None:
            account_id = str(row["id"] if uses_postgres() else row[0])
            status = str(row["status"] if uses_postgres() else row[1])
            if status != "active":
                raise AccountNotProvisioned("This Comvoly account is not active.")
            self.connection.execute(query("UPDATE accounts SET last_active_at = ? WHERE id = ?"),
                                    (utc_now(), account_id))
            return Principal(account_id)
        if not self.allow_registration:
            raise AccountNotProvisioned("This account has not been approved for Comvoly.")

        account_id, identity_id, now = new_id("acct"), new_id("ident"), utc_now()
        safe_metadata = {
            key: identity.claims[key] for key in ("email", "email_verified")
            if key in identity.claims
        }
        self.connection.execute(query("""INSERT INTO accounts
            (id, display_name, status, created_at, last_active_at)
            VALUES (?, ?, 'active', ?, ?)"""), (account_id, identity.display_name, now, now))
        self.connection.execute(query("""INSERT INTO linked_identities
            (id, account_id, provider, provider_subject, display_metadata_json,
             verification_method, verified_at, state, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 'jwt_jwks', ?, 'linked', ?, ?)"""),
            (identity_id, account_id, identity.provider, identity.subject,
             json.dumps(safe_metadata, separators=(",", ":")), now, now, now))
        self.connection.execute(query("""INSERT INTO audit_events
            (id, actor_account_id, action, target_type, target_id, outcome,
             metadata_json, occurred_at) VALUES (?, ?, 'account.registered',
             'account', ?, 'success', ?, ?)"""),
            (new_id("audit"), account_id, account_id,
             json.dumps({"provider": identity.provider}, separators=(",", ":")), now))
        return Principal(account_id)
