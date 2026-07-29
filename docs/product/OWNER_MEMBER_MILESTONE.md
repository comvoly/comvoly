# Owner workspace and invited-member milestone

Status: implemented and locally verified on 29 July 2026; isolated development
deployment and founder acceptance testing are the remaining release steps.

## Outcome

This milestone turns a registered identity into a usable multi-community account
without connecting a production platform or weakening workspace isolation.

An authenticated owner can:

- create an empty community workspace with a unique handle;
- switch between every owned and joined workspace;
- see role and server-derived capabilities for the selected workspace;
- complete the five owner setup steps;
- create draft planning records for Telegram, Discord, or Skool;
- see the future historical-import progress area;
- create a 72-hour invitation for a member, moderator, or administrator; and
- copy a single-use invitation URL.

An invited person can sign in or register once, follow the invitation URL, join the
intended workspace and switch between it and their other communities. Registration
without an invitation continues to grant no community access.

## Security decisions

- Workspace creation remains controlled by the server environment gate. It will be
  enabled only in the isolated development environment for this acceptance test.
- Every workspace read and mutation derives the principal from a verified managed
  identity token and re-authorises the requested workspace server-side.
- Missing access and missing workspaces both return the same concealed response.
- Invitation tokens are returned once, stored only as SHA-256 hashes, expire after 72
  hours and cannot grant ownership.
- Member roles cannot create sources, change owner setup, invite members or inspect
  another workspace.
- Source planning records contain no platform credentials and do not claim that a
  platform has been connected. Production connectors remain out of scope.
- The optional invitation email is only a reminder hint in this milestone. No email is
  sent and it is not used as authentication or authorisation evidence.

## API surface

- `GET /v2/session`
- `POST /v2/workspaces`
- `GET /v2/workspaces/{workspace_id}`
- `POST /v2/workspaces/{workspace_id}/setup/{step_key}`
- `POST /v2/workspaces/{workspace_id}/sources`
- `GET /v2/workspaces/{workspace_id}/members`
- `POST /v2/workspaces/{workspace_id}/invitations`
- `POST /v2/invitations/accept`

Workspace overview responses include only that authorised workspace's setup steps,
sources and latest import jobs. The UI never supplies a role or capability decision.

## Verification

Automated coverage includes:

- owner workspace creation and duplicate-handle rejection;
- initial setup-step creation;
- source planning and setup progress;
- member rejection from owner-only controls;
- scoped overview data with a second workspace fixture;
- managed-identity workspace-creation gating;
- hashed invitation storage and invitation acceptance; and
- the existing retrieval, jobs, export, media, usage and audit isolation suite.

## Explicitly deferred

- platform OAuth/bot registration or credentials;
- Telegram, Discord or Skool production connectors;
- archive upload and import execution;
- email delivery;
- role editing, suspension, ownership transfer and billing;
- production authentication or production workspace migration; and
- migrating the existing prototype archive.

The next implementation milestone should be the founder Telegram workspace: a guided
bot setup plus Telegram export import, progress/review and workspace-authorised Ask and
Search. That milestone requires explicit external bot/application and data-processing
decisions before production connection.
