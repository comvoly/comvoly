# Accounts, identity, and permissions

## 1. Model summary

One human has one Comvoly account. Platform identities, workspace memberships, and
source permissions are separate records.

```text
Account
  -> linked identities (Telegram, Discord, recovery identity)
  -> workspace memberships (role and state per community)
  -> personal preferences and saved items

Workspace
  -> memberships
  -> source connections
  -> content, media, answers, citations, imports, and usage
```

This separation allows one person to own a Telegram community, moderate a Discord
server, and join other communities without creating several Comvoly accounts or
combining their data.

## 2. Core records

### Account

Minimum fields:

- internal account ID;
- display name and optional avatar;
- status: pending, active, suspended, deletion_pending, deleted;
- primary recovery identity;
- locale/time zone;
- created/last-active timestamps;
- accepted policy versions.

Email is not assumed to be the permanent account key. Accounts are referenced only by
an internal immutable ID.

### Linked identity

- identity ID and account ID;
- provider: Telegram, Discord, Google, email, or future provider;
- provider subject/user ID;
- provider display metadata;
- verification timestamp and method;
- token reference where required, never a token in application responses;
- token expiry/refresh state;
- last membership-verification timestamp;
- linked, revoked, or conflicted state.

The pair `(provider, provider subject)` is unique. Linking an identity already attached
to another account triggers account-recovery/support resolution rather than silent
merging.

### Workspace

- immutable workspace ID;
- name, handle, logo, purpose, and time zone;
- lifecycle: setup, importing, review, active, paused, read_only, deletion_pending,
  deleted;
- owning account/organisation;
- retention and processing policy versions;
- subscription and usage-policy reference.

### Workspace membership

- workspace ID and account ID;
- role;
- state: invited, verification_pending, active, suspended, left, revoked;
- admission method and approving account where applicable;
- source identity used for membership proof;
- proof/verification timestamp and next recheck;
- joined, last-active, suspended, and revoked timestamps.

Membership is unique per account/workspace. Role changes and overrides are audited.

### Source connection and source scope

The connection stores the workspace, provider, external community ID, credential
reference, state, health, and authorised scope. Scope records identify included and
excluded channels/topics/spaces plus media and history permissions.

## 3. Authentication design

### Recommended pilot approach

- Managed OpenID Connect identity for account sessions and recovery.
- Telegram and Discord linked as platform identities using their approved login/OAuth
  flows.
- One secure Comvoly browser session independent of individual provider tokens.
- Step-up reauthentication before linking/unlinking identities, exporting a workspace,
  changing ownership, or deleting data.

The current single owner-password cookie is retained only for the isolated prototype.
It is not extended into multi-user production.

### Account creation

1. User follows a general or workspace invitation link.
2. User selects an approved sign-in method.
3. Comvoly creates or resumes the account.
4. If the invitation requires another platform identity, the user links it next.
5. Comvoly validates membership/approval and activates the workspace membership.

### Identity linking

1. User starts linking from Account settings or an invitation.
2. Comvoly creates a short-lived signed linking transaction tied to the current
   account/session.
3. Provider authenticates the user and redirects to the fixed callback.
4. Backend validates state, nonce, signature/token, time, audience, and provider subject.
5. Conflict checks run before the identity becomes active.
6. Security notification and audit event are generated.

## 4. Roles and capabilities

Legend: **Yes** allowed, **Limited** scoped/conditional, **No** denied.

| Capability | Owner | Administrator | Moderator | Member |
|---|---:|---:|---:|---:|
| Use Ask/Search/Catch Up/Explore | Yes | Yes | Yes | Yes |
| View permitted original evidence | Yes | Yes | Yes | Yes |
| Save personal items | Yes | Yes | Yes | Yes |
| Curate community knowledge | Yes | Yes | Yes | No |
| Review content concerns | Yes | Yes | Yes | No |
| Invite/approve members | Yes | Yes | Limited | No |
| Change roles | Yes | Limited | No | No |
| Connect/pause sources | Yes | Yes | No | No |
| Change source scope | Yes | Yes | No | No |
| Import historical content | Yes | Yes | No | No |
| Change retention/AI processing | Yes | Limited | No | No |
| View aggregate workspace usage | Yes | Yes | Limited | No |
| Manage billing | Yes | No | No | No |
| Export complete workspace | Yes | Limited | No | No |
| Transfer ownership | Yes | No | No | No |
| Delete workspace | Yes | No | No | No |

An administrator's `Limited` capabilities may require explicit owner-granted permission.
There must always be at least one active owner. The final owner cannot leave without
transferring ownership or deleting the workspace.

## 5. Admission and ongoing access

### Supported admission methods

1. Verified membership through a linked platform identity.
2. Workspace invitation plus platform verification.
3. Administrator approval when reliable provider verification is unavailable.
4. Organisation-managed access in a later release.

Invitation links are scoped, expiring, revocable, and never grant content access until
the membership becomes active.

### Membership revalidation

- Recheck on sensitive requests when proof is stale.
- Recheck periodically in the background.
- Consume provider member-left/removed events when available.
- Gracefully handle provider outages without permanently granting access.
- Suspend access after confirmed departure; do not delete the person's Comvoly account.
- Preserve personal saved-item references only where policy permits; inaccessible source
  content is no longer displayed.

### Telegram caveat

Telegram membership lookup is most reliable when the Comvoly bot is an administrator.
If membership cannot be proven, administrators may approve members during the pilot,
with an explicit `admin_approved` admission method and periodic review queue.

### Discord caveat

Discord OAuth and guild membership provide a strong linking route. Private-channel
access must not be inferred from general server membership; imported channel scope and
Comvoly workspace access remain separate decisions.

### Skool caveat

Until an approved member-identity API exists, Skool membership cannot be represented as
automatically verified. Pilot access must use owner/admin invitation and approval, and
must be labelled accordingly.

## 6. Permission enforcement rules

1. Resolve account session.
2. Resolve active workspace membership.
3. Check role/capability for the requested action.
4. Apply workspace ID to every database/retrieval/job/storage operation.
5. Apply optional source-space restrictions.
6. Return only fields permitted by author-display and media policy.
7. Emit an audit/security event for sensitive operations.

Workspace ID must come from the authorised server-side context, not be trusted merely
because a browser submitted it.

Background jobs carry a signed/internal job identity plus workspace and source scope.
They may not process an unscoped queue message.

## 7. Personal cross-community features

The personal account layer may later search or summarise several active memberships,
subject to these rules:

- user explicitly selects included workspaces;
- retrieval executes separately within each workspace boundary;
- citations name their workspace and source;
- no combined result is written back into a community workspace automatically;
- workspace owners receive no visibility into unrelated selections or results;
- loss of membership removes that workspace from future personal retrieval.

## 8. Audit and support access

Audit events cover:

- identity link/unlink and conflicts;
- account recovery and session revocation;
- member invitation, approval, suspension, and role change;
- source connection/scope and processing-policy change;
- imports, exports, ownership transfer, pause, and deletion;
- exceptional operator access.

Logs record actor, workspace, action, timestamp, outcome, and non-secret reason. They do
not duplicate message content.

Operator access requires a support case, least privilege, time limit, explicit reason,
and audit trail. Pilot owners should be notified when support accessed community data.

