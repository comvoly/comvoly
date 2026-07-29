# Account and workspace experience milestone

Status: safe implementation slice and isolated PostgreSQL migration rehearsal complete
on 29 July 2026; managed identity and live rollout remain closed.

## Completed

- Versioned migration 2 adds expiring workspace invitations and owner-setup progress.
- A transport-neutral application service exposes account sessions, workspace lists,
  workspace creation, workspace overview, member lists, invitations, and acceptance.
- Invitation tokens are returned once and stored only as SHA-256 hashes.
- Accepted invitations create or reactivate a membership in the intended workspace.
- Workspace creation automatically creates the five agreed owner setup steps.
- A feature-gated HTTP adapter exposes the application service only when both the v2
  schema and v2 API have been explicitly enabled.
- The temporary development identity adapter requires a long shared secret and an
  account ID. It defaults off and is prohibited in production.
- A responsive account/workspace preview implements:
  - one Comvoly account spanning several communities;
  - workspace switching with role context;
  - owner setup progress;
  - member and source management;
  - mobile and desktop navigation; and
  - product-level Ask, Catch Up, and Explore destinations.

## Safety gates

All gates default to false:

```text
COMVOLY_ENABLE_V2_SCHEMA=false
COMVOLY_ENABLE_V2_API=false
COMVOLY_V2_DEV_AUTH=false
NEXT_PUBLIC_COMVOLY_V2_PREVIEW=false or unset
```

Consequently, deploying `main` does not create v2 production tables, expose v2 API
routes, accept development identities, or display the preview route. The legacy owner
prototype remains the only live product path.

## Local preview

The preview contains synthetic product data only. To review it locally:

```powershell
$env:NEXT_PUBLIC_COMVOLY_V2_PREVIEW='true'
npm.cmd run dev -- --hostname 127.0.0.1 --port 3100
```

Then open `http://127.0.0.1:3100/v2-preview`.

The responsive review covered desktop and 390-pixel mobile layouts, workspace
navigation, management navigation, and horizontal-overflow checks.

## Automated coverage

The backend tests now additionally cover:

- disabled API and invalid development sessions;
- account-scoped workspace session results;
- concealment of another workspace through the HTTP adapter;
- invitation creation and acceptance;
- non-storage of raw invitation tokens; and
- setup-step creation for new workspaces.

## Isolated Neon rehearsal (29 July 2026)

- Created `comvoly-v2-development` (`br-bitter-snow-zarme2bt`) as a schema-only
  branch of the existing Neon project. No production rows were copied.
- Ran migrations 1 and 2 inside a transaction, then ran them a second time to verify
  idempotency. Both expected migration records and all six sampled core tables were
  present.
- Added `backend/tools/render_v2_migrations.py` so the exact migration registry can be
  rendered as reviewable PostgreSQL SQL without handling a database credential.
- Did not change the production branch, production environment variables, live data,
  or any public Comvoly route.

The branch was created with automatic expiry on 30 July 2026. It is a disposable
rehearsal environment, not a persistent development database.

## Neon Auth finding and activation gate

Neon Auth provisioning on the schema-only branch failed with `permission denied for
database neondb`, despite the selected role owning the database. A separate empty test
project confirmed a more important product constraint: the current Neon Auth beta
enables unrestricted web signup and states that restricted signup support is still
coming. The empty test project was immediately deleted.

This conflicts with the approved private-founder rollout. Neon Auth therefore remains
disabled and no Auth URL, client configuration, user, production key, or public signup
surface has been retained. Reassess Neon Auth when restricted signup is available, or
approve a provider that supports invitation-only access before implementing an adapter.

## Decision required before activation

The next step requires selecting a managed identity provider and approving a staged
database rollout. The existing provider-neutral `IdentityProvider` boundary allows the
choice to be made without changing the domain model.

The decision should compare at least:

- support for email/passkey or social sign-in and account recovery;
- OpenID Connect standards and exportability;
- secure server-side session verification;
- pricing at pilot and early-growth volumes;
- custom-domain and branding support;
- multi-environment configuration;
- data-processing location and contractual terms; and
- operational fit with Railway, Cloudflare, and Neon.

No provider account, production key, paid service, live schema migration, or user-data
conversion has been created by this milestone.

## Activation sequence after approval

1. Configure separate development and production identity applications.
2. Implement and test the selected managed identity adapter.
3. Add server-side account resolution and secure browser sessions.
4. Rehearse migrations 1 and 2 against an isolated Neon branch or disposable database. **Completed.**
5. Produce a live rollout backup, dry-run report, reconciliation plan, and rollback.
6. Enable the v2 schema in a controlled maintenance deployment.
7. Seed the founder account and migrate the prototype community through a separately
   approved, idempotent migration.
8. Enable authenticated v2 API routes for the founder only.
9. Replace synthetic preview data with the authenticated application service.
10. Conduct owner and invited-member acceptance testing before broader access.
