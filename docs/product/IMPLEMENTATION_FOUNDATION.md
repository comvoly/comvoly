# Comvoly v2 implementation foundation

Status: milestone 1 implemented on 28 July 2026.

## Outcome

The repository now contains an additive, production-oriented multi-community domain
foundation. It does not replace the working owner prototype or alter its data. The old
`communities`, `messages`, and `sync_runs` records continue to power the current site;
the v2 records are ready for subsequent account, onboarding, and importer work.

## Implemented boundaries

- Immutable Comvoly accounts and separately linked provider identities.
- Multiple workspace memberships per account, with independent role and state.
- Central server-side capability resolution, including explicit administrator
  overrides for sensitive actions.
- Account, membership, and workspace lifecycle checks on every authorised context.
- Platform-neutral source connections, spaces, conversations, content, and media.
- Resumable, idempotent import jobs and workspace-bound checkpoints.
- Signed internal job identities tied to a job, workspace, source, and expiry.
- Workspace audit events, usage counters, and entitlement records.
- Provider-neutral contracts for identity, connectors, and AI retrieval.
- Workspace-scoped repositories for search, evidence, media, jobs, and export manifests.
- Database constraints preventing important cross-workspace source/content/media/job
  relationships even if application code is bypassed.

## Migration strategy

`database.create_schema()` still creates the legacy prototype tables. It runs the v2
migration registry in `backend/src/migrations.py` only when
`COMVOLY_ENABLE_V2_SCHEMA=true`. The default is false so an automatic Railway deploy
cannot alter the live schema. Applied versions are recorded in `schema_migrations`.
Migration 1 is additive and contains no update, deletion, rename, or copy of live
records.

This repository does **not** automatically convert the existing Telegram archive to a
workspace. A separately reviewed migration will be required after managed identity and
the initial owner account exist. That migration must support a dry run, backup,
reconciliation counts, and rollback.

## Authorisation rule

Application code receives an authenticated `Principal`, then resolves a
`WorkspaceContext` on the server. The context is issued only when:

1. the account is active;
2. the membership is active;
3. the workspace is not being deleted or deleted; and
4. the role plus any explicit override grants the requested capability.

Every repository query includes the authorised workspace ID. A caller-supplied
workspace identifier alone never grants access. Missing and unauthorised resources
produce the same application-level outcome so IDs cannot enumerate another community.

## Role decisions

- Owners receive all capabilities.
- Administrators receive operational capabilities by default.
- Role changes, processing-policy changes, full exports, billing, ownership transfer,
  and deletion are not implicit administrator capabilities. The first three may be
  granted through an audited per-member override in a later management service.
- Moderators can use intelligence, view evidence, save items, curate knowledge, and
  review concerns.
- Members can use intelligence, view evidence, and save personal items.
- Ownership mutation is intentionally absent until a transaction can enforce that an
  active workspace always has at least one active owner.

## Identity decision

No production identity vendor was selected. `IdentityProvider` defines the managed
session boundary and `LocalTestIdentityProvider` is closed by default, accepting only
tokens explicitly registered in a test. The existing password cookie remains limited
to the legacy prototype and is not treated as a v2 multi-user identity.

## Connector and intelligence decisions

No Telegram, Discord, or Skool production connector was started. A connector must
produce `NormalisedContent` through the shared cursor-based contract. AI retrieval must
accept an already-authorised `RetrievalScope`; provider credentials and raw browser
workspace IDs are not part of that interface.

## Verification

The automated suite covers migration idempotency and legacy-table preservation;
multiple memberships; role denial and capability overrides; suspended-account denial;
cross-workspace search, evidence, media, jobs, checkpoints, and exports; database-level
foreign-key rejection; signed worker identities; and the closed local identity adapter.

## Deliberately deferred

- Managed OpenID Connect vendor and browser-session integration.
- Live archive migration or production data changes.
- Account/workspace UI and public v2 HTTP routes.
- Queue, object-storage, malware-scanning, and AI vendors.
- Provider app registration and production connectors.
- Import parser and media processing implementation.
- Billing collection or paid infrastructure.

These require product UI work, external accounts, live-data approval, or material
vendor/security decisions.

## Next milestone

Build the first end-to-end account and workspace experience against these boundaries:
managed identity selection, account resolution, workspace switcher, owner setup, member
invitation/approval, and authenticated v2 API routes. Do not expose a v2 route until its
principal is resolved from a verified server-side session.
