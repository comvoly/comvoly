from __future__ import annotations

import sqlite3
import json
import sys
import tempfile
import unittest
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
            [(1, "v2_secure_multi_community_foundation"), (2, "v2_account_workspace_experience")],
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


if __name__ == "__main__":
    unittest.main()
