# Import diagnostics and curation milestone

Status: implemented and locally verified on 2 August 2026; isolated-development
deployment pending the milestone commit.

## Outcome

The historical import review now explains what an archive would do before the owner
accepts it. Each checkpoint records and the review aggregates:

- new messages;
- already-stored identical messages;
- source messages whose checksum differs from the accepted version; and
- skipped service or unsupported records.

Accepted and live records remain canonical during this dry run. A changed record is
reported but is not silently replaced. This makes cancelling a repeat import safe and
defers edited-message replacement to a future explicit comparison workflow.

Owners can download a JSON diagnostics report containing the job state, inventory,
change counts, active review policy and parser warnings. The report contains aggregate
diagnostics rather than full message bodies.

## Reversible review policy

While a job is in `owner_review`, an owner can restrict the included staged knowledge
by:

- inclusive start date;
- inclusive end date; and
- up to 100 exact Telegram sender IDs.

Applying filters marks matching job records as `staged` and non-matching records as
`excluded`. Reapplying or clearing the policy reverses that decision until acceptance.
Only `staged` records become `active` when accepted; excluded records remain
unavailable to search, evidence lookup, media access and intelligence retrieval.

The policy is stored as a workspace/job-bound checkpoint and changes create audit
events with aggregate included/excluded counts. Sender IDs are capped and validated;
dates use ISO `YYYY-MM-DD` and the start cannot follow the end.

## Security and data safety

- Policy reads and writes require the server-side `import_history` capability.
- Job and content queries always include the authorised workspace and import job.
- Members and other workspace owners receive concealed not-found responses.
- Cancellation and restart remove both staged and excluded records for that job only.
- Existing accepted/live content with the same source ID is never reassigned to the
  staged job and therefore cannot be deleted by its cancellation.
- Diagnostics reports are constructed locally from already-authorised review metadata.

## Verification

The automated acceptance suite covers new/unchanged/changed/skipped classification,
date filtering, sender filtering, reversible restoration, member denial, mixed live
and accepted-history retrieval, changed re-import preservation, cancel safety and
retry-state reset. The complete backend, frontend and migration suites must remain
green before deployment.

## Deliberate boundary and stopping point

This completes the safe text-history onboarding loop needed for founder usability
testing. The following work is deliberately gated:

- applying edited historical versions needs an owner-facing field comparison and
  retention decision;
- binary media needs storage, malware scanning, retention and budget approval;
- external AI interpretation needs provider/model, data-processing and cost approval;
- inviting real pilot communities needs owner-authority, member-notice and privacy/legal
  review; and
- Discord registration or Skool access would create external-account/platform
  consequences.

The next action should therefore be a founder acceptance run on a real authorised
small export, followed by a short product review of the above gates.
