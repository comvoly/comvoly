# Platform connector specifications

## 1. Shared connector contract

Every connector implements the same product lifecycle while respecting provider
differences.

### Required capabilities

- authorise and verify an owner/admin;
- discover communities and permitted spaces;
- record owner-selected scope;
- test permissions before import;
- import available history with pagination/resume;
- receive or poll ongoing changes;
- normalise threads, messages, authors, timestamps, edits, replies, and attachments;
- expose stable source IDs and source links;
- verify membership where the provider supports it;
- report connection health without exposing credentials;
- pause, reconnect, change scope, and disconnect;
- describe provider limitations honestly in the UI.

### Normalised connector output

Each item supplies:

- workspace and source-connection context;
- provider/community/space/conversation/item identifiers;
- item type and source URL;
- author source identity and display metadata where permitted;
- created/edited/deleted timestamps;
- text/structured content;
- reply/thread relationships;
- attachment metadata and download reference;
- visibility/scope metadata;
- raw source checksum/version for idempotency;
- ingestion method and timestamp.

The original provider payload may be retained only when necessary, encrypted, covered
by retention policy, and excluded from ordinary application responses.

## 2. Telegram connector

### Product composition

- Branded Comvoly bot for setup, ongoing messages, membership checks, notices, and
  optional commands.
- Owner-provided Telegram Desktop export for historical text and media.
- Possible temporary desktop importer later, subject to policy/legal/security review.

The current persistent personal Telethon session is a prototype mechanism, not the
production customer connection.

### Owner setup

1. Sign in/link Telegram identity.
2. Add bot through a deep link to the intended group.
3. Verify connecting user is authorised and bot has the minimum required status.
4. Record immutable chat identity and display information.
5. Post or preview a member notice.
6. Choose historical import and media settings.
7. Import/review history.
8. Set a cut-over marker so ongoing updates do not duplicate imported items.

### Historical behaviour

The Bot API is not treated as a complete pre-installation history source. Telegram
Desktop JSON export is the launch path. Import maps message IDs, replies, dates,
authors, text, edits where present, and media paths. The importer supports differing
export structures through versioned parsers and fixture tests.

### Ongoing behaviour

- webhook delivery rather than a long polling loop where practical;
- verify Telegram webhook secret and expected bot;
- deduplicate by chat/message ID;
- record edits and deletes when Telegram delivers them;
- download permitted media promptly because provider file availability is not permanent
  storage;
- queue processing separately from webhook acknowledgement;
- use bounded retries and dead-letter handling.

### Minimum permissions and privacy

The bot requests only the access needed to receive authorised group activity and check
membership. Admin status may be required for reliable full-message/membership behaviour,
but unrelated management rights are not requested. The setup screen explains every
requested permission.

### Native experience

- pinned/open-Comvoly button;
- `/ask`, `/catchup`, `/help`, and `/privacy` considered for the pilot;
- detailed answers open on the web with citations;
- bot responses avoid posting sensitive archive excerpts into a group without clear
  invocation and workspace policy.

### Feasibility and policy gate

Before external pilot use, obtain a documented review of Telegram's platform terms,
content licensing/AI restrictions, consent model, bot behaviour, and historical export
processing. Product copy must distinguish retrieval/inference from model training and
must not claim approval Telegram has not granted.

## 3. Discord connector

### Feasibility

Confirmed through Discord's official API: authorised bots can list accessible channels,
retrieve paginated historical messages, enumerate active/public/private archived
threads according to permission, receive ongoing events, and access attachment
metadata/content when permitted.

### Owner setup

1. Link Discord identity with OAuth.
2. Show only servers where the user has suitable authority.
3. Install the Comvoly application/bot with least-privilege permissions.
4. Select included channels, forums, and thread policy.
5. Preview inaccessible/private spaces and exclusions.
6. Confirm history/media scope, estimate import, and begin.

### Required access

- `VIEW_CHANNEL` for selected channels;
- `READ_MESSAGE_HISTORY` for historical import;
- Message Content privileged intent for text, embeds, attachments/components data as
  required;
- Guild Members intent only where needed for member lifecycle at scale;
- send/application-command permissions only for selected native features.

The app must apply for required privileged intents before its scale requires approval.
Loss of intent approval is a launch blocker for features dependent on it.

### Historical behaviour

- enumerate guild channel/space structure;
- include active and permitted archived threads;
- paginate channel/thread messages newest-to-oldest with resumable cursors;
- preserve replies, thread parent, author, roles where permitted, embeds, reactions as
  metadata, and attachments;
- respect channel overwrites and exclude spaces the bot cannot view;
- avoid importing direct messages or unrelated servers.

### Ongoing behaviour

- Gateway connection receives create/update/delete and thread events;
- use resumable sessions, heartbeats, reconnect/backoff, and sequence tracking;
- periodically reconcile missed ranges after reconnect;
- download/store permitted attachments according to policy;
- slash commands `/ask`, `/catchup`, and `/comvoly` open the web experience or provide a
  concise permitted response.

### Membership

Link Discord user subject to the Comvoly account and verify guild membership. Workspace
membership does not automatically reproduce every Discord channel-role restriction in
the pilot; the owner chooses a workspace-wide imported scope. If per-member private
channel fidelity is required later, content-level entitlements must be added before
such channels are imported.

## 4. Skool connector

### Current status

Conditional, not confirmed for full production import. Official Skool documentation
shows a Pro-plan Zapier/API-key facility but does not establish complete approved access
to historical posts, comments, chats, classroom material, and attachments.

### Acceptable routes

One of the following must be validated before a connector is promised:

1. documented official API with sufficient owner-authorised read/event access;
2. official comprehensive owner export suitable for import;
3. written partnership/private API agreement;
4. a narrower approved integration whose limitations still produce a useful product.

### Unacceptable routes

- scraping authenticated pages;
- storing customer browser cookies/passwords;
- undocumented reverse-engineered endpoints as the production dependency;
- claiming continuous sync when only one-time or partial import is available.

### Discovery test matrix

| Content/capability | Must confirm |
|---|---|
| Community posts | Historical list, content, author, date, category |
| Comments/replies | Complete hierarchy and ongoing changes |
| Images/files/links | Metadata, download rights, retention |
| Classroom | Lessons/resources and permission model |
| Chats/DMs | Whether accessible and whether appropriate to import |
| Members | ID, current membership, roles, joins/leaves |
| Events | Historical/upcoming events and changes |
| Identity | Approved member sign-in/linking route |
| Deletions/edits | Event or reconciliation behaviour |
| Limits/terms | Rate limits, data use, AI processing, storage |

### Pilot fallback

If Skool supplies an approved owner export but no continuous API, Comvoly may offer a
clearly labelled one-time or periodic import beta. Membership uses owner invitations
and approval. The UI shows the archive's last refresh time and does not imply live sync.

## 5. Connector health states

All platforms use common user-facing states:

- **Setup required**: connection not complete;
- **Importing**: historical job active;
- **Healthy**: ongoing updates current;
- **Delayed**: provider/retry lag but data is safe;
- **Action required**: expired credential, revoked permission, or owner intervention;
- **Paused**: owner intentionally stopped collection;
- **Disconnected**: no ongoing access; retained archive follows workspace policy.

Health shows last successful event/import, lag, included scope, and a plain-language
next action. It never exposes raw tokens, phone numbers, API secrets, or provider payloads.

## 6. Connector acceptance tests

Each connector must pass:

- permission-denied and partial-scope tests;
- historical pagination and resume after interruption;
- duplicate import and edited-item reconciliation;
- thread/reply reconstruction;
- attachment inventory and failed-download handling;
- ongoing reconnect and missed-event reconciliation;
- source removal and credential revocation;
- member join/leave where supported;
- cross-workspace isolation with identical source IDs;
- pause, reconnect, export, and delete lifecycle;
- cost/rate-limit behaviour at projected pilot volume.

