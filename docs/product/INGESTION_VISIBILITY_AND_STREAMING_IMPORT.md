# Ingestion visibility and streaming import milestone

Status: implemented and locally verified on 1 August 2026; isolated-development
deployment pending the milestone commit.

## Outcome

An owner can now see whether each connected source is actually delivering knowledge,
not merely whether its setup record says `connected`. The account screen reports live,
historical and total message counts, the last ingestion time, historical coverage and
a clear receiving/connecting/attention state. It refreshes every ten seconds without
requiring the owner to reload the page.

Telegram Desktop history import no longer reads the whole `result.json` into browser
memory or sends it as one large request. The browser scans the file in 1 MiB sections,
parses one message at a time and uploads bounded batches of 200 records. This design
supports Telegram's current 4 GB export ceiling for the JSON file while keeping memory
use proportional to a batch and the largest individual message, not the archive size.
Actual performance still depends on the device, browser, network and message shapes.

## Resume and progress model

- A stable import key is derived locally from file metadata and the first and last
  64 KiB of the selected file.
- Starting the same workspace/file combination returns its existing import job.
- The API returns completed chunk indexes. The client scans deterministically from the
  beginning but skips batches already committed by the server.
- Every completed batch stores a workspace-bound checkpoint and byte watermark.
- Replaying a completed batch remains a no-op, and message upserts remain idempotent by
  source plus external message ID.
- The owner sees bytes read, records found, records stored and whether a run resumed.
- A failure is presented as safely paused. Choosing the same file resumes it.

Live bot ingestion and archive import are separate states. Starting or completing a
history job never pauses a source that is already connected and healthy, so ongoing
Telegram messages can continue while old knowledge is imported.

## Security and privacy

- Import start, status, chunks, completion and ingestion health all derive workspace
  context from the authenticated principal on the server.
- Import-job lookups include the authorised workspace. Cross-workspace and ordinary
  member health requests are concealed as not found.
- The selected archive remains on the owner's device while being processed; Comvoly
  receives only bounded message batches over the authenticated API.
- The UI never provides authority. Every operation is capability checked server-side.
- The resume fingerprint is an idempotency identifier, not a content-authentication or
  malware-scanning mechanism.

## Media boundary

Message and caption text plus media references are imported. Exported photos, videos,
voice notes and documents are not uploaded in this milestone. Full media ingestion
requires private object storage, quotas, malware scanning, deletion semantics and a
cost/provider decision, so it remains outside this milestone.

## Acceptance checks

Automated backend coverage verifies a 4 GB file-size watermark, unknown message total,
chunk and byte progress, deterministic resume, completed-chunk reporting, final
summary, preservation of a live source, source-level ingestion counts, member denial
and cross-workspace concealment. The complete backend suite, frontend lint, production
static build and repository whitespace checks must pass before deployment.

## Next product slice

Run founder acceptance with a real small export, deliberately interrupt and resume a
second import, and compare the displayed live count with newly posted Telegram
messages. After acceptance, the next build should focus on imported-knowledge review,
coverage/warning remediation and an owner-controlled import cancellation/restart
journey. Media binaries remain a separate approved infrastructure milestone.
