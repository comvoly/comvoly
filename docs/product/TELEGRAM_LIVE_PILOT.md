# Telegram live pilot milestone

Status: implementation complete behind the isolated v2 feature gates. The founder has
registered `@ComvolyBot`; its token has not been shared with Comvoly or activated yet.

## Delivered

- Additive migrations 3 and 4 create workspace-bound Telegram connection
  configuration, one-time group-binding codes and idempotent webhook-event records.
- `@ComvolyBot` uses Telegram's required single global webhook. A high-entropy,
  owner-generated `startgroup` link binds each Telegram group to exactly one existing
  Comvoly source and workspace.
- The public webhook resolves its workspace from the bound Telegram chat ID or a
  one-time code. It never accepts a workspace ID from Telegram or the client.
- Every webhook requires Telegram's secret-token header. Its value is derived with
  HMAC-SHA256 from a server-held master key and each prepared connection stores only a
  digest.
- Bot tokens remain deployment secrets and are neither accepted by the API nor stored
  in Comvoly's database.
- Membership updates move a source into verification. The first valid message proves
  delivery, upserts content and marks the source connected and healthy.
- Telegram `update_id` and source message IDs make retries idempotent. Updates from an
  unexpected chat are recorded as ignored and cannot enter any workspace.
- New and edited text/caption messages use the same platform-neutral spaces,
  conversations and content records as historical imports.
- Connection preparation and first verified delivery create audit events.
- The owner UI shows preparation, installation and connection state without exposing
  secrets. Until the official bot is configured it accurately shows the external
  registration boundary.

## Cited intelligence pilot

The workspace account screen now includes a cited-answer experience for both owners
and authorised members. The current safe adapter performs workspace-scoped lexical
retrieval and returns an extractive evidence view. It deliberately does not call an
external model or claim full interpretation yet. Every cited item includes source,
author, message ID, date and excerpt. Questions increment a zero-cost workspace usage
counter and create an audit event without storing the question in the audit metadata.

This service boundary can later receive semantic retrieval and an approved model while
retaining the same server-authorised workspace context and evidence contract.

## Security and isolation acceptance

Automated coverage verifies:

- missing or incorrect webhook secrets are rejected before an event is stored;
- duplicate Telegram updates do not duplicate content;
- an unbound or unexpected Telegram chat is ignored;
- two workspaces receive different one-time codes and binding one cannot bind the other;
- owners cannot prepare another workspace's source;
- live content is written only to the configured source's workspace;
- member cited answers are restricted to an active membership's workspace; and
- an unauthorised workspace is concealed as not found.

## External activation boundary

Founder action is required for the following steps:

1. Store the existing `@ComvolyBot` token directly in the isolated Railway secret
   manager. Never paste it
   into chat, a browser form, a document or Git.
2. Configure a separate random webhook master key and the official numeric bot user ID.
3. Run the token-safe admin command to verify the bot identity and register the one
   global webhook.
4. Approve the member-facing pilot notice/privacy wording and confirm the selected test
   group owner has authority to connect the group.
5. Run a real test-group acceptance
   before any broader pilot.

Production remains unchanged. Do not add these values to the production Railway
environment during the isolated pilot.
