from __future__ import annotations

import sqlite3
import json
import sys
import tempfile
import unittest
from urllib.parse import parse_qs, urlparse
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from authorization import AccessDenied, Principal
from database import connect_database, create_schema
from identity_provider import (
    AccountNotProvisioned,
    DatabaseAccountResolver,
    LocalTestIdentityProvider,
    NeonJWTIdentityProvider,
    VerifiedIdentity,
)
from job_security import InvalidJobIdentity, JobIdentity, authorise_job, sign_job, verify_job
from telegram_live import derive_webhook_secret
from v2_http import V2HTTPAdapter
from v2_store import ComvolyStore, utc_now


class V2FoundationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "foundation.db"
        self.environment = patch.dict("os.environ", {
            "DATABASE_URL": "", "COMVOLY_ENABLE_V2_SCHEMA": "true",
            "COMVOLY_ENABLE_V2_API": "true", "COMVOLY_V2_DEV_AUTH": "true",
            "COMVOLY_V2_DEV_SECRET": "a-long-local-development-secret"
        })
        self.environment.start()
        self.database_context = connect_database(self.path)
        self.database = self.database_context.__enter__()
        create_schema(self.database)
        self.store = ComvolyStore(self.database)
        self.owner_a = Principal(self.store.create_account("Owner A", "acct_a"))
        self.owner_b = Principal(self.store.create_account("Owner B", "acct_b"))
        self.member = Principal(self.store.create_account("Member", "acct_member"))
        self.workspace_a = self.store.create_workspace(self.owner_a, "Alpha", "alpha", "ws_a")
        self.workspace_b = self.store.create_workspace(self.owner_b, "Beta", "beta", "ws_b")
        self.context_a = self.store.context(self.owner_a, self.workspace_a, "manage_sources")
        self.context_b = self.store.context(self.owner_b, self.workspace_b, "manage_sources")
        now = utc_now()
        for workspace, source in (("ws_a", "src_a"), ("ws_b", "src_b")):
            self.database.execute("""INSERT INTO source_connections
                (id, workspace_id, provider, external_community_id, display_name, state, created_at, updated_at)
                VALUES (?, ?, 'fixture', ?, ?, 'connected', ?, ?)""",
                (source, workspace, f"external_{source}", source, now, now))

    def tearDown(self) -> None:
        self.database_context.__exit__(None, None, None)
        self.environment.stop()
        self.temp.cleanup()

    def _add_content(self) -> tuple[str, str]:
        item_a = self.store.add_content(self.context_a, "src_a", "1", "alpha secret", utc_now())
        item_b = self.store.add_content(self.context_b, "src_b", "1", "beta secret", utc_now())
        return item_a, item_b

    def test_migrations_are_versioned_idempotent_and_preserve_legacy_schema(self) -> None:
        create_schema(self.database)
        tables = {row[0] for row in self.database.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertTrue({"communities", "accounts", "workspaces", "content_items", "import_jobs", "audit_events"}.issubset(tables))
        migrations = self.database.execute("SELECT version, name FROM schema_migrations ORDER BY version").fetchall()
        self.assertEqual(
            [(1, "v2_secure_multi_community_foundation"),
             (2, "v2_account_workspace_experience"),
             (3, "v2_telegram_live_pilot"),
             (4, "v2_telegram_global_webhook_binding"),
             (5, "v2_import_review_activation")],
            [tuple(row) for row in migrations],
        )

    def test_account_can_hold_multiple_workspace_memberships(self) -> None:
        self.store.add_membership(self.context_a, self.member.account_id, "member")
        self.store.add_membership(self.context_b, self.member.account_id, "member")
        workspaces = self.store.list_workspaces(self.member)
        self.assertEqual({"ws_a", "ws_b"}, {row["id"] for row in workspaces})

    def test_unrelated_account_cannot_authorise_workspace(self) -> None:
        with self.assertRaises(AccessDenied):
            self.store.context(self.owner_b, self.workspace_a, "view_evidence")

    def test_member_cannot_import_or_manage_sources(self) -> None:
        self.store.add_membership(self.context_a, self.member.account_id, "member")
        with self.assertRaises(AccessDenied):
            self.store.context(self.member, self.workspace_a, "import_history")
        with self.assertRaises(AccessDenied):
            self.store.context(self.member, self.workspace_a, "manage_sources")

    def test_suspended_account_cannot_use_active_membership(self) -> None:
        self.store.add_membership(self.context_a, self.member.account_id, "member")
        self.database.execute("UPDATE accounts SET status = 'suspended' WHERE id = 'acct_member'")
        with self.assertRaises(AccessDenied):
            self.store.context(self.member, self.workspace_a, "view_evidence")

    def test_limited_administrator_capability_requires_explicit_override(self) -> None:
        self.store.add_membership(self.context_a, self.member.account_id, "administrator")
        with self.assertRaises(AccessDenied):
            self.store.context(self.member, self.workspace_a, "export_workspace")
        self.database.execute("""INSERT INTO capability_overrides
            (workspace_id, account_id, capability, allowed, granted_by_account_id, created_at)
            VALUES ('ws_a', 'acct_member', 'export_workspace', 1, 'acct_a', ?)""", (utc_now(),))
        context = self.store.context(self.member, self.workspace_a, "export_workspace")
        self.assertEqual("administrator", context.role)

    def test_search_and_direct_content_lookup_cannot_cross_workspace(self) -> None:
        item_a, item_b = self._add_content()
        read_a = self.store.context(self.owner_a, self.workspace_a, "use_intelligence")
        evidence_a = self.store.context(self.owner_a, self.workspace_a, "view_evidence")
        self.assertEqual([item_a], [row["id"] for row in self.store.search_content(read_a, "secret")])
        self.assertIsNone(self.store.get_content(evidence_a, item_b))

    def test_jobs_and_checkpoints_reject_cross_workspace_sources_and_ids(self) -> None:
        import_a = self.store.context(self.owner_a, self.workspace_a, "import_history")
        import_b = self.store.context(self.owner_b, self.workspace_b, "import_history")
        with self.assertRaises(ValueError):
            self.store.create_import_job(import_a, "src_b", "history", "wrong-source")
        job_b = self.store.create_import_job(import_b, "src_b", "history", "beta-history")
        with self.assertRaises(ValueError):
            self.store.save_checkpoint(import_a, job_b, "page", {"cursor": 2})

    def test_media_lookup_cannot_cross_workspace(self) -> None:
        item_a, item_b = self._add_content()
        now = utc_now()
        self.database.execute("""INSERT INTO media_assets
            (id, workspace_id, content_item_id, media_type, source_availability, download_state,
             safety_state, extraction_state, retention_state, created_at, updated_at)
             VALUES ('media_b', 'ws_b', ?, 'image/png', 'available', 'stored', 'clean', 'pending', 'active', ?, ?)""",
             (item_b, now, now))
        evidence_a = self.store.context(self.owner_a, self.workspace_a, "view_evidence")
        self.assertEqual([], self.store.list_media(evidence_a, item_b))
        self.assertEqual([], self.store.list_media(evidence_a, item_a))

    def test_database_rejects_cross_workspace_content_reference(self) -> None:
        with self.assertRaises(sqlite3.IntegrityError):
            self.database.execute("""INSERT INTO content_items
                (id, workspace_id, source_connection_id, external_item_id, item_type,
                 source_created_at, ingestion_method, ingested_at)
                 VALUES ('bad', 'ws_a', 'src_b', 'bad', 'message', ?, 'test', ?)""", (utc_now(), utc_now()))

    def test_identity_adapter_is_closed_by_default(self) -> None:
        identity = VerifiedIdentity("test", "subject-1", "A Person", {})
        self.assertIsNone(LocalTestIdentityProvider().verify_session("unknown"))
        self.assertEqual(identity, LocalTestIdentityProvider({"token": identity}).verify_session("token"))

    def test_neon_identity_verification_is_fail_closed(self) -> None:
        provider = NeonJWTIdentityProvider(
            "https://auth.example.test/.well-known/jwks.json",
            "https://auth.example.test",
            decoder=lambda token: {"sub": "neon-user", "email": "member@example.test",
                                   "iss": "https://auth.example.test/"}
            if token == "valid" else (_ for _ in ()).throw(ValueError("invalid")),
        )
        self.assertEqual("neon-user", provider.verify_session("valid").subject)
        self.assertIsNone(provider.verify_session("invalid"))
        self.assertIsNone(provider.verify_session(""))

        wrong_issuer = NeonJWTIdentityProvider(
            "https://auth.example.test/.well-known/jwks.json",
            "https://auth.example.test",
            decoder=lambda token: {"sub": "neon-user", "iss": "https://attacker.example"},
        )
        self.assertIsNone(wrong_issuer.verify_session("valid"))

    def test_registered_neon_account_starts_with_zero_workspace_access(self) -> None:
        identity = VerifiedIdentity("neon", "new-user", "New Member",
                                    {"email": "new@example.test", "email_verified": True})
        provider = LocalTestIdentityProvider({"neon-token": identity})
        resolver = DatabaseAccountResolver(self.database, allow_registration=True)
        adapter = V2HTTPAdapter(self.database, provider, resolver)

        status, session = adapter.dispatch(
            "GET", "/v2/session", {}, {"Authorization": "Bearer neon-token"})

        self.assertEqual(200, status)
        self.assertEqual([], session["workspaces"])
        account_id = session["account_id"]
        self.assertEqual(0, self.database.execute(
            "SELECT COUNT(*) FROM memberships WHERE account_id=?", (account_id,)).fetchone()[0])
        self.assertEqual(404, adapter.dispatch(
            "GET", "/v2/workspaces/ws_a", {}, {"Authorization": "Bearer neon-token"})[0])
        self.assertEqual(403, adapter.dispatch(
            "POST", "/v2/workspaces", {"name": "Unapproved", "handle": "unapproved"},
            {"Authorization": "Bearer neon-token"})[0])

    def test_unapproved_valid_identity_is_denied_when_registration_is_closed(self) -> None:
        identity = VerifiedIdentity("neon", "unapproved", "Unapproved", {})
        adapter = V2HTTPAdapter(
            self.database,
            LocalTestIdentityProvider({"valid-token": identity}),
            DatabaseAccountResolver(self.database, allow_registration=False),
        )
        status, _ = adapter.dispatch(
            "GET", "/v2/session", {}, {"Authorization": "Bearer valid-token"})
        self.assertEqual(403, status)
        with self.assertRaises(AccountNotProvisioned):
            DatabaseAccountResolver(self.database, False).resolve_account(identity)

    def test_export_manifest_contains_only_authorised_workspace(self) -> None:
        self._add_content()
        export_a = self.store.context(self.owner_a, self.workspace_a, "export_workspace")
        manifest = self.store.export_manifest(export_a)
        self.assertEqual("ws_a", manifest["workspace"]["id"])
        self.assertEqual(["src_a"], [source["id"] for source in manifest["sources"]])
        self.assertEqual(1, manifest["content_count"])

    def test_members_cannot_export_workspace(self) -> None:
        self.store.add_membership(self.context_a, self.member.account_id, "member")
        with self.assertRaises(AccessDenied):
            self.store.context(self.member, self.workspace_a, "export_workspace")

    def test_usage_and_audit_reads_are_workspace_scoped(self) -> None:
        usage_a = self.store.context(self.owner_a, self.workspace_a, "view_usage")
        usage_b = self.store.context(self.owner_b, self.workspace_b, "view_usage")
        self.store.increment_usage(usage_a, "ai_tokens", "2026-07-01", 50, 2)
        self.store.increment_usage(usage_b, "ai_tokens", "2026-07-01", 900, 40)
        self.assertEqual(50, self.store.get_usage(usage_a, "2026-07-01")[0]["quantity"])
        audit_a = self.store.context(self.owner_a, self.workspace_a, "review_concerns")
        self.assertTrue(all(event["target_id"] != "ws_b" for event in self.store.list_audit_events(audit_a)))

    def test_job_identity_is_signed_expiring_and_bound_to_database_scope(self) -> None:
        context = self.store.context(self.owner_a, self.workspace_a, "import_history")
        job_id = self.store.create_import_job(context, "src_a", "history", "signed-job")
        secret = "a-secure-internal-job-secret-value"
        token = sign_job(JobIdentity(job_id, "ws_a", "src_a", 2_000), secret)
        verified = verify_job(token, secret, now=1_000)
        authorise_job(self.database, verified)
        with self.assertRaises(InvalidJobIdentity):
            verify_job(token + "tampered", secret, now=1_000)
        with self.assertRaises(InvalidJobIdentity):
            verify_job(token, secret, now=2_001)
        with self.assertRaises(InvalidJobIdentity):
            authorise_job(self.database, JobIdentity(job_id, "ws_b", "src_a", 2_000))

    def test_http_adapter_requires_verified_session_and_hides_other_workspace(self) -> None:
        adapter = V2HTTPAdapter(self.database)
        self.assertEqual(401, adapter.dispatch("GET", "/v2/session", {}, {})[0])
        headers = {"Authorization": "Bearer a-long-local-development-secret", "X-Comvoly-Account-Id": "acct_a"}
        status, session = adapter.dispatch("GET", "/v2/session", {}, headers)
        self.assertEqual(200, status)
        self.assertEqual(["ws_a"], [item["id"] for item in session["workspaces"]])
        self.assertEqual(404, adapter.dispatch("GET", "/v2/workspaces/ws_b", {}, headers)[0])

    def test_http_adapter_is_closed_when_api_gate_is_disabled(self) -> None:
        adapter = V2HTTPAdapter(self.database)
        headers = {"Authorization": "Bearer a-long-local-development-secret", "X-Comvoly-Account-Id": "acct_a"}
        with patch.dict("os.environ", {"COMVOLY_ENABLE_V2_API": "false"}):
            self.assertEqual(404, adapter.dispatch("GET", "/v2/session", {}, headers)[0])

    def test_invitation_acceptance_adds_workspace_without_exposing_token_in_database(self) -> None:
        adapter = V2HTTPAdapter(self.database)
        owner_headers = {"Authorization": "Bearer a-long-local-development-secret", "X-Comvoly-Account-Id": "acct_a"}
        member_headers = {"Authorization": "Bearer a-long-local-development-secret", "X-Comvoly-Account-Id": "acct_member"}
        status, invitation = adapter.dispatch("POST", "/v2/workspaces/ws_a/invitations", {"role": "member"}, owner_headers)
        self.assertEqual(201, status)
        stored = self.database.execute("SELECT token_hash FROM workspace_invitations WHERE id=?", (invitation["invitation_id"],)).fetchone()
        self.assertNotEqual(invitation["token"], stored[0])
        status, accepted = adapter.dispatch("POST", "/v2/invitations/accept", {"token": invitation["token"]}, member_headers)
        self.assertEqual(200, status)
        self.assertEqual("ws_a", accepted["workspace_id"])
        session = adapter.dispatch("GET", "/v2/session", {}, member_headers)[1]
        self.assertEqual(["ws_a"], [item["id"] for item in session["workspaces"]])

    def test_workspace_creation_initialises_owner_setup_steps(self) -> None:
        adapter = V2HTTPAdapter(self.database)
        headers = {"Authorization": "Bearer a-long-local-development-secret", "X-Comvoly-Account-Id": "acct_a"}
        status, created = adapter.dispatch("POST", "/v2/workspaces", {"name": "Gamma", "handle": "gamma"}, headers)
        self.assertEqual(201, status)
        count = self.database.execute("SELECT COUNT(*) FROM workspace_setup_steps WHERE workspace_id=?", (created["workspace_id"],)).fetchone()[0]
        self.assertEqual(5, count)
        duplicate_status = adapter.dispatch("POST", "/v2/workspaces",
            {"name": "Another Gamma", "handle": "gamma"}, headers)[0]
        self.assertEqual(409, duplicate_status)

    def test_workspace_overview_contains_only_scoped_setup_sources_and_imports(self) -> None:
        adapter = V2HTTPAdapter(self.database)
        owner_headers = {"Authorization": "Bearer a-long-local-development-secret", "X-Comvoly-Account-Id": "acct_a"}
        status, overview = adapter.dispatch("GET", "/v2/workspaces/ws_a", {}, owner_headers)
        self.assertEqual(200, status)
        self.assertEqual(["src_a"], [source["id"] for source in overview["sources"]])
        self.assertEqual(5, len(overview["setup_steps"]))
        self.assertEqual([], overview["imports"])
        self.assertNotIn("src_b", repr(overview))

    def test_owner_can_plan_source_and_complete_setup_step(self) -> None:
        adapter = V2HTTPAdapter(self.database)
        owner_headers = {"Authorization": "Bearer a-long-local-development-secret", "X-Comvoly-Account-Id": "acct_a"}
        status, source = adapter.dispatch("POST", "/v2/workspaces/ws_a/sources",
            {"provider": "telegram", "display_name": "Alpha Telegram"}, owner_headers)
        self.assertEqual(201, status)
        row = self.database.execute("SELECT workspace_id, state FROM source_connections WHERE id=?",
                                    (source["source_id"],)).fetchone()
        self.assertEqual(("ws_a", "draft"), tuple(row))
        status, step = adapter.dispatch("POST", "/v2/workspaces/ws_a/setup/community_details",
            {"state": "completed"}, owner_headers)
        self.assertEqual((200, "completed"), (status, step["state"]))

    def test_member_cannot_manage_owner_setup_or_sources(self) -> None:
        self.store.add_membership(self.context_a, self.member.account_id, "member")
        adapter = V2HTTPAdapter(self.database)
        member_headers = {"Authorization": "Bearer a-long-local-development-secret", "X-Comvoly-Account-Id": "acct_member"}
        self.assertEqual(404, adapter.dispatch("POST", "/v2/workspaces/ws_a/sources",
            {"provider": "discord", "display_name": "Forbidden"}, member_headers)[0])
        self.assertEqual(404, adapter.dispatch("POST", "/v2/workspaces/ws_a/setup/community_details",
            {"state": "completed"}, member_headers)[0])

    def test_managed_identity_workspace_creation_remains_environment_gated(self) -> None:
        identity = VerifiedIdentity("neon", "owner-subject", "Owner", {"sub": "owner-subject"})
        provider = LocalTestIdentityProvider({"owner-token": identity})
        resolver = DatabaseAccountResolver(self.database, allow_registration=True)
        adapter = V2HTTPAdapter(self.database, provider, resolver)
        headers = {"Authorization": "Bearer owner-token"}
        with patch.dict("os.environ", {"COMVOLY_V2_ALLOW_WORKSPACE_CREATION": "false"}):
            self.assertEqual(403, adapter.dispatch("POST", "/v2/workspaces",
                {"name": "Owner workspace", "handle": "owner-workspace"}, headers)[0])
        with patch.dict("os.environ", {"COMVOLY_V2_ALLOW_WORKSPACE_CREATION": "true"}):
            status, created = adapter.dispatch("POST", "/v2/workspaces",
                {"name": "Owner workspace", "handle": "owner-workspace"}, headers)
            self.assertEqual(201, status)
            self.assertTrue(created["workspace_id"].startswith("ws_"))

    def test_owner_can_safely_delete_workspace_but_members_and_other_tenants_cannot(self) -> None:
        self._add_content()
        self.store.add_membership(self.context_a, self.member.account_id, "member")
        adapter = V2HTTPAdapter(self.database)
        owner_headers = {"Authorization": "Bearer a-long-local-development-secret",
                         "X-Comvoly-Account-Id": "acct_a"}
        member_headers = {"Authorization": "Bearer a-long-local-development-secret",
                          "X-Comvoly-Account-Id": "acct_member"}
        other_headers = {"Authorization": "Bearer a-long-local-development-secret",
                         "X-Comvoly-Account-Id": "acct_b"}
        path = "/v2/workspaces/ws_a"
        self.assertEqual(404, adapter.dispatch("DELETE", path,
            {"confirm_name": "Alpha"}, member_headers)[0])
        self.assertEqual(404, adapter.dispatch("DELETE", path,
            {"confirm_name": "Alpha"}, other_headers)[0])
        self.assertEqual(400, adapter.dispatch("DELETE", path,
            {"confirm_name": "wrong"}, owner_headers)[0])

        status, result = adapter.dispatch("DELETE", path,
            {"confirm_name": "Alpha"}, owner_headers)
        self.assertEqual((200, "deleted", True),
                         (status, result["state"], result["recoverable"]))
        self.assertEqual([], adapter.dispatch("GET", "/v2/session", {}, owner_headers)[1]["workspaces"])
        self.assertEqual(404, adapter.dispatch("GET", path, {}, owner_headers)[0])
        self.assertEqual("revoked", self.database.execute(
            "SELECT state FROM source_connections WHERE id='src_a'").fetchone()[0])
        self.assertEqual(0, self.database.execute(
            "SELECT COUNT(*) FROM memberships WHERE workspace_id='ws_a' AND state='active'").fetchone()[0])
        self.assertEqual(1, self.database.execute(
            "SELECT COUNT(*) FROM content_items WHERE workspace_id='ws_a'").fetchone()[0])

    def test_telegram_export_import_is_resumable_idempotent_and_workspace_scoped(self) -> None:
        adapter = V2HTTPAdapter(self.database)
        owner_headers = {"Authorization": "Bearer a-long-local-development-secret", "X-Comvoly-Account-Id": "acct_a"}
        member_headers = {"Authorization": "Bearer a-long-local-development-secret", "X-Comvoly-Account-Id": "acct_member"}
        document = json.loads((Path(__file__).parent / "fixtures" / "telegram_small.json").read_text(encoding="utf-8"))
        status, summary = adapter.dispatch("POST", "/v2/workspaces/ws_a/telegram/preview",
                                           {"export": document}, owner_headers)
        self.assertEqual(200, status)
        status, started = adapter.dispatch("POST", "/v2/workspaces/ws_a/telegram/imports",
            {"summary": summary, "idempotency_key": "fixture-import"}, owner_headers)
        self.assertEqual(201, status)
        path = f"/v2/workspaces/ws_a/telegram/imports/{started['job_id']}/chunks"
        payload = {"chunk_index": 0, "messages": document["messages"]}
        status, progress = adapter.dispatch("POST", path, payload, owner_headers)
        self.assertEqual((200, 3, False), (status, progress["progress_current"], progress["duplicate"]))
        status, replay = adapter.dispatch("POST", path, payload, owner_headers)
        self.assertEqual((200, 3, True), (status, replay["progress_current"], replay["duplicate"]))
        content = self.database.execute("SELECT external_item_id, workspace_id FROM content_items WHERE source_connection_id=? ORDER BY external_item_id",
                                        (started["source_id"],)).fetchall()
        self.assertEqual([("2", "ws_a"), ("3", "ws_a"), ("4", "ws_a")], [tuple(row) for row in content])
        complete_path = f"/v2/workspaces/ws_a/telegram/imports/{started['job_id']}/complete"
        status, completed = adapter.dispatch("POST", complete_path, {}, owner_headers)
        self.assertEqual((200, "owner_review"), (status, completed["state"]))
        self.store.add_membership(self.context_a, self.member.account_id, "member")
        self.assertEqual(404, adapter.dispatch("POST", "/v2/workspaces/ws_a/telegram/preview",
            {"export": document}, member_headers)[0])
        self.assertEqual(404, adapter.dispatch("POST", f"/v2/workspaces/ws_b/telegram/imports/{started['job_id']}/complete",
            {}, owner_headers)[0])

    def test_streaming_import_resumes_reports_health_and_preserves_live_source(self) -> None:
        self.database.execute("""UPDATE source_connections SET provider='telegram', state='connected',
            health='healthy' WHERE id='src_a'""")
        adapter = V2HTTPAdapter(self.database)
        owner_headers = {"Authorization": "Bearer a-long-local-development-secret",
                         "X-Comvoly-Account-Id": "acct_a"}
        other_headers = {"Authorization": "Bearer a-long-local-development-secret",
                         "X-Comvoly-Account-Id": "acct_b"}
        document = json.loads((Path(__file__).parent / "fixtures" / "telegram_small.json").read_text(encoding="utf-8"))
        summary = adapter.dispatch("POST", "/v2/workspaces/ws_a/telegram/preview",
            {"export": document}, owner_headers)[1]
        start_payload = {"summary": {**summary, "message_count": None}, "source_id": "src_a",
                         "idempotency_key": "stream-file-fingerprint", "bytes_total": 4_000_000_000}
        status, started = adapter.dispatch("POST", "/v2/workspaces/ws_a/telegram/imports",
                                           start_payload, owner_headers)
        self.assertEqual((201, False, None, 4_000_000_000),
                         (status, started["resumed"], started["progress_total"], started["bytes_total"]))
        chunk_path = f"/v2/workspaces/ws_a/telegram/imports/{started['job_id']}/chunks"
        progress = adapter.dispatch("POST", chunk_path,
            {"chunk_index": 0, "messages": document["messages"], "bytes_processed": 12345}, owner_headers)[1]
        self.assertEqual((3, 12345), (progress["progress_current"], progress["bytes_current"]))

        resumed = adapter.dispatch("POST", "/v2/workspaces/ws_a/telegram/imports",
                                   start_payload, owner_headers)[1]
        self.assertEqual((started["job_id"], True, [0], 3),
                         (resumed["job_id"], resumed["resumed"], resumed["completed_chunks"],
                          resumed["progress_current"]))
        status_path = f"/v2/workspaces/ws_a/telegram/imports/{started['job_id']}"
        self.assertEqual([0], adapter.dispatch("GET", status_path, {}, owner_headers)[1]["completed_chunks"])
        self.assertEqual(404, adapter.dispatch("GET",
            f"/v2/workspaces/ws_b/telegram/imports/{started['job_id']}", {}, other_headers)[0])

        complete_path = f"{status_path}/complete"
        completed = adapter.dispatch("POST", complete_path, {"summary": summary}, owner_headers)[1]
        self.assertEqual(("owner_review", 3), (completed["state"], completed["progress_total"]))
        self.assertEqual(("connected", "healthy"), tuple(self.database.execute(
            "SELECT state, health FROM source_connections WHERE id='src_a'").fetchone()))

        health = adapter.dispatch("GET", "/v2/workspaces/ws_a/ingestion", {}, owner_headers)[1]
        source = health["sources"][0]
        self.assertEqual((3, 0, 3), (source["stored_message_count"],
                                     source["live_message_count"], source["historical_message_count"]))
        self.store.add_membership(self.context_a, self.member.account_id, "member")
        member_headers = {"Authorization": "Bearer a-long-local-development-secret",
                          "X-Comvoly-Account-Id": "acct_member"}
        self.assertEqual(404, adapter.dispatch("GET", "/v2/workspaces/ws_a/ingestion",
                                               {}, member_headers)[0])
        self.assertEqual(404, adapter.dispatch("GET", "/v2/workspaces/ws_b/ingestion",
                                               {}, owner_headers)[0])

    def test_import_review_accept_cancel_restart_and_mixed_retrieval_are_isolated(self) -> None:
        self.database.execute("UPDATE source_connections SET provider='telegram' WHERE id IN ('src_a','src_b')")
        live_id = self.store.add_content(self.context_a, "src_a", "live-1",
                                         "A current decision from the live chat", utc_now())
        self.database.execute("UPDATE content_items SET ingestion_method='telegram_bot_webhook' WHERE id=?",
                              (live_id,))
        adapter = V2HTTPAdapter(self.database)
        owner_headers = {"Authorization": "Bearer a-long-local-development-secret",
                         "X-Comvoly-Account-Id": "acct_a"}
        other_headers = {"Authorization": "Bearer a-long-local-development-secret",
                         "X-Comvoly-Account-Id": "acct_b"}
        document = json.loads((Path(__file__).parent / "fixtures" / "telegram_small.json").read_text(encoding="utf-8"))
        summary = adapter.dispatch("POST", "/v2/workspaces/ws_a/telegram/preview",
                                   {"export": document}, owner_headers)[1]
        started = adapter.dispatch("POST", "/v2/workspaces/ws_a/telegram/imports",
            {"summary": summary, "source_id": "src_a", "idempotency_key": "review-a"}, owner_headers)[1]
        base = f"/v2/workspaces/ws_a/telegram/imports/{started['job_id']}"
        adapter.dispatch("POST", f"{base}/chunks", {"chunk_index": 0, "messages": document["messages"]}, owner_headers)
        adapter.dispatch("POST", f"{base}/complete", {"summary": summary}, owner_headers)

        before = adapter.dispatch("POST", "/v2/workspaces/ws_a/intelligence/ask",
                                  {"question": "What decision was made?"}, owner_headers)[1]
        self.assertEqual({"telegram_bot_webhook"},
                         {item["ingestion_method"] for item in before["citations"]})
        status, review = adapter.dispatch("GET", f"{base}/review", {}, owner_headers)
        self.assertEqual((200, True, 3, 3), (status, review["can_accept"],
                         review["inventory"]["message_count"], len(review["samples"])))
        self.assertEqual(3, review["summary"]["message_count"])
        evidence_context = self.store.context(self.owner_a, self.workspace_a, "view_evidence")
        retrieval_context = self.store.context(self.owner_a, self.workspace_a, "use_intelligence")
        staged_id = review["samples"][0]["id"]
        self.assertIsNone(self.store.get_content(evidence_context, staged_id))
        self.assertEqual([], self.store.search_content(retrieval_context, "later decision"))
        self.assertEqual(404, adapter.dispatch("GET",
            f"/v2/workspaces/ws_b/telegram/imports/{started['job_id']}/review", {}, other_headers)[0])
        self.store.add_membership(self.context_a, self.member.account_id, "member")
        member_headers = {"Authorization": "Bearer a-long-local-development-secret",
                          "X-Comvoly-Account-Id": "acct_member"}
        self.assertEqual(404, adapter.dispatch("GET", f"{base}/review", {}, member_headers)[0])

        accepted = adapter.dispatch("POST", f"{base}/accept", {}, owner_headers)[1]
        self.assertEqual(("active", False), (accepted["state"], accepted["can_accept"]))
        self.assertIsNotNone(self.store.get_content(evidence_context, staged_id))
        after = adapter.dispatch("POST", "/v2/workspaces/ws_a/intelligence/ask",
                                 {"question": "What decision was made?"}, owner_headers)[1]
        self.assertEqual({"telegram_bot_webhook", "telegram_desktop_export"},
                         {item["ingestion_method"] for item in after["citations"]})
        self.assertEqual(409, adapter.dispatch("POST", f"{base}/cancel", {}, owner_headers)[0])

        repeated = adapter.dispatch("POST", "/v2/workspaces/ws_a/telegram/imports",
            {"summary": summary, "source_id": "src_a", "idempotency_key": "review-a-changed-file"}, owner_headers)[1]
        repeated_base = f"/v2/workspaces/ws_a/telegram/imports/{repeated['job_id']}"
        adapter.dispatch("POST", f"{repeated_base}/chunks",
                         {"chunk_index": 0, "messages": document["messages"]}, owner_headers)
        repeated_review = adapter.dispatch("GET", f"{repeated_base}/review", {}, owner_headers)[1]
        self.assertEqual((0, 3), (repeated_review["inventory"]["message_count"],
                                 repeated_review["inventory"]["overlap_count"]))
        adapter.dispatch("POST", f"{repeated_base}/cancel", {}, owner_headers)
        still_available = adapter.dispatch("POST", "/v2/workspaces/ws_a/intelligence/ask",
                                           {"question": "What decision was made?"}, owner_headers)[1]
        self.assertEqual({"telegram_bot_webhook", "telegram_desktop_export"},
                         {item["ingestion_method"] for item in still_available["citations"]})

        live_b = self.store.add_content(self.context_b, "src_b", "live-b", "Keep this live message", utc_now())
        self.database.execute("UPDATE content_items SET ingestion_method='telegram_bot_webhook' WHERE id=?", (live_b,))
        started_b = adapter.dispatch("POST", "/v2/workspaces/ws_b/telegram/imports",
            {"summary": summary, "source_id": "src_b", "idempotency_key": "review-b"}, other_headers)[1]
        base_b = f"/v2/workspaces/ws_b/telegram/imports/{started_b['job_id']}"
        adapter.dispatch("POST", f"{base_b}/chunks", {"chunk_index": 0, "messages": document["messages"]}, other_headers)
        cancelled = adapter.dispatch("POST", f"{base_b}/cancel", {}, other_headers)[1]
        self.assertEqual(("cancelled", 0), (cancelled["state"], cancelled["inventory"]["message_count"]))
        self.assertEqual(1, self.database.execute("SELECT COUNT(*) FROM content_items WHERE id=?", (live_b,)).fetchone()[0])
        restarted = adapter.dispatch("POST", f"{base_b}/restart", {}, other_headers)[1]
        self.assertEqual(("uploading", 0, [], 1), (restarted["state"], restarted["progress_current"],
                         restarted["completed_chunks"], restarted["attempt"]))

    def test_telegram_live_webhook_is_secret_verified_idempotent_and_workspace_bound(self) -> None:
        self.database.execute("UPDATE source_connections SET provider='telegram' WHERE id='src_a'")
        self.database.execute("UPDATE source_connections SET provider='telegram' WHERE id='src_b'")
        owner_headers = {"Authorization": "Bearer a-long-local-development-secret",
                         "X-Comvoly-Account-Id": "acct_a"}
        other_headers = {"Authorization": "Bearer a-long-local-development-secret",
                         "X-Comvoly-Account-Id": "acct_b"}
        master = "telegram-test-master-key-longer-than-thirty-two-characters"
        with patch.dict("os.environ", {
            "COMVOLY_TELEGRAM_WEBHOOK_MASTER_KEY": master,
            "COMVOLY_TELEGRAM_BOT_USER_ID": "9001",
            "COMVOLY_TELEGRAM_BOT_USERNAME": "ComvolyTestBot",
            "COMVOLY_PUBLIC_API_URL": "https://api.dev.example.test",
        }):
            adapter = V2HTTPAdapter(self.database)
            status, prepared = adapter.dispatch("POST", "/v2/workspaces/ws_a/telegram/live/prepare",
                {"source_id": "src_a"}, owner_headers)
            self.assertEqual((200, "awaiting_bot"), (status, prepared["state"]))
            self.assertNotIn("secret", repr(prepared).lower())
            self.assertEqual(404, adapter.dispatch("POST", "/v2/workspaces/ws_b/telegram/live/prepare",
                {"source_id": "src_a"}, other_headers)[0])
            prepared_b = adapter.dispatch("POST", "/v2/workspaces/ws_b/telegram/live/prepare",
                {"source_id": "src_b"}, other_headers)[1]

            webhook = "/v2/telegram/webhooks"
            self.assertEqual(401, adapter.dispatch("POST", webhook, {"update_id": 1},
                {"X-Telegram-Bot-Api-Secret-Token": "wrong"})[0])
            self.assertEqual(0, self.database.execute(
                "SELECT COUNT(*) FROM telegram_webhook_events").fetchone()[0])
            secret = derive_webhook_secret(master)
            code = parse_qs(urlparse(prepared["install_url"]).query)["startgroup"][0]
            activation = {"update_id": 2, "message": {"message_id": 1,
                "date": 1785484700, "chat": {"id": -10042, "type": "supergroup",
                "title": "Pilot Group"}, "text": f"/start {code}"}}
            self.assertEqual("verifying", adapter.dispatch("POST", webhook, activation,
                {"X-Telegram-Bot-Api-Secret-Token": secret})[1]["state"])
            bindings = self.database.execute("""SELECT source_connection_id, expected_chat_id
                FROM telegram_connection_configs ORDER BY source_connection_id""").fetchall()
            self.assertEqual([("src_a", "-10042"), ("src_b", "pending:src_b")],
                             [tuple(row) for row in bindings])
            self.assertNotEqual(code, parse_qs(urlparse(prepared_b["install_url"]).query)["startgroup"][0])
            membership = {"update_id": 2, "my_chat_member": {"chat": {"id": -10042},
                "new_chat_member": {"status": "administrator"}}}
            membership["update_id"] = 3
            self.assertEqual("verifying", adapter.dispatch("POST", webhook, membership,
                {"X-Telegram-Bot-Api-Secret-Token": secret})[1]["state"])
            message = {"update_id": 4, "message": {"message_id": 77, "date": 1785484800,
                "chat": {"id": -10042, "title": "Pilot Group"},
                "from": {"id": 123, "first_name": "Pilot"}, "text": "alpha live advice"}}
            response = adapter.dispatch("POST", webhook, message,
                {"X-Telegram-Bot-Api-Secret-Token": secret})
            self.assertEqual((200, "connected"), (response[0], response[1]["state"]))
            duplicate = adapter.dispatch("POST", webhook, message,
                {"X-Telegram-Bot-Api-Secret-Token": secret})
            self.assertTrue(duplicate[1]["duplicate"])
            stored = self.database.execute("""SELECT workspace_id, body_text, ingestion_method
                FROM content_items WHERE source_connection_id='src_a' AND external_item_id='77'""").fetchone()
            self.assertEqual(("ws_a", "alpha live advice", "telegram_bot_webhook"), tuple(stored))
            source = self.database.execute("SELECT state, health FROM source_connections WHERE id='src_a'").fetchone()
            self.assertEqual(("connected", "healthy"), tuple(source))

    def test_telegram_connect_is_one_action_reuses_source_and_enforces_workspace_access(self) -> None:
        owner_headers = {"Authorization": "Bearer a-long-local-development-secret",
                         "X-Comvoly-Account-Id": "acct_a"}
        member_headers = {"Authorization": "Bearer a-long-local-development-secret",
                          "X-Comvoly-Account-Id": "acct_member"}
        with patch.dict("os.environ", {
            "COMVOLY_TELEGRAM_WEBHOOK_MASTER_KEY": "telegram-test-master-key-longer-than-thirty-two-characters",
            "COMVOLY_TELEGRAM_BOT_USER_ID": "9001",
            "COMVOLY_TELEGRAM_BOT_USERNAME": "ComvolyTestBot",
            "COMVOLY_PUBLIC_API_URL": "https://api.dev.example.test",
        }):
            adapter = V2HTTPAdapter(self.database)
            path = "/v2/workspaces/ws_a/telegram/connect"
            status, result = adapter.dispatch("POST", path, {"display_name": "Pilot Group"}, owner_headers)
            self.assertEqual((200, "awaiting_bot"), (status, result["state"]))
            self.assertIn("startgroup=", result["install_url"])
            source_id = result["source_id"]
            status, repeated = adapter.dispatch("POST", path, {"display_name": "Renamed Group"}, owner_headers)
            self.assertEqual((200, source_id), (status, repeated["source_id"]))
            rows = self.database.execute("""SELECT id, display_name FROM source_connections
                WHERE workspace_id='ws_a' AND provider='telegram'""").fetchall()
            self.assertEqual([(source_id, "Renamed Group")], [tuple(row) for row in rows])
            self.store.add_membership(self.context_a, self.member.account_id, "member")
            self.assertEqual(404, adapter.dispatch("POST", path,
                {"display_name": "Forbidden"}, member_headers)[0])
            self.assertEqual(404, adapter.dispatch("POST", "/v2/workspaces/ws_b/telegram/connect",
                {"display_name": "Wrong workspace"}, owner_headers)[0])

            disconnect = f"/v2/workspaces/ws_a/telegram/disconnect/{source_id}"
            status, removed = adapter.dispatch("POST", disconnect, {}, owner_headers)
            self.assertEqual((200, "revoked", True),
                             (status, removed["state"], removed["knowledge_retained"]))
            source_state = self.database.execute(
                "SELECT state FROM source_connections WHERE id=?", (source_id,)).fetchone()[0]
            binding = self.database.execute(
                """SELECT activation_state, expected_chat_id FROM telegram_connection_configs
                    WHERE source_connection_id=?""", (source_id,)).fetchone()
            self.assertEqual(("revoked", "revoked", f"revoked:{source_id}"),
                             (source_state, binding[0], binding[1]))
            self.assertEqual(404, adapter.dispatch("POST", disconnect, {}, owner_headers)[0])
            self.assertEqual(404, adapter.dispatch("POST", disconnect, {}, member_headers)[0])
            status, replacement = adapter.dispatch("POST", path,
                {"display_name": "Fresh Group"}, owner_headers)
            self.assertEqual(200, status)
            self.assertNotEqual(source_id, replacement["source_id"])

    def test_revoked_telegram_binding_does_not_block_group_reconnection(self) -> None:
        self.database.execute("UPDATE source_connections SET provider='telegram' WHERE id='src_a'")
        master = "telegram-test-master-key-longer-than-thirty-two-characters"
        with patch.dict("os.environ", {"COMVOLY_TELEGRAM_WEBHOOK_MASTER_KEY": master,
            "COMVOLY_TELEGRAM_BOT_USER_ID": "9001", "COMVOLY_TELEGRAM_BOT_USERNAME": "ComvolyTestBot",
            "COMVOLY_PUBLIC_API_URL": "https://api.dev.example.test"}):
            adapter = V2HTTPAdapter(self.database)
            owner_headers = {"Authorization": "Bearer a-long-local-development-secret",
                             "X-Comvoly-Account-Id": "acct_a"}
            original = adapter.dispatch("POST", "/v2/workspaces/ws_a/telegram/live/prepare",
                {"source_id": "src_a"}, owner_headers)[1]
            original_code = parse_qs(urlparse(original["install_url"]).query)["startgroup"][0]
            secret = derive_webhook_secret(master)
            activation = {"update_id": 40, "message": {"message_id": 1, "date": 1785484700,
                "chat": {"id": -10042, "type": "supergroup"}, "text": f"/start {original_code}"}}
            self.assertEqual(200, adapter.dispatch("POST", "/v2/telegram/webhooks", activation,
                {"X-Telegram-Bot-Api-Secret-Token": secret})[0])
            self.assertEqual(200, adapter.dispatch("POST",
                "/v2/workspaces/ws_a/telegram/disconnect/src_a", {}, owner_headers)[0])
            # Existing deployments revoked connections without releasing the
            # group identifier. Reproduce that legacy row during reconnection.
            self.database.execute("""UPDATE telegram_connection_configs
                SET expected_chat_id='-10042' WHERE source_connection_id='src_a'""")

            replacement = adapter.dispatch("POST", "/v2/workspaces/ws_a/telegram/connect",
                {"display_name": "Reconnected Group"}, owner_headers)[1]
            replacement_code = parse_qs(urlparse(replacement["install_url"]).query)["startgroup"][0]
            retry = {"update_id": 41, "message": {"message_id": 2, "date": 1785484800,
                "chat": {"id": -10042, "type": "supergroup"},
                "text": f"/start {replacement_code}"}}
            result = adapter.dispatch("POST", "/v2/telegram/webhooks", retry,
                {"X-Telegram-Bot-Api-Secret-Token": secret})
            self.assertEqual((200, "verifying"), (result[0], result[1]["state"]))
            released = self.database.execute("""SELECT expected_chat_id
                FROM telegram_connection_configs WHERE source_connection_id='src_a'""").fetchone()[0]
            self.assertEqual("revoked:src_a", released)

    def test_telegram_live_ignores_wrong_chat_without_cross_workspace_content(self) -> None:
        self.database.execute("UPDATE source_connections SET provider='telegram' WHERE id='src_a'")
        master = "telegram-test-master-key-longer-than-thirty-two-characters"
        with patch.dict("os.environ", {"COMVOLY_TELEGRAM_WEBHOOK_MASTER_KEY": master,
            "COMVOLY_TELEGRAM_BOT_USER_ID": "9001", "COMVOLY_TELEGRAM_BOT_USERNAME": "ComvolyTestBot",
            "COMVOLY_PUBLIC_API_URL": "https://api.dev.example.test"}):
            adapter = V2HTTPAdapter(self.database)
            owner_headers = {"Authorization": "Bearer a-long-local-development-secret", "X-Comvoly-Account-Id": "acct_a"}
            prepared = adapter.dispatch("POST", "/v2/workspaces/ws_a/telegram/live/prepare",
                {"source_id": "src_a"}, owner_headers)[1]
            code = parse_qs(urlparse(prepared["install_url"]).query)["startgroup"][0]
            secret = derive_webhook_secret(master)
            adapter.dispatch("POST", "/v2/telegram/webhooks", {"update_id": 7,
                "message": {"message_id": 1, "date": 1785484700,
                "chat": {"id": -10042, "type": "group"}, "text": f"/start {code}"}},
                {"X-Telegram-Bot-Api-Secret-Token": secret})
            update = {"update_id": 8, "message": {"message_id": 1, "date": 1785484800,
                "chat": {"id": -999}, "text": "must not enter either workspace"}}
            result = adapter.dispatch("POST", "/v2/telegram/webhooks", update,
                {"X-Telegram-Bot-Api-Secret-Token": secret})
            self.assertEqual((200, "ignored"), (result[0], result[1]["state"]))
            self.assertEqual(0, self.database.execute(
                "SELECT COUNT(*) FROM content_items WHERE body_text LIKE '%must not%'").fetchone()[0])

    def test_workspace_cited_answers_are_member_accessible_and_tenant_isolated(self) -> None:
        self._add_content()
        self.store.add_membership(self.context_a, self.member.account_id, "member")
        adapter = V2HTTPAdapter(self.database)
        member_headers = {"Authorization": "Bearer a-long-local-development-secret",
                          "X-Comvoly-Account-Id": "acct_member"}
        status, answer = adapter.dispatch("POST", "/v2/workspaces/ws_a/intelligence/ask",
            {"question": "What is the alpha secret?"}, member_headers)
        self.assertEqual(200, status)
        self.assertEqual(1, answer["evidence_count"])
        self.assertEqual("alpha secret", answer["citations"][0]["excerpt"])
        self.assertNotIn("beta secret", repr(answer))
        self.assertEqual(404, adapter.dispatch("POST", "/v2/workspaces/ws_b/intelligence/ask",
            {"question": "beta secret"}, member_headers)[0])


if __name__ == "__main__":
    unittest.main()
