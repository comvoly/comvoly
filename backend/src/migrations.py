"""Small, dependency-free migration runner for SQLite and PostgreSQL."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from database import query, uses_postgres


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    statements: tuple[str, ...]


V2_FOUNDATION = Migration(
    1,
    "v2_secure_multi_community_foundation",
    (
        """CREATE TABLE IF NOT EXISTS accounts (
            id TEXT PRIMARY KEY, display_name TEXT NOT NULL, avatar_url TEXT,
            status TEXT NOT NULL CHECK (status IN ('pending','active','suspended','deletion_pending','deleted')),
            locale TEXT NOT NULL DEFAULT 'en-GB', timezone TEXT NOT NULL DEFAULT 'Europe/London',
            policy_versions_json TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL,
            last_active_at TEXT, deleted_at TEXT)""",
        """CREATE TABLE IF NOT EXISTS linked_identities (
            id TEXT PRIMARY KEY, account_id TEXT NOT NULL REFERENCES accounts(id),
            provider TEXT NOT NULL, provider_subject TEXT NOT NULL, display_metadata_json TEXT NOT NULL DEFAULT '{}',
            verification_method TEXT, verified_at TEXT, credential_reference TEXT,
            token_expires_at TEXT, refresh_state TEXT, membership_verified_at TEXT,
            state TEXT NOT NULL CHECK (state IN ('linked','revoked','conflicted')),
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
            UNIQUE(provider, provider_subject))""",
        """CREATE TABLE IF NOT EXISTS workspaces (
            id TEXT PRIMARY KEY, owner_account_id TEXT NOT NULL REFERENCES accounts(id),
            name TEXT NOT NULL, handle TEXT NOT NULL UNIQUE, logo_url TEXT, purpose TEXT,
            timezone TEXT NOT NULL DEFAULT 'Europe/London',
            lifecycle TEXT NOT NULL CHECK (lifecycle IN ('setup','importing','review','active','paused','read_only','deletion_pending','deleted')),
            retention_policy_version TEXT, processing_policy_version TEXT,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL, deleted_at TEXT)""",
        """CREATE TABLE IF NOT EXISTS memberships (
            workspace_id TEXT NOT NULL REFERENCES workspaces(id), account_id TEXT NOT NULL REFERENCES accounts(id),
            role TEXT NOT NULL CHECK (role IN ('owner','administrator','moderator','member')),
            state TEXT NOT NULL CHECK (state IN ('invited','verification_pending','active','suspended','left','revoked')),
            admission_method TEXT NOT NULL, approved_by_account_id TEXT REFERENCES accounts(id),
            proof_identity_id TEXT REFERENCES linked_identities(id), proof_verified_at TEXT, next_recheck_at TEXT,
            joined_at TEXT, last_active_at TEXT, suspended_at TEXT, revoked_at TEXT,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
            PRIMARY KEY(workspace_id, account_id))""",
        """CREATE TABLE IF NOT EXISTS capability_overrides (
            workspace_id TEXT NOT NULL, account_id TEXT NOT NULL, capability TEXT NOT NULL,
            allowed INTEGER NOT NULL CHECK (allowed IN (0,1)), granted_by_account_id TEXT NOT NULL REFERENCES accounts(id),
            reason TEXT, created_at TEXT NOT NULL,
            PRIMARY KEY(workspace_id, account_id, capability),
            FOREIGN KEY(workspace_id, account_id) REFERENCES memberships(workspace_id, account_id))""",
        """CREATE TABLE IF NOT EXISTS source_connections (
            id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL REFERENCES workspaces(id), provider TEXT NOT NULL,
            external_community_id TEXT NOT NULL, display_name TEXT NOT NULL, credential_reference TEXT,
            state TEXT NOT NULL CHECK (state IN ('draft','connecting','connected','paused','degraded','revoked')),
            health TEXT NOT NULL DEFAULT 'unknown', authorised_scope_json TEXT NOT NULL DEFAULT '{}',
            cutover_at TEXT, cursor_json TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
            UNIQUE(workspace_id, provider, external_community_id), UNIQUE(id, workspace_id))""",
        """CREATE TABLE IF NOT EXISTS source_spaces (
            id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL REFERENCES workspaces(id),
            source_connection_id TEXT NOT NULL REFERENCES source_connections(id), external_space_id TEXT NOT NULL,
            parent_external_space_id TEXT, name TEXT NOT NULL, space_type TEXT NOT NULL,
            included INTEGER NOT NULL DEFAULT 1 CHECK (included IN (0,1)), metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
            UNIQUE(source_connection_id, external_space_id), UNIQUE(id, workspace_id),
            FOREIGN KEY(source_connection_id, workspace_id) REFERENCES source_connections(id, workspace_id))""",
        """CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL REFERENCES workspaces(id),
            source_connection_id TEXT NOT NULL REFERENCES source_connections(id), source_space_id TEXT REFERENCES source_spaces(id),
            external_conversation_id TEXT NOT NULL, conversation_type TEXT NOT NULL, title TEXT,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
            UNIQUE(source_connection_id, external_conversation_id), UNIQUE(id, workspace_id),
            FOREIGN KEY(source_connection_id, workspace_id) REFERENCES source_connections(id, workspace_id),
            FOREIGN KEY(source_space_id, workspace_id) REFERENCES source_spaces(id, workspace_id))""",
        """CREATE TABLE IF NOT EXISTS content_items (
            id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL REFERENCES workspaces(id),
            source_connection_id TEXT NOT NULL REFERENCES source_connections(id), source_space_id TEXT REFERENCES source_spaces(id),
            conversation_id TEXT REFERENCES conversations(id), external_item_id TEXT NOT NULL,
            item_type TEXT NOT NULL, author_external_id TEXT, author_display_name TEXT, body_text TEXT,
            source_url TEXT, reply_to_content_id TEXT REFERENCES content_items(id),
            source_created_at TEXT NOT NULL, source_edited_at TEXT, source_deleted_at TEXT,
            visibility_json TEXT NOT NULL DEFAULT '{}', source_checksum TEXT, ingestion_method TEXT NOT NULL,
            ingested_at TEXT NOT NULL, metadata_json TEXT NOT NULL DEFAULT '{}',
            UNIQUE(source_connection_id, external_item_id), UNIQUE(id, workspace_id),
            FOREIGN KEY(source_connection_id, workspace_id) REFERENCES source_connections(id, workspace_id),
            FOREIGN KEY(source_space_id, workspace_id) REFERENCES source_spaces(id, workspace_id),
            FOREIGN KEY(conversation_id, workspace_id) REFERENCES conversations(id, workspace_id))""",
        """CREATE TABLE IF NOT EXISTS media_assets (
            id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL REFERENCES workspaces(id),
            content_item_id TEXT NOT NULL REFERENCES content_items(id), external_media_id TEXT,
            original_name TEXT, media_type TEXT NOT NULL, byte_size BIGINT, checksum TEXT,
            object_key TEXT, source_availability TEXT NOT NULL, download_state TEXT NOT NULL,
            safety_state TEXT NOT NULL, extraction_state TEXT NOT NULL, processor_version TEXT,
            extraction_reference TEXT, retention_state TEXT NOT NULL, metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
            FOREIGN KEY(content_item_id, workspace_id) REFERENCES content_items(id, workspace_id))""",
        """CREATE TABLE IF NOT EXISTS import_jobs (
            id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL REFERENCES workspaces(id),
            source_connection_id TEXT REFERENCES source_connections(id), requested_by_account_id TEXT NOT NULL REFERENCES accounts(id),
            job_type TEXT NOT NULL, state TEXT NOT NULL, stage TEXT NOT NULL, attempt INTEGER NOT NULL DEFAULT 0,
            idempotency_key TEXT NOT NULL, progress_current BIGINT NOT NULL DEFAULT 0,
            progress_total BIGINT, bytes_current BIGINT NOT NULL DEFAULT 0, bytes_total BIGINT,
            warning_count INTEGER NOT NULL DEFAULT 0, failure_count INTEGER NOT NULL DEFAULT 0,
            error_code TEXT, error_detail TEXT, created_at TEXT NOT NULL, started_at TEXT,
            updated_at TEXT NOT NULL, finished_at TEXT,
            UNIQUE(workspace_id, idempotency_key), UNIQUE(id, workspace_id),
            FOREIGN KEY(source_connection_id, workspace_id) REFERENCES source_connections(id, workspace_id))""",
        """CREATE TABLE IF NOT EXISTS import_checkpoints (
            job_id TEXT NOT NULL REFERENCES import_jobs(id), checkpoint_key TEXT NOT NULL,
            workspace_id TEXT NOT NULL REFERENCES workspaces(id), cursor_json TEXT NOT NULL,
            checksum TEXT, updated_at TEXT NOT NULL, PRIMARY KEY(job_id, checkpoint_key),
            FOREIGN KEY(job_id, workspace_id) REFERENCES import_jobs(id, workspace_id))""",
        """CREATE TABLE IF NOT EXISTS audit_events (
            id TEXT PRIMARY KEY, workspace_id TEXT REFERENCES workspaces(id), actor_account_id TEXT REFERENCES accounts(id),
            action TEXT NOT NULL, target_type TEXT, target_id TEXT, outcome TEXT NOT NULL,
            reason_code TEXT, metadata_json TEXT NOT NULL DEFAULT '{}', occurred_at TEXT NOT NULL)""",
        """CREATE TABLE IF NOT EXISTS workspace_entitlements (
            workspace_id TEXT PRIMARY KEY REFERENCES workspaces(id), plan_code TEXT NOT NULL,
            status TEXT NOT NULL, allowances_json TEXT NOT NULL DEFAULT '{}', effective_at TEXT NOT NULL,
            expires_at TEXT, updated_at TEXT NOT NULL)""",
        """CREATE TABLE IF NOT EXISTS usage_counters (
            workspace_id TEXT NOT NULL REFERENCES workspaces(id), metric TEXT NOT NULL,
            period_start TEXT NOT NULL, quantity BIGINT NOT NULL DEFAULT 0, estimated_cost_minor BIGINT NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL, PRIMARY KEY(workspace_id, metric, period_start))""",
        "CREATE INDEX IF NOT EXISTS memberships_account_state ON memberships(account_id, state)",
        "CREATE INDEX IF NOT EXISTS content_workspace_created ON content_items(workspace_id, source_created_at)",
        "CREATE INDEX IF NOT EXISTS media_workspace_content ON media_assets(workspace_id, content_item_id)",
        "CREATE INDEX IF NOT EXISTS jobs_workspace_state ON import_jobs(workspace_id, state, updated_at)",
        "CREATE INDEX IF NOT EXISTS audit_workspace_time ON audit_events(workspace_id, occurred_at)",
    ),
)

ACCOUNT_EXPERIENCE = Migration(
    2,
    "v2_account_workspace_experience",
    (
        """CREATE TABLE IF NOT EXISTS workspace_invitations (
            id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL REFERENCES workspaces(id),
            invited_by_account_id TEXT NOT NULL REFERENCES accounts(id), email_hint TEXT,
            intended_role TEXT NOT NULL CHECK (intended_role IN ('administrator','moderator','member')),
            admission_method TEXT NOT NULL, token_hash TEXT NOT NULL UNIQUE,
            state TEXT NOT NULL CHECK (state IN ('pending','accepted','revoked','expired')),
            expires_at TEXT NOT NULL, accepted_by_account_id TEXT REFERENCES accounts(id),
            accepted_at TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
            UNIQUE(id, workspace_id))""",
        """CREATE TABLE IF NOT EXISTS workspace_setup_steps (
            workspace_id TEXT NOT NULL REFERENCES workspaces(id), step_key TEXT NOT NULL,
            state TEXT NOT NULL CHECK (state IN ('not_started','in_progress','completed','blocked','skipped')),
            completed_by_account_id TEXT REFERENCES accounts(id), completed_at TEXT,
            metadata_json TEXT NOT NULL DEFAULT '{}', updated_at TEXT NOT NULL,
            PRIMARY KEY(workspace_id, step_key))""",
        "CREATE INDEX IF NOT EXISTS invitations_workspace_state ON workspace_invitations(workspace_id, state, expires_at)",
    ),
)

MIGRATIONS = (V2_FOUNDATION, ACCOUNT_EXPERIENCE)


def apply_migrations(connection: Any) -> None:
    connection.execute("""CREATE TABLE IF NOT EXISTS schema_migrations (
        version INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, applied_at TEXT NOT NULL)""")
    rows = connection.execute("SELECT version FROM schema_migrations").fetchall()
    applied = {int(row["version"] if uses_postgres() else row[0]) for row in rows}
    for migration in MIGRATIONS:
        if migration.version in applied:
            continue
        for statement in migration.statements:
            connection.execute(statement)
        connection.execute(
            query("INSERT INTO schema_migrations (version, name, applied_at) VALUES (?, ?, ?)"),
            (migration.version, migration.name, datetime.now(UTC).isoformat()),
        )
