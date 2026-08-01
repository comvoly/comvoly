# Imported-knowledge review milestone

Status: implemented and locally verified on 1 August 2026; isolated-development
deployment pending the milestone commit.

## Outcome

Historical Telegram messages now have an explicit trust boundary between ingestion
and use. A completed archive enters `owner_review`; its newly discovered messages are
staged and cannot be retrieved by Comvoly until an authorised owner accepts them.

The owner review shows:

- staged messages and already-stored overlaps;
- participant count and historical date coverage;
- parser warnings and failed-item counts;
- a bounded sample of recent messages; and
- clear accept, cancel, and restart actions for the states where each is safe.

After acceptance, the job becomes `active`, its staged items become available to
workspace-scoped retrieval, and the setup review step is completed. Citations identify
whether evidence came from a historical Telegram import or the live Telegram bot.

## State and data safety

Migration 5 adds an optional import-job reference and a review state to content items.
Existing and live records default to `active`; new historical records are written as
`staged` with their import job ID.

Cancellation:

- is restricted to the server-side `import_history` capability;
- removes media rows and staged content belonging to that workspace and job only;
- does not delete live messages, accepted history, another import, or another
  workspace;
- records a terminal `cancelled` state and an audit event; and
- retains job/checkpoint metadata for traceability and a controlled restart.

Restart is allowed only from a retryable terminal state. It removes non-preview
checkpoints, resets progress and byte watermarks, increments the attempt number and
requires the owner to choose the same local export again. It does not silently restart
network or file processing in the background.

## Re-import overlap rule

Canonical accepted/live records win over a later staged import with the same source
message ID. The new review reports these as already stored rather than replacing them.
Cancelling the later job therefore cannot delete or roll back previously accepted
knowledge. Dry-run edited-message comparison remains a later curation feature.

## Retrieval acceptance

The retrieval boundary now filters to `review_state='active'` in addition to the
authorised workspace. Automated acceptance proves that:

1. live Telegram evidence is available while an import awaits review;
2. staged historical evidence is absent from answers;
3. accepting the import makes both live and historical evidence available;
4. citations label each ingestion route;
5. cancelling a repeat import preserves already accepted history; and
6. member and cross-workspace review requests are concealed.

The answer generator remains the deterministic extractive pilot. This milestone
validates the evidence boundary and mixed-source citation contract; it does not yet
activate a paid interpretation model.

## Next product slice

Founder acceptance should import a small real export, inspect the sample and coverage,
accept it, and ask a question whose evidence exists in both old and newly posted
messages. The next engineering milestone should add import diagnostics and curation:
downloadable warning details, date/source exclusions, edited-message dry runs, and
owner remediation for partial imports. Full media binaries remain separately gated by
the storage, scanning, retention and cost decision.
