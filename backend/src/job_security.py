"""Signed, workspace-scoped identities for internal background jobs."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass

from database import query


class InvalidJobIdentity(PermissionError):
    pass


@dataclass(frozen=True)
class JobIdentity:
    job_id: str
    workspace_id: str
    source_connection_id: str | None
    expires_at: int


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def sign_job(identity: JobIdentity, secret: str) -> str:
    if len(secret) < 32:
        raise ValueError("The internal job-signing secret must contain at least 32 characters.")
    payload = _encode(json.dumps({"job": identity.job_id, "workspace": identity.workspace_id,
        "source": identity.source_connection_id, "exp": identity.expires_at},
        separators=(",", ":"), sort_keys=True).encode())
    signature = _encode(hmac.new(secret.encode(), payload.encode(), hashlib.sha256).digest())
    return f"{payload}.{signature}"


def verify_job(token: str, secret: str, now: int | None = None) -> JobIdentity:
    try:
        payload, supplied = token.split(".", 1)
        expected = _encode(hmac.new(secret.encode(), payload.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(supplied, expected):
            raise InvalidJobIdentity("The background-job identity is invalid.")
        data = json.loads(_decode(payload))
        identity = JobIdentity(str(data["job"]), str(data["workspace"]), data.get("source"), int(data["exp"]))
        if identity.expires_at < (now if now is not None else int(time.time())):
            raise InvalidJobIdentity("The background-job identity has expired.")
        return identity
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        if isinstance(error, InvalidJobIdentity):
            raise
        raise InvalidJobIdentity("The background-job identity is invalid.") from error


def authorise_job(connection, identity: JobIdentity) -> None:
    row = connection.execute(query("""SELECT id FROM import_jobs WHERE id = ? AND workspace_id = ?
        AND (source_connection_id = ? OR (source_connection_id IS NULL AND ? IS NULL))""",
        ), (identity.job_id, identity.workspace_id, identity.source_connection_id, identity.source_connection_id)).fetchone()
    if row is None:
        raise InvalidJobIdentity("The background job does not match its workspace and source scope.")
