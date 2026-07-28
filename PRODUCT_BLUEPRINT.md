# Comvoly product blueprint

Status: expanded into a review-ready design package  
Purpose: define the product experience and decisions required before replacing the
technical prototype with a multi-user product.

Detailed specifications and review material are indexed in
[`docs/product/README.md`](docs/product/README.md).

## 1. Product definition

Comvoly is a private intelligence and memory layer for online communities. It turns
authorised community conversations and resources into searchable, cited answers,
catch-up summaries, decisions, recommendations, and reusable knowledge.

Comvoly is not a general-purpose chatbot, a covert monitoring product, or a tool that
trains models on community content. Its value comes from helping permitted members use
knowledge their communities have already created.

### North-star promise

> Connect a community, bring its useful history with you, and make its collective
> knowledge easy for authorised members to find and understand.

### Product principles

1. Historical content is part of onboarding, not an afterthought.
2. A community owner connects a shared community once; ordinary members do not provide
   platform secrets or repeat the import.
3. One person has one Comvoly account across every community and linked platform.
4. Every answer respects source-community permissions and cites its evidence.
5. Communities remain isolated unless a user explicitly performs a permitted personal
   search across communities they can access.
6. Collection, AI processing, retention, export, and deletion are visible and
   controllable.
7. Setup must be achievable by a non-technical community owner without configuration
   files, developer keys, or command-line instructions.

## 2. Target customer and initial wedge

### Recommended first customer

An owner of an established private, knowledge-rich community with repeated questions,
valuable recommendations, and enough activity that members struggle to find prior
answers.

Strong early examples include:

- paid creator and professional communities;
- owners' clubs and specialist interest groups;
- membership associations;
- course and coaching communities;
- resident, parent, and local communities;
- customer and partner communities.

The initial buyer is the community owner, creator, administrator, or sponsoring
organisation. Members receive the shared experience as part of the community plan.

## 3. Account and workspace model

### Comvoly account

A person creates one Comvoly account. They may link several identities:

- Telegram;
- Discord;
- Skool when an approved identity/integration route exists;
- email or Google for recovery and account management.

Linked identities prove who the person is on each source platform. They do not merge
community content or permissions automatically.

### Workspace

Each connected community becomes a separate workspace. A single account can have a
different role in each workspace:

- **Owner**: billing, deletion, platform connection, retention, and all settings;
- **Administrator**: connection management, members, content scope, and reports;
- **Moderator**: content exclusions, corrections, and member support;
- **Member**: uses the permitted archive and personal features;
- **Guest**: optional restricted or time-limited access in a later phase.

### Source connection

A workspace may contain one or more authorised sources, for example:

- one Telegram group;
- selected channels in a Discord server;
- approved spaces from a Skool community;
- additional sources in later releases.

Source identities, messages, attachments, and permissions are normalised into a shared
Comvoly model while retaining the original platform identifiers and links.

## 4. Primary product journeys

### 4.1 New member journey

1. Member follows a community-specific Comvoly invitation.
2. Member signs in or creates one Comvoly account.
3. Member links the identity used in that community.
4. Comvoly verifies current membership or an administrator approves access.
5. Member lands in the relevant workspace.
6. Future visits use the same Comvoly account, including for other communities.

Members never enter bot tokens, API IDs, API hashes, group IDs, or configuration
values.

### 4.2 Returning multi-community member journey

The account home shows:

- communities owned by the user;
- communities joined as a member;
- unread or new catch-ups;
- saved answers;
- followed topics;
- linked-account and notification controls.

The user selects a workspace before asking a question. A later personal feature may
search several authorised workspaces, but only after the user explicitly selects that
scope and the answer labels every source community.

### 4.3 Owner creates a workspace

1. Sign in to Comvoly.
2. Select **Create a community**.
3. Add community name, purpose, logo, and primary platform.
4. Connect the platform using an approved guided flow.
5. Verify administrator authority.
6. Choose channels, topics, date range, and media types.
7. Import historical content.
8. Review privacy, member notice, retention, and AI-processing settings.
9. Watch import progress and review sample results.
10. Invite members and start ongoing synchronisation.

The workspace remains in **Setup** until the owner has reviewed the import and access
policy. It does not silently become available to members.

## 5. Telegram product design

### Decision: use historical import plus an ongoing bot

The existing prototype proves that a Telegram user session can retrieve historical
messages. It is not an acceptable production onboarding method because it requires
technical credentials and leaves a powerful personal session in the cloud.

The production Telegram connection has two complementary parts:

1. **Historical import** brings in the existing archive and selected media.
2. **Comvoly bot** collects new activity, verifies membership, and provides native
   commands after installation.

The bot alone is not presented as a historical-import solution.

### Telegram owner onboarding

1. Owner creates a workspace and selects Telegram.
2. Owner adds the branded Comvoly bot to the group through a Telegram deep link.
3. Comvoly verifies that both the connecting user and bot have the required status.
4. Owner chooses **Start with history** or **Start from today**.
5. The recommended route guides the owner through a Telegram Desktop JSON export with
   selected media.
6. Owner uploads a ZIP or folder using a resumable importer.
7. Comvoly previews message count, date range, member count, and media volume before
   processing.
8. Owner confirms the community notice and data settings.
9. Import runs in the background; errors identify the affected files rather than
   failing the entire archive.
10. Bot continues from the import cut-off without duplicating messages.

### Future import convenience

Investigate a temporary desktop Comvoly Importer using Telegram QR/code authorisation.
It would let the owner select one permitted chat, transfer its archive, and destroy the
temporary session afterwards. This is not built until security, platform-policy, and
legal review are complete.

### Telegram member experience

- sign in/link with Telegram;
- verify membership through the installed bot or administrator approval;
- open Comvoly from a pinned link or bot button;
- use `/ask`, `/catchup`, and `/help` where native commands add value;
- open cited answers on the web for complete context.

## 6. Discord and Skool decisions

### Discord

Discord is the recommended second working connector before a wider launch.

**Feasibility confirmed (28 July 2026):** Discord's official API can enumerate
permitted channels, retrieve historical messages in pages, enumerate active and
archived threads, receive ongoing message events, and expose attachments. The bot must
have `VIEW_CHANNEL` and `READ_MESSAGE_HISTORY`; message text and attachment metadata
also depend on the Message Content privileged intent. Private channels and threads
remain subject to their own permissions. This is a viable, supportable connector.

Owner flow:

1. Connect Discord with OAuth.
2. Select an administered server.
3. Install the Comvoly application/bot.
4. Select permitted channels and threads.
5. Review message-content and member permissions.
6. Import permitted history and begin ongoing event collection.

Member flow:

- link Discord to the existing Comvoly account;
- verify server membership;
- use the web workspace and optional Discord slash commands.

The team must investigate Discord Message Content and Guild Members intent approval
early, before dependence on unapproved production-scale access.

### Skool

Skool is a high-priority commercial segment but not yet a promised full connector.
Official access to posts, comments, classroom resources, member identity, history, and
ongoing events must be verified first.

**Feasibility not yet confirmed (28 July 2026):** Skool officially documents a Pro-plan
Zapier/API-key integration, but its published use cases focus on membership/CRM and
course actions rather than a complete historical export of community posts, comments,
threads, chat, and attachments. Unofficial services claim broader post/comment access,
but Comvoly will not base a production connector on undocumented endpoints, scraping,
or customer browser credentials. A full connector is therefore technically plausible
but commercially conditional on approved access, an adequate owner export, or a Skool
partnership.

Before implementation:

1. interview at least five Skool owners;
2. inspect an owner-authorised test community;
3. test the official Zapier integration and document its available triggers/actions;
4. seek official API or partnership clarification;
5. assess permitted export/import routes;
6. do not scrape pages or request customer passwords.

Skool may enter the pilot through an approved import route before it supports a fully
continuous connector.

## 7. Information architecture and core screens

### Account-level navigation

- **Home**: all communities, catch-ups, followed topics, and recent saved answers;
- **Communities**: owned and joined workspaces;
- **Saved**: personal answers, messages, and collections;
- **Notifications**: digest and topic preferences;
- **Account**: linked identities, security, privacy, and billing relationships.

### Workspace navigation

- **Overview**: important recent activity and suggested questions;
- **Ask**: grounded questions with source citations;
- **Catch up**: configurable summaries since a date or last visit;
- **Explore**: topics, decisions, FAQs, recommendations, links, and files;
- **Search**: exact and semantic retrieval of source content;
- **Saved**: personal and community-curated knowledge;
- **Members**: roles and access, visible to authorised administrators;
- **Settings**: connections, scope, privacy, retention, billing, export, and deletion.

### Owner setup screens

1. Create workspace
2. Choose platform
3. Connect and verify
4. Select content scope
5. Import history
6. Configure media
7. Set access and consent
8. Process and review
9. Invite members
10. Connection health dashboard

## 8. Value features and release priority

### Pilot essentials

1. **Ask with evidence**: answers cite original messages and clearly state uncertainty.
2. **Exact search**: reliable retrieval with filters and original context.
3. **Catch me up**: activity summaries by time range or since last visit.
4. **Community memory**: extracted decisions, recurring questions, and recommendations.
5. **Original context**: source community, date, author where permitted, and source link.
6. **Owner controls**: content scope, access, sync status, export, pause, and delete.

### Later differentiation

- personal cross-community catch-up;
- followed topics and alerts;
- owner-curated answers and corrections;
- recommendation directories;
- action items and volunteer tracking;
- newsletters and shareable summaries;
- multilingual communities;
- organisation-wide administration across many workspaces.

## 9. Media design

### Launch requirement

The importer must recognise and securely retain the relationship between messages and
their photos, documents, links, voice notes, and videos. The owner sees media counts and
estimated processing/storage before confirming an import.

### Staged processing

1. Store permitted media securely and display it with source context.
2. Extract text from common documents and screenshots.
3. Add opt-in image understanding.
4. Add opt-in voice/video transcription.
5. Add retention tiers and storage add-ons.

Media is not automatically sent to an external AI service without a clear workspace
setting. Storage and AI-processing consent are separate choices.

## 10. Trust, privacy, and safety decisions

Before an external pilot, Comvoly must provide:

- a visible community connection notice;
- documented owner authority and source scope;
- least-privilege platform permissions;
- workspace-level access checks on every request;
- encryption in transit and at rest;
- auditable administrator actions;
- retention, export, pause, and deletion controls;
- a process for content exclusion and member concerns;
- clear disclosure of AI providers and processing;
- a contractual commitment not to train models on community content;
- platform-policy and legal review, particularly for historical Telegram data and AI
  processing;
- tested separation preventing information leakage between workspaces.

## 11. Monetisation design

### Initial model

The community owner or sponsoring organisation pays for the shared workspace. Member
access is included, avoiding a paywall during initial adoption.

Plans should ultimately consider active usage, archive/media volume, and AI processing
rather than charging only for total registered membership.

### Expansion

- free trial or limited free workspace;
- paid community tiers;
- professional/creator tier;
- organisation tier for multiple workspaces;
- storage, transcription, imports, branding, and support add-ons;
- optional personal premium for cross-community catch-up, alerts, and larger personal
  allowances.

Member premium must enhance the individual experience without withholding the core
community benefit already purchased by the owner.

## 12. Technical product boundaries

The next architecture uses neutral concepts instead of Telegram-specific product
concepts:

- account and linked identity;
- workspace and membership;
- source connection;
- space/channel/topic;
- conversation/thread;
- message/post/comment;
- attachment and extracted content;
- source permission and source link;
- import/sync run;
- answer and citation;
- subscription and usage allowance.

Every stored item carries a workspace identifier and original source identifier.
Authorisation is applied before retrieval, not merely when results are displayed.

The current prototype remains available as a validation environment while this model is
designed and migrated. Production changes are made through explicit migrations with
backups; the working 61-message test archive is not treated as the final schema.

## 13. Recommended private pilot

### Scope

- 3 to 5 owner-led communities;
- Telegram first, with at least one Discord integration during the pilot;
- historical import required for at least two established communities;
- 10 to 50 active test members across workspaces;
- no public self-service launch until access isolation and deletion are tested.

### Success measures

- non-technical owner completes connection/import with minimal live assistance;
- at least 90% of selected historical text imports successfully;
- media inventory matches the source export within an agreed tolerance;
- no cross-workspace access failures;
- cited answers are judged useful and supported by evidence;
- members return for catch-up or answers without owner prompting;
- owner reports fewer repeated questions or faster retrieval of prior knowledge;
- infrastructure and AI cost per active workspace is measured.

### Pilot exit criteria

The product is ready for a broader beta only when owners can connect, import, review,
invite, pause, export, and delete without developer intervention.

## 14. Delivery sequence

### Phase A: product and risk definition

1. Confirm the founder decisions below.
2. Create low-fidelity screen flows and test them with prospective owners.
3. Validate Telegram policy/legal approach and Discord intents.
4. Conduct Skool owner discovery.

### Phase B: multi-tenant foundation

1. Accounts and linked identities
2. Workspaces, roles, and membership checks
3. Neutral source/message schema
4. Audit, retention, deletion, and usage foundations

### Phase C: owner onboarding

1. Telegram bot setup
2. Historical ZIP/JSON/media importer
3. Import review and progress
4. Member invitation and verification
5. Connection health

### Phase D: member value

1. Ask and exact search
2. Catch up
3. Explore decisions, FAQs, and recommendations
4. Saved answers and personal preferences

### Phase E: additional connectors and pilot

1. Discord connector
2. Skool approved experiment
3. Pilot analytics and support process
4. Pricing test

## 15. Founder decisions to confirm

The recommended defaults are shown first.

1. **Initial segment**: established private paid/professional communities; broaden after
   pilot.
2. **Launch platforms**: production-quality Telegram plus Discord beta; Skool discovery
   or approved import beta.
3. **Telegram history**: owner-uploaded Telegram Desktop export at launch; investigate a
   temporary importer later.
4. **History requirement**: an owner may start from today, but the product must offer a
   usable historical-import path before wider launch.
5. **Media launch scope**: securely store/display permitted media and extract document/
   screenshot text; defer broad video transcription.
6. **Member access**: linked platform membership where reliable, with invitation/admin
   approval as fallback.
7. **Cross-community use**: separate workspaces by default; personal multi-workspace
   views are explicit and never available to community owners across unrelated groups.
8. **Commercial model**: owner-sponsored workspace with included member access; personal
   premium later.
9. **Pilot posture**: invitation-only with 3 to 5 communities and hands-on founder
   onboarding.
10. **Data promise**: no training on community content, transparent processors, and full
    owner export/deletion.

## 16. Explicitly out of scope for the next build

- native mobile applications;
- public community discovery;
- advertising or sale of community data;
- autonomous moderation or member scoring;
- unsupported scraping of platforms;
- invisible ingestion without community-owner authorisation;
- automatic blending of unrelated community archives;
- full enterprise compliance certification before the private pilot.
