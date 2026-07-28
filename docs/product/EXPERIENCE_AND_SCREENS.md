# Experience and screen designs

## 1. Experience principles

- **Start with value:** explain what the owner/member receives before requesting access.
- **Progressive disclosure:** show only the next decision, with details available when
  needed.
- **No developer language:** no API IDs, hashes, source IDs, environment variables, or
  command-line instructions.
- **History is visible:** owners always understand whether the workspace includes old
  content, starts today, or is out of date.
- **Permission before processing:** scope and media/AI choices precede import.
- **Evidence before confidence:** answers lead naturally to original context.
- **One account, clear boundaries:** switching communities is easy; mixing them is never
  accidental.
- **Recoverable setup:** progress survives interruptions and explains failures.

## 2. Navigation model

### Account navigation

- Home
- Communities
- Saved
- Notifications
- Account

### Workspace navigation

- Overview
- Ask
- Catch Up
- Explore
- Search
- Saved
- Members (authorised roles)
- Settings (authorised roles)

Desktop uses a compact sidebar. Mobile uses a bottom or menu-based primary navigation,
with workspace switcher always clearly accessible.

## 3. Account entry journey

### Screen A01: Welcome/sign in

**Purpose:** establish the one-account promise.

Content:

- “One account for the communities you own and belong to.”
- primary managed sign-in option;
- Telegram/Discord linking is explained as the next step when needed;
- privacy and terms links;
- invitation context if the user followed a workspace link.

States: new account, returning account, expired invitation, provider failure, account
conflict, account suspended.

### Screen A02: Account home

**Purpose:** orient a returning multi-community user.

Sections:

- owned/administered communities;
- joined communities;
- new catch-ups;
- recent saved items;
- create/join community action;
- incomplete setup or connection-health alerts.

Community tile shows role, platform(s), last activity/catch-up, and attention state—not
private content excerpts from another workspace by default.

### Screen A03: Link identities

**Purpose:** connect provider identities safely.

Rows for Telegram, Discord, recovery identity, and conditional Skool. Each shows linked
account, verification time, usage (which memberships depend on it), and unlink action.
Unlinking previews affected workspace access and requires reauthentication.

## 4. Owner onboarding journey

### O01: Create community

Fields: name, purpose, logo, time zone, owner role confirmation. Explain that the
workspace is private during setup.

Primary action: **Choose platform**.

### O02: Choose platform

Options:

- Telegram: available; bot plus history import;
- Discord: beta; authorised server/channel import;
- Skool: availability/waitlist until approved access is confirmed.

Do not present unavailable integrations as working connections.

### O03-T: Connect Telegram

Explain the two parts:

1. Add Comvoly for new activity and membership.
2. Bring an export for previous history.

Action opens Telegram deep link. Return state verifies group, owner/admin authority,
bot status, and community name. Permission details are expandable in plain language.

### O03-D: Connect Discord

OAuth server selection, bot install, then channel selector. Show accessible/inaccessible
spaces and permission reasons. Private channels default off.

### O04: Select content scope

Show selected community and hierarchical spaces/topics. Controls:

- include/exclude channels/topics;
- history date range;
- message text/links;
- media classes;
- author display policy;
- ongoing collection status.

Update an aggregate estimate as scope changes.

### O05: Historical import

Telegram: illustrated export instructions plus drag/drop/resumable upload. Discord:
history is fetched directly after scope confirmation. Skool: approved import only.

Offer **Start from today** but explain the resulting limitation without shaming the
owner. Historical import remains accessible later.

### O06: Import preview

Show source match, date range, counts, media bytes/types, overlap, omissions, estimated
storage/processing, and policy selections. Owner must actively confirm.

### O07: Access and community notice

Choose verified-platform membership, invite-only, or admin approval fallback. Preview
the member notice. Configure retention, external media processing, concern reporting,
and initial administrator-only review.

### O08: Processing

Stage-based progress, aggregate counts, warnings, leave-page reassurance, cancel/retry.
Bot/ongoing connection status is separate from historical progress.

### O09: Owner review

Before activation:

- sample exact searches;
- suggested questions and cited answers;
- detected topics/FAQs/recommendations;
- excluded/failed items;
- connection health;
- member-access summary.

Actions: adjust scope, retry items, curate sample knowledge, activate workspace.

### O10: Invite and launch

Create invitation/pinned link, preview member arrival, post community notice, choose
digest defaults, and open active workspace. Show a short launch checklist.

## 5. Member arrival journey

### M01: Community invitation

Show community identity, owner/sponsor, connected platform, archive coverage, member
benefits, privacy summary, and **Continue to Comvoly**.

Do not show archive content before authorisation.

### M02: Sign in or use existing account

Returning members continue with their Comvoly account. New members create one. The page
preserves invitation context throughout authentication.

### M03: Link/verify platform identity

If the required Telegram/Discord identity is not linked, explain why it is needed and
what is shared. Verify membership. If automatic proof is unavailable, show
administrator-approval state and expected next step.

### M04: Member welcome

Show what is available:

- archive date coverage and last sync;
- Ask, Catch Up, Explore, Search;
- citation/privacy explanation;
- digest preference;
- three useful suggested actions.

Primary action: **Catch me up** or **Ask a question**, selected based on available
history and recent activity.

## 6. Member value screens

### W01: Workspace overview

Sections:

- catch-up since last visit;
- important recent decisions/questions/resources;
- suggested questions;
- followed topics;
- connection/archive freshness;
- owner-curated knowledge.

Avoid vanity message counts as the dominant experience. Lead with useful community
knowledge.

### W02: Ask

Components:

- question field and optional scope/date filters;
- example questions drawn from available topics;
- progress state with cancel/new-question option;
- concise answer;
- inline citation markers;
- evidence list with original context;
- uncertainty/conflict notices;
- save, refine, report, and open-source actions.

The answer never implies certainty beyond its evidence.

### W03: Catch Up

Controls: since last visit, today, 7 days, custom range; optional spaces/topics.

Output groups:

- decisions;
- questions needing answers;
- recommendations;
- useful links/files;
- notable discussion;
- actions/volunteers where supported.

Every item opens supporting messages. Members can follow a topic or save an item.

### W04: Explore

Browse topics, recurring questions, decisions, recommendations, links, files, and
curated collections. Show generated versus owner-curated status. Filters remain
workspace-scoped.

### W05: Search

Exact and semantic modes are understandable rather than technical:

- **Find messages** for words/phrases and filters;
- **Find discussions about** for meaning-based discovery.

Result includes source space, date, author where permitted, excerpt, attachment, reply
context, and open-original action.

### W06: Source context

Displays the cited message/post and surrounding permitted conversation. Clearly label
provider, community, channel/topic, date, edits, attachments, and whether context is
missing. Avoid reconstructing content the user is not authorised to view.

### W07: Saved

Private saved answers/items and optional user-created collections. Saving does not copy
content outside its workspace permission; losing access makes source content
unavailable.

## 7. Owner operations screens

### S01: Connection health

Provider, included scope, historical coverage, last ongoing update, current lag,
warnings, credential/permission state, pause/reconnect/change-scope actions.

### S02: Members and roles

Active, pending, suspended, and departed members; admission method; last verification;
role and capability controls; invitation management; audit history.

### S03: Content and AI settings

History/source scope, media types, external processing choices, author display,
generated-feature toggles, exclusion rules, reprocessing implications.

### S04: Usage and plan

Active members, stored text/media, processing and AI usage, current allowance, forecast,
alerts, hard-limit behaviour, and plan/billing ownership.

### S05: Export and deletion

Export contents/formats/progress. Pause/disconnect distinction. Workspace deletion
impact, cooling-off period, backup expiry, reauthentication, typed confirmation, and
final audit receipt.

## 8. Global states

Every value screen accounts for:

- loading with useful skeleton/progress;
- empty but correctly connected;
- setup incomplete;
- import processing;
- source delayed/action required/paused;
- no search results;
- insufficient evidence;
- provider or AI temporary outage;
- access pending/suspended/revoked;
- usage allowance reached;
- partial media failure;
- mobile/narrow layout.

Generic “cannot reach backend” is replaced with a specific state and safe next action.

## 9. Content design vocabulary

Prefer:

- community, workspace, connection, history, message, discussion, original source;
- “Bring previous history” rather than “backfill”;
- “Connect Telegram” rather than “create session”;
- “Comvoly is preparing your archive” rather than “embedding/indexing pipeline”;
- “Checked against 18 messages” rather than internal retrieval terminology.

Avoid claims such as “Comvoly knows” where the archive may be partial. Use “Based on
the connected community history…” and display coverage/freshness.

## 10. Visual direction for later refinement

Modern, calm, premium, and trustworthy. Use generous spacing, strong typography,
restrained colour, clear information hierarchy, and subtle motion. The design should
feel like a polished knowledge product rather than a technical admin console.

Visual refinement follows journey validation, but implementation should start with
reusable tokens/components so polish does not require another structural rewrite.

## 11. Usability test script

Give a prospective owner the low-fidelity flow and ask them to:

1. create a community;
2. explain what the bot and history import each do;
3. decide whether images are stored/processed;
4. identify who can access the workspace;
5. find when members will be invited;
6. pause collection and locate deletion/export.

Give a prospective member the member flow and ask them to:

1. join using an existing Comvoly account;
2. explain why a platform identity is requested;
3. catch up since last visit;
4. inspect evidence for an answer;
5. switch communities without combining them;
6. locate privacy/help and leave the workspace.

Measure completion, hesitation, incorrect mental models, assistance required, and trust
concerns. Revise wording/sequence before visual polish or production build.

