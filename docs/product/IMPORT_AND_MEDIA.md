# Historical import and media design

## 1. Product promise

An established community should not feel empty after connecting. Comvoly must offer an
owner-controlled path to useful history, report exactly what was and was not imported,
and continue from the historical cut-over without duplicate content.

Historical import and ongoing sync are separate jobs sharing one normalised content
model and identity/deduplication strategy.

## 2. Telegram launch import

### Supported source

Telegram Desktop individual-chat export in machine-readable JSON, optionally including
selected media. The owner is guided through the export with current, illustrated
instructions and an import checklist.

### Owner steps

1. Select **Import previous history**.
2. View Telegram Desktop export instructions and privacy explanation.
3. Choose history/date/media scope in Telegram.
4. Select the exported folder or ZIP in Comvoly.
5. Comvoly validates locally where possible, then uploads resumably.
6. Comvoly inventories the archive without AI processing.
7. Owner reviews scope, exclusions, storage, estimated processing, and cost/allowance.
8. Owner confirms import and community notice.
9. Background jobs parse, normalise, deduplicate, store, and optionally extract content.
10. Owner reviews sample search/answers and activates member access.

### Required parser coverage

- chat identity and export metadata;
- ordinary text, formatted entities, links, replies, forwards, and service messages;
- created/edited timestamps where supplied;
- sender identity/display metadata where supplied;
- photos, video, audio, voice notes, stickers/animations, and generic files;
- missing media paths and zero-byte/corrupt files;
- differing export versions and optional fields;
- Unicode, emoji, right-to-left text, and long messages;
- messages omitted by the export or protected-content rules.

Service events may be retained as structured metadata but are excluded from ordinary AI
retrieval unless they add useful context.

## 3. Upload and job lifecycle

### Upload

- resumable multipart uploads;
- checksums per part/file;
- encrypted transport and private object storage;
- filename/path sanitisation;
- decompression limits and archive traversal protection;
- malware scanning for files exposed back to users;
- explicit maximum archive/file size and allowance messaging;
- upload token scoped to workspace, account, import ID, size, and expiry.

### Import states

```text
created -> uploading -> validating -> preview_ready -> confirmed
        -> parsing -> storing -> extracting -> indexing -> owner_review
        -> active
```

Terminal alternatives:

- cancelled;
- rejected (invalid/unsafe archive);
- failed (actionable reason and retry path);
- partially_completed (usable content plus item-level exceptions).

### Progress model

Show stages rather than an unreliable single percentage. Within a measurable stage,
show processed/total items and bytes. Display:

- current stage;
- messages/media discovered and processed;
- warnings and failed items;
- estimated remaining range, not false precision;
- safe actions: leave page, cancel before activation, retry failures.

## 4. Preview and owner confirmation

Before content extraction or AI processing, show:

- detected community name/source;
- history start/end dates;
- message, participant, and thread/topic counts;
- media counts and bytes by type;
- excluded/unsupported/protected items;
- overlap with already stored source items;
- estimated storage and optional processing usage;
- selected retention and AI-processing settings;
- member notice status.

The owner can exclude date ranges, sender identities where appropriate, media classes,
or source spaces before confirmation. Exclusions are stored as policy, not only as a
one-time parser setting.

Implementation note (1 August 2026): the first review slice now stages historical
Telegram text until owner acceptance, displays inventory/coverage/warnings/sample
messages, and provides workspace-scoped cancel/restart controls. Date, sender, space
and media-class exclusions remain part of the later curation slice.

## 5. Idempotency and cut-over

### Stable identity

Uniqueness is based on workspace, provider, external community/space, and external item
ID. Where an export lacks a stable ID, use a documented composite fingerprint and mark
its lower-confidence identity.

### Re-import

- unchanged records are skipped;
- edited records create/update the current representation and retain audit metadata;
- attachments are deduplicated by source ID/checksum within policy;
- new history is appended;
- policy exclusions are re-applied;
- a dry-run preview reports changes before confirmation.

### Historical/ongoing overlap

The connector records the bot installation/cut-over time and highest observed source
markers. Ongoing events may arrive while history imports. Both paths use the same
unique constraints, so ordering does not create duplicates.

## 6. Media storage model

### Records

An attachment record includes:

- workspace/content/source identifiers;
- original name, type, size, checksum, and provider metadata;
- secure object key (never a public permanent URL);
- source availability and download status;
- thumbnail/preview references;
- extraction state and processor/version;
- retention/deletion state;
- safety scan state;
- optional extracted text, transcript, or description reference.

### Access

Media requests re-authorise account, membership, workspace, and source scope. The
backend returns a short-lived signed delivery URL or streams the object. Shared cached
URLs must never grant cross-workspace access.

### Storage lifecycle

- upload/source download lands in quarantine;
- validate/scan and compute checksum;
- move to private canonical storage;
- create permitted previews;
- schedule optional extraction;
- apply retention and deletion jobs;
- verify deletion across originals, derivatives, indexes, and backups according to
  documented timing.

## 7. Processing tiers

### Required for pilot

- inventory and securely display common images/files;
- extract text from PDFs and common office/text documents;
- OCR screenshots/images when the owner enables external processing;
- include extracted text in retrieval with a citation to the parent message/file;
- display processing state and unsupported types.

### Optional/later

- general image descriptions;
- voice-note transcription;
- video audio transcription and chaptering;
- object/scene search;
- richer table and diagram extraction.

Each derivative records the processor, model/version, timestamp, language, confidence
where available, and source attachment. Reprocessing is versioned and reversible.

## 8. Retrieval and citation

Media-derived content is never presented as an independent source. A citation includes:

- workspace and source community;
- original message/post/comment;
- attachment name/type;
- date and author where permitted;
- extracted excerpt or timestamp/page reference;
- direct authorised link to the original context or stored preview.

Answers distinguish source text from OCR/transcription/model-derived descriptions.

## 9. Retention, export, and deletion

### Retention

Workspace policy separately covers:

- normalised text/metadata;
- original media;
- derived previews/extractions;
- raw import archive;
- logs and audit records;
- generated answers and summaries.

Raw archives should be deleted after a short verification window unless the owner
explicitly chooses and pays to retain them. Canonical imported items remain according
to workspace policy.

### Export

Owner export contains:

- documented structured content format;
- media and derivatives where permitted;
- source identifiers and relationships;
- workspace knowledge/curation;
- member/account data only to the extent legally and contractually appropriate;
- manifest, checksums, export date, and known omissions.

### Deletion

Deletion is asynchronous and tracked. The owner sees affected categories, cooling-off
period, expected backup expiry, and final confirmation. Disconnecting a source does not
silently delete retained history; deleting a workspace does.

## 10. Failure and edge cases

- wrong group export: stop before processing and let owner replace it;
- multiple chats in export: require explicit matching/selection;
- bot group differs from export: require owner confirmation or reject;
- partial archive/media: import valid content and report omissions;
- protected/deleted content: do not bypass provider restrictions;
- participant name changes: retain source identity where possible and historical display
  metadata without treating names as unique;
- huge archive: estimate, quota-check, batch, and resume;
- duplicate files: deduplicate storage only without losing message relationships;
- malicious archive/path: reject and audit;
- owner cancels: stop new processing and delete staged material according to stated
  timing.

## 11. Acceptance tests

Use synthetic and owner-authorised fixtures, never unapproved personal archives.

- small text-only export;
- large export with every supported media type;
- changed export schema/optional fields;
- interrupted upload and processing resume;
- duplicate/re-import with edits and new messages;
- overlap with ongoing bot events;
- malformed JSON and missing/corrupt media;
- traversal/decompression-bomb and unsupported file safety tests;
- workspace isolation with identical filenames/checksums;
- OCR/document extraction citation trace;
- export and complete deletion lifecycle.
