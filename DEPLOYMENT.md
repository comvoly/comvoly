# Comvoly test deployment

This deployment uses one small Railway service for the Python API and Telegram sync,
Neon PostgreSQL for the archive, and Cloudflare Workers Static Assets for the frontend.

## Safety rules

- Never commit `.env`, the Telegram session, the Neon connection string, or API keys.
- Use Neon’s pooled connection string for `DATABASE_URL`.
- Keep Cloudflare Access in front of both the site and API during the private pilot.
- Keep the local SQLite archive until the Neon import and backup have been verified.

## Railway service

Deploy the repository using the root `Dockerfile`. Configure these Railway variables:

| Variable | Value |
|---|---|
| `DATABASE_URL` | Neon pooled connection string |
| `OPENAI_API_KEY` | OpenAI project key |
| `TELEGRAM_API_ID` | Existing Telegram application ID |
| `TELEGRAM_API_HASH` | Existing Telegram application hash |
| `TELEGRAM_PHONE` | Authorised Telegram account phone number |
| `TELEGRAM_GROUP` | Existing authorised group reference |
| `TELEGRAM_SESSION_STRING` | Output of `python src/export_telegram_session.py` |
| `COMVOLY_OWNER_PASSWORD_HASH` | Generated owner password hash |
| `COMVOLY_SESSION_SECRET` | Random session signing secret |
| `COMVOLY_AI_MODEL` | `gpt-5.6-luna` |
| `COMVOLY_AI_REASONING` | `none` |
| `COMVOLY_AI_MAX_OUTPUT_TOKENS` | `1200` |
| `COMVOLY_RUN_SYNC` | `true` |
| `COMVOLY_SYNC_INTERVAL` | `120` |
| `COMVOLY_SECURE_COOKIES` | `true` |
| `COMVOLY_WEB_ORIGIN` | `https://comvoly.com` |

Railway supplies `PORT`. After deployment, generate a Railway domain temporarily and
verify `/health` before adding `api.comvoly.com`.

## Initial archive import

The embedded sync creates the schema automatically and imports up to 100 new messages
per pass. For the current test archive this reproduces the local 61 messages in Neon.
Verify the message count in Comvoly before considering the cloud archive authoritative.

## Cloudflare Workers Static Assets

Create a Workers project from the same GitHub repository. Cloudflare's unified setup
replaces the older Pages flow for new static sites:

- Build command: `cd frontend && npm ci && npm run build`
- Deploy command: `npx wrangler deploy --config wrangler.jsonc`
- Build variable: `NEXT_PUBLIC_COMVOLY_API_URL=https://api.comvoly.com`

First use the generated `workers.dev` URL. After the API is healthy, attach `comvoly.com`
and `www.comvoly.com`, then redirect `comvoly.co.uk` to `https://comvoly.com`.

## Isolated v2 Auth development

Do not add these values to the live Railway or Cloudflare production environments.
For an isolated development deployment only:

- frontend: `NEXT_PUBLIC_NEON_AUTH_URL` and the development API URL;
- backend: `COMVOLY_IDENTITY_PROVIDER=neon`, the branch-specific
  `NEON_AUTH_ISSUER` and `NEON_AUTH_JWKS_URL`, and optionally
  `NEON_AUTH_AUDIENCE`;
- backend gates: `COMVOLY_ENABLE_V2_SCHEMA=true`, `COMVOLY_ENABLE_V2_API=true`, and
  `COMVOLY_V2_SELF_REGISTRATION=true`.

Keep `COMVOLY_V2_ALLOW_WORKSPACE_CREATION=false`. Owner creation is a separate approval
and commercial-entitlement decision; ordinary registration must not imply ownership.

For the isolated owner/member acceptance milestone only, this gate may be set to
`true`. It lets any authenticated development account create its own empty workspace;
it does not grant access to any existing workspace, connect a platform or start an
import. Keep it `false` in production until entitlement and pilot admission are
implemented.

A verified new identity creates an `accounts` and `linked_identities` record only. It
does not create a membership, workspace, source or entitlement. Community access starts
only when an owner invitation is accepted or an authorised administrator explicitly
adds a membership.

### Active isolated development deployment

- Neon project: `comvoly-v2-development` (`morning-tree-70922570`)
- Neon branch: `br-icy-glade-zac59aez`
- Railway environment: `v2-development` (`06a69fbb-4e84-4dab-87bd-eeddbdcd5776`)
- Railway API service: `0959bb6d-9939-4212-852c-aab1600d80c3`
- Development API: `https://clever-miracle-v2-development.up.railway.app`
- Development frontend Worker: `comvoly-v2-development`, configured by
  `wrangler.development.jsonc`
- Development frontend: `https://comvoly-v2-development.stephen-hammond86.workers.dev`

The Railway environment was created empty rather than duplicated from production, so it
does not inherit the production database, Telegram session or OpenAI key. Telegram sync
is disabled and Railway serverless sleeping is enabled to keep test usage low.

On 29 July 2026 the deployed registration path was verified end to end with a synthetic
account. The resulting database state was exactly one account, one linked identity, no
memberships, no workspaces and one registration audit event. The signed Neon issuer is
the Auth host origin, while `NEON_AUTH_JWKS_URL` remains the full Auth URL plus
`/.well-known/jwks.json`.

The owner/member milestone was then deployed with
`COMVOLY_V2_ALLOW_WORKSPACE_CREATION=true` in **v2-development only**. Live testing
verified workspace creation, setup progress, draft source planning, expiring invitation
creation, new-account acceptance, member-role presentation and removal of owner-only
controls. Production retains its existing owner-password application and was not
changed.

### Telegram Desktop history import

The v2 development API accepts a Telegram Desktop `result.json` through the
workspace-authorised preview/start/chunk/complete endpoints. The frontend limits the
pilot file to 25 MiB, while `COMVOLY_MAX_JSON_BYTES` defaults to 30 MiB. Each batch is
checkpointed and duplicate message IDs are upserted within one Telegram source.

This import currently stores message text and metadata plus a media-path inventory; it
does not upload the media directory. Do not configure a bot token in this environment
until the bot registration, webhook secret, least-privilege permissions, community
notice and platform/data-processing review are approved.

The Cloudflare production-dependency audit currently reports three high-severity
advisories in transitive Next.js build packages (`postcss` and `sharp`) and no critical
advisories. This deployment publishes static assets only, so those packages are not in
the Worker runtime. npm's proposed automatic fix is an unsuitable major downgrade and
must not be applied; reassess the dependency tree before a future framework upgrade.

## Private-pilot access

Create Cloudflare Access self-hosted applications for `comvoly.com` and
`api.comvoly.com`. Start with an allow policy containing only the founder’s existing
Google identity. Do not invite pilot users until API access through Cloudflare and the
application owner session have both been tested.
