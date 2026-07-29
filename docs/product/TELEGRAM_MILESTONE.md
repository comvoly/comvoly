# Founder Telegram history milestone

Status: implemented, locally verified, deployed to the isolated v2 environment and
accepted through a live synthetic owner journey on 29 July 2026. Real bot activation
is externally gated.

## Delivered scope

This milestone implements the part of Telegram onboarding that creates immediate value
for an established community: owner-authorised history from Telegram Desktop's
machine-readable `result.json` export.

The owner journey now:

1. creates or selects a workspace;
2. plans a Telegram source without providing a credential;
3. selects one Telegram Desktop `result.json` file;
4. receives a non-AI inventory preview;
5. reviews community name, export type, date range, message, participant, media-reference
   and service-event counts;
6. confirms a resumable batch import;
7. sees stored/total progress and safe retry behaviour; and
8. lands at owner review with the historical source clearly labelled as not live.

## Parser and storage behaviour

- Versioned parser: `telegram-desktop-json-v1`.
- Supports string and formatted-entity-array message text.
- Preserves message ID, author ID, date, edit metadata, reply target and media-path
  inventory.
- Service events are counted but excluded from ordinary retrieval.
- Stable chat IDs are preferred; old exports without one receive a clearly marked
  deterministic export fingerprint.
- Invalid dates/messages are skipped with preview warnings.
- Normalised items are upserted by source and external message ID, so re-import does
  not duplicate messages and edited representations can be refreshed.
- Upload batches are limited to 500 source records and checkpointed by job/chunk.
  Replaying a completed chunk is a no-op.
- Import jobs, checkpoints, content, sources, spaces and conversations are all bound to
  the server-authorised workspace.
- Browser JSON requests default to a 30 MiB backend limit; the current UI applies a
  25 MiB file limit so the owner receives a useful error before uploading.

## Media boundary

This slice inventories media references from the Telegram export but does not upload
the exported media directory. It therefore makes no claim that images/files are stored
or available to AI yet. ZIP/folder upload, private object storage, malware scanning,
media checksums and extraction are the next media-specific slice.

## Ongoing bot boundary

A real Comvoly bot is still required for messages created after onboarding. The UI
explains that the bot cannot retrieve pre-installation history and keeps activation
disabled until all of the following are approved and available:

- an official Comvoly bot registered through Telegram BotFather;
- a securely stored development bot token and webhook secret;
- an HTTPS webhook and bot identity verification;
- least-privilege group permission and admin-status checks;
- member-facing notice/privacy wording; and
- Telegram terms, community authority and AI-processing review for the pilot.

The existing production Telethon personal-account session is not copied into the v2
environment and is not treated as the customer connection architecture.

## Verification

Synthetic fixtures cover ordinary messages, formatted text, Unicode, replies, edit
metadata, service events, media references and Unix/ISO timestamps. Automated tests
also cover preview validation, resumable/replayed chunks, normalised storage,
owner-review completion, member rejection and cross-workspace job concealment.

No real Telegram archive or credential is used by the automated suite.

Live isolated acceptance confirmed that the owner UI previewed a synthetic Telegram
Desktop export as 3 messages, 2 participants, 1 media reference and 1 service event;
imported all 3 messages; moved the job to `owner_review`; and left the source paused
pending bot activation. The isolated v2 API and unchanged production API both returned
healthy after deployment.
