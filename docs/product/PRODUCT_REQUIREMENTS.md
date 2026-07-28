# Product requirements

## 1. Purpose

Comvoly uses AI to interpret the accumulated knowledge inside authorised online
communities. It goes beyond searching individual messages by connecting conversations,
experience, recommendations, decisions, patterns, and resources into cited answers,
catch-ups, insights, exploration, and reusable community knowledge.

Every interpretation remains grounded in permitted source material so members can
inspect the people, messages, and evidence behind it.

This specification defines the invitation-only multi-community pilot. It does not
define the eventual public marketplace, native mobile application, or enterprise
compliance product.

## 2. Users and jobs

### Community owner

Primary jobs:

- connect a community without developer assistance;
- bring established history and media into Comvoly;
- decide what is included and who can access it;
- reduce repeated questions and recover useful prior knowledge;
- inspect connection health, usage, cost, and member activity;
- pause, export, or delete the workspace.

### Administrator or moderator

Primary jobs:

- support member access;
- review excluded or reported content;
- correct curated knowledge;
- monitor imports and ongoing source health.

### Community member

Primary jobs:

- sign in once and access every authorised community;
- find an exact prior message;
- ask a question and inspect its evidence;
- catch up on missed discussion;
- browse recurring questions, decisions, recommendations, links, and files;
- save useful items privately.

### Comvoly operator

Primary jobs:

- support pilot owners without accessing unnecessary content;
- diagnose connector and import failures;
- monitor cost, reliability, and security events;
- honour deletion and export requests.

## 3. Product surfaces

### Account level

- account home;
- owned and joined communities;
- linked platform identities;
- personal saved items and preferences;
- personal notifications and digests;
- security and recovery.

### Workspace level

- overview;
- Ask;
- Search;
- Catch Up;
- Explore;
- saved and curated knowledge;
- members and roles;
- connections/imports;
- privacy, retention, usage, billing, export, and deletion.

## 4. Pilot functional requirements

Requirement IDs remain stable so implementation and tests can reference them.

### Accounts and membership

- **ACC-01** A person can create one Comvoly account using an approved identity method.
- **ACC-02** A person can link multiple platform identities to that account.
- **ACC-03** Linking an identity requires fresh proof from the platform; typed usernames
  are not proof.
- **ACC-04** The account home separates owned, administered, and joined workspaces.
- **ACC-05** Losing source-community membership suspends workspace access when reliable
  verification is available.
- **ACC-06** An invitation/admin-approval fallback exists when a platform cannot verify
  membership reliably.
- **ACC-07** Account recovery cannot silently replace or unlink a platform identity.

### Workspaces and separation

- **WSP-01** Every community has an immutable internal workspace identifier.
- **WSP-02** Every content record, import, answer, citation, membership, and usage event
  belongs to exactly one workspace.
- **WSP-03** Every workspace request authorises the account and membership before data
  retrieval.
- **WSP-04** Separate communities are never blended into an answer by default.
- **WSP-05** Personal multi-workspace features require explicit workspace selection and
  label every cited workspace.
- **WSP-06** Workspace owners cannot inspect a member's activity in unrelated
  workspaces.

### Owner onboarding

- **ONB-01** A non-technical owner can create a workspace without configuration files,
  source IDs, developer keys, or command-line steps.
- **ONB-02** Comvoly verifies owner/admin authority before activating a shared source.
- **ONB-03** Owners choose included channels/topics/date range/media types before
  processing.
- **ONB-04** Historical import is offered during setup and remains available later.
- **ONB-05** A preview shows date range, message count, participant count, media count,
  estimated processing, and exclusions.
- **ONB-06** Member access remains closed or administrator-only until owner review.
- **ONB-07** Owners can test sample Search and Ask results before inviting members.
- **ONB-08** Setup progress survives navigation and browser closure.

### Content ingestion

- **ING-01** Historical and ongoing ingestion use stable source identifiers to avoid
  duplicates.
- **ING-02** Re-running an import is idempotent and updates edited items safely.
- **ING-03** Deletions and edits are recorded according to workspace policy and platform
  capability.
- **ING-04** Individual malformed items do not fail an otherwise valid import.
- **ING-05** Owners receive actionable failure messages and can retry failed items.
- **ING-06** Import/sync records include source, start/end time, counts, status, and
  non-secret diagnostics.
- **ING-07** Attachments retain their relationship to the source item and thread.
- **ING-08** Ingestion does not expand beyond the owner-approved source scope.

### Ask, Search, Catch Up, and Explore

- **VAL-01** Ask answers use only content the requesting member may access.
- **VAL-02** Material answer claims include citations to source items.
- **VAL-03** Answers state when evidence is missing, conflicting, old, or uncertain.
- **VAL-04** Exact Search supports text, date, author where permitted, source space, and
  attachment filters.
- **VAL-05** Semantic retrieval never replaces access checks or evidence display.
- **VAL-06** Catch Up supports since-last-visit and explicit date ranges.
- **VAL-07** Catch Up distinguishes decisions, questions, recommendations, resources,
  and general discussion.
- **VAL-08** Explore provides generated topics, recurring questions, decisions,
  recommendations, links, and files.
- **VAL-09** Members can save answers and source items privately.
- **VAL-10** Owners/moderators can curate, correct, hide, or retire generated community
  knowledge without altering the original source archive.

### Privacy and owner controls

- **CTL-01** Connection scope and current sync status are visible to authorised admins.
- **CTL-02** Owners can pause ongoing ingestion without deleting history.
- **CTL-03** Owners can export the workspace in documented formats.
- **CTL-04** Owners can initiate deletion with clear scope, timing, and recovery period.
- **CTL-05** Members can report a content/privacy concern to workspace administrators.
- **CTL-06** Administrators have an audit trail for role, scope, import, export, and
  deletion changes.
- **CTL-07** Storage consent and external AI-processing consent are separate settings.
- **CTL-08** Community content is not used to train Comvoly or third-party models.

### Usage and subscriptions

- **BIL-01** The pilot records active members, stored content/media, imports, AI usage,
  and estimated infrastructure cost by workspace.
- **BIL-02** Owners see allowances before a limit affects service.
- **BIL-03** A hard usage limit must not corrupt imports or expose partial data.
- **BIL-04** Member access is included in the owner-sponsored pilot workspace.
- **BIL-05** Billing failure degrades to read-only/paused behaviour before deletion.

## 5. Non-functional requirements

### Security

- Tenant isolation is tested at API, retrieval, job, cache, export, and storage layers.
- Sessions are short-lived, revocable, secure, and resistant to cross-site attacks.
- Platform credentials and bot tokens are encrypted and never returned to browsers.
- Object-storage access uses short-lived, workspace-authorised URLs.
- Privileged support access is exceptional, logged, time-bounded, and disclosed.

### Reliability

- Import and connector jobs are resumable.
- User-facing requests do not perform long imports synchronously.
- Failed jobs retry with bounded backoff and a visible terminal state.
- Database and object storage have tested backup/restore procedures.
- Provider outages produce specific status messages rather than generic data loss.

### Performance targets for pilot

- Account/workspace pages: useful content within 2 seconds at the 75th percentile.
- Exact search: results within 2 seconds at the 95th percentile for pilot-scale data.
- Ask: visible progress immediately and typical answer within 15 seconds.
- Catch Up: cached results within 3 seconds; new generation may continue in background.
- Import UI: progress update at least every 10 seconds while work is active.

### Accessibility and device support

- Responsive web experience down to 320px width.
- Keyboard-operable core journeys.
- WCAG 2.2 AA target for production UI.
- Status never communicated by colour alone.
- Plain-language alternatives for platform and processing terminology.

## 6. Analytics events for the pilot

Analytics must avoid message content. Record events such as:

- onboarding started/completed/abandoned by step;
- connection verified or failed by reason code;
- import previewed/confirmed/completed with aggregate counts;
- first search, first cited answer, first catch-up;
- citation opened;
- member invited/verified/returned;
- workspace paused/exported/deletion requested;
- latency, failure class, and aggregate cost.

## 7. Acceptance boundary

The pilot product is not accepted merely because content can be ingested. It is
accepted when a non-technical owner can connect, import, review, invite, operate,
export, and delete, and when an authorised member can reliably find value without
developer intervention.
