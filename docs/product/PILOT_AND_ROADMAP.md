# Private pilot and implementation roadmap

## 1. Delivery objective

Produce an invitation-only multi-community pilot that proves a non-technical owner can
connect useful history and that authorised members repeatedly use cited answers,
catch-up, and discovery.

The existing one-owner cloud prototype remains a demonstration and data fixture. It is
not incrementally exposed as the multi-user pilot without the account/workspace
security foundation.

## 2. Pilot cohort

### Target

- 3–5 owner-led private communities;
- 10–50 active members overall initially;
- at least two established Telegram communities with history/media exports;
- one Discord test community during the pilot;
- Skool owner discovery and approved import experiment only if access is validated.

### Recruitment profile

Choose owners who:

- personally feel the lost-knowledge/repeated-question problem;
- have authority and member trust;
- will complete onboarding with observation;
- have a meaningful archive, not only a newly created test group;
- agree to provide structured feedback and report member concerns;
- are not initially handling highly regulated or safety-critical data.

Avoid early medical, legal-case, safeguarding, employee-surveillance, or similarly
high-risk communities until governance is stronger.

## 3. Pilot stages

### Stage 0: founder prototype safety

- preserve current working prototype;
- add appropriate private access/rate limiting before sharing;
- verify backups and spend alerts;
- rotate secrets when required;
- do not onboard outside users into the owner-password model.

### Stage 1: internal product foundation

- accounts and linked identities;
- workspaces, roles, membership, and tenant isolation;
- neutral source/content/media schema;
- audit, job, usage, retention, export/deletion foundations;
- automated isolation/security tests.

Exit: two test accounts/workspaces cannot access each other's content through API,
retrieval, jobs, exports, or media URLs.

### Stage 2: founder Telegram workspace

- bot setup and webhook pipeline;
- Telegram Desktop export parser/upload;
- import preview/progress/review;
- media inventory/storage and initial extraction;
- Ask/Search migrated to workspace authorisation;
- connection health and owner controls.

Exit: founder can rebuild the existing test workspace through the new non-technical
flow without environment variables or personal cloud session.

### Stage 3: invited member experience

- invitation, account, identity linking, verification/approval;
- account home and workspace switcher;
- member Overview, Ask, Search, Catch Up, Explore, Saved;
- reporting/privacy/help;
- owner member/role management.

Exit: at least five invited testers complete access and value tasks without developer
intervention; no isolation failures.

### Stage 4: external Telegram pilot

- onboard 2–4 additional Telegram communities with observed setup;
- measure import fidelity, time-to-value, repeated usage, answer quality, support load,
  and costs;
- operate export/deletion drills;
- revise onboarding and limits.

### Stage 5: Discord beta

- Discord OAuth/install/channel scope;
- history/threads/attachments and Gateway events;
- membership verification and optional slash commands;
- privileged intent/verification readiness.

### Stage 6: pricing and broader beta readiness

- test owner willingness to pay and plan language;
- implement billing only after usage/cost measurements;
- publish privacy/security/support materials;
- broader beta only after pilot exit criteria pass.

## 4. Implementation workstreams

### Workstream A: product platform

1. Database migrations and repository/service boundaries
2. Account session/identity provider
3. Workspace membership/capability enforcement
4. Audit and usage events
5. Background job/queue framework
6. Object storage and authorised delivery

### Workstream B: ingestion

1. Connector interface and normalised content model
2. Telegram bot webhooks
3. Export upload/inventory/parser
4. Deduplication, edits, cut-over, and reconciliation
5. Media storage/extraction
6. Health, retries, and owner reports

### Workstream C: member value

1. Workspace-scoped exact/semantic retrieval
2. Cited Ask
3. Catch Up
4. Explore extraction/curation
5. Search/source context
6. Saved items/preferences

### Workstream D: trust and operations

1. Platform/legal/privacy review
2. Consent/notice/retention policies
3. Export/deletion and support controls
4. Monitoring, backups, incident response
5. Spend/usage limits
6. Pilot analytics and feedback

## 5. Milestones and acceptance

### M1: design approved

- founder accepts product decisions and journey;
- usability test script prepared;
- Telegram/Discord/Skool feasibility labels accepted;
- no major production rewrite started prematurely.

### M2: secure multi-tenant skeleton

- account/workspace/role flows work;
- isolated test fixtures and automated negative tests;
- no Telegram-specific field required in the core domain model;
- audit and migration/backup procedures work.

### M3: history-to-value

- non-technical Telegram export upload;
- preview and owner confirmation;
- reliable text/media import with report;
- cited Ask/Search over the imported workspace;
- bot continues without duplicates.

### M4: member-ready pilot

- one account can access several authorised workspaces;
- invitation and membership lifecycle work;
- Catch Up/Explore produce cited useful outputs;
- owner can manage, pause, export, and delete;
- accessibility/performance baselines pass.

### M5: connector expansion

- Discord history/threads/ongoing/member proof works;
- Skool go/no-go based on approved evidence;
- shared connector tests pass.

## 6. Pilot measurements

### Onboarding

- owner completion rate and time by step;
- assistance required;
- import preview-to-confirmation rate;
- import success/partial/failure counts;
- time from account creation to first useful cited result.

### Member value

- invitation-to-active rate;
- first Search/Ask/Catch Up completion;
- weekly returning members;
- citation-open rate;
- saved items/followed topics;
- member-rated answer support/usefulness;
- owner-reported repeated-question reduction.

### Trust and quality

- access/identity support incidents;
- reported content concerns and resolution time;
- unsupported or misleading answer reports;
- source freshness/connector lag;
- cross-workspace leakage attempts/results;
- export/deletion completion time.

### Economics

- storage by workspace and content class;
- processing and AI cost per import/active member/question;
- background connector cost;
- support time per onboarding;
- owner willingness-to-pay range and preferred metric.

## 7. Go/no-go gates

### Telegram external pilot

Go only with:

- documented policy/legal assessment;
- clear member notice and owner authority;
- working history/media import, pause, export, deletion;
- no persistent personal customer Telegram session in Comvoly cloud;
- tenant isolation and secure media delivery tests.

### Discord external pilot

Go only with:

- approved/configured required intents;
- least-privilege install and channel scope;
- historical and ongoing reconciliation tests;
- clear handling of private channels/threads and membership.

### Skool connector

Go only with official documented API/export or written partnership approval adequate for
the advertised scope. Otherwise maintain discovery/waitlist or a clearly labelled
owner-provided import experiment.

## 8. Recommended implementation order

1. Approve design package and test low-fidelity journeys with 3–5 owners/members.
2. Select managed identity, queue, and object-storage approach within existing cost
   constraints.
3. Design versioned database migrations and tenant-isolation tests.
4. Build accounts, linked identities, workspaces, membership, and audit.
5. Build resumable import jobs and Telegram export fixtures/parser.
6. Build bot setup/webhooks and history cut-over.
7. Migrate Ask/Search behind workspace authorisation.
8. Build owner review, member invitation, and account/workspace navigation.
9. Add Catch Up/Explore and initial media extraction.
10. Run founder/new-community pilot, then Discord beta.

## 9. Work deliberately deferred

- final brand/visual polish;
- native mobile apps;
- public self-service acquisition funnel;
- automated Skool scraping;
- personal cross-community AI until workspace isolation is proven;
- complex per-message source-platform ACL mirroring;
- enterprise SSO/compliance certification;
- advertising or community-data monetisation.

