# Decisions, assumptions, and risks

## 1. Decision status

Legend:

- **Accepted direction**: derived from explicit founder discussion; change only with a
  reason.
- **Recommended assumption**: safe working default for design; founder may revise.
- **External dependency**: cannot be declared complete without provider/legal evidence.

## 2. Product decisions

| ID | Decision | Status | Consequence |
|---|---|---|---|
| D01 | One Comvoly account spans owned and joined communities | Accepted direction | Identity is account-level; access is workspace-level |
| D02 | Communities remain separate workspaces by default | Accepted direction | No accidental cross-community retrieval or owner visibility |
| D03 | Community owner/sponsor initially pays; members are included | Accepted direction | Billing attaches to workspace/organisation, not every member |
| D04 | Historical content and media are central to value | Accepted direction | Import is a core launch journey, not a future add-on |
| D05 | Telegram uses history import plus ongoing bot | Recommended assumption | Avoids bot-history gap and persistent personal cloud sessions |
| D06 | Discord is the second supported connector | Recommended assumption | Core connector model must support channels/threads from outset |
| D07 | Skool support is conditional on approved access | External dependency | Do not promise full sync yet |
| D08 | One owner may start from today, but history import remains available | Recommended assumption | Supports quick trials without weakening product promise |
| D09 | Media storage and external AI processing are separate consent choices | Recommended assumption | UI, storage, retrieval, and billing model remain explicit |
| D10 | Community content is not used for model training | Accepted direction | Contracts/provider settings/communications must support promise |
| D11 | Pilot is invitation-only and owner-led | Recommended assumption | Hands-on learning before public self-service |
| D12 | Final visual polish follows journey/security validation | Accepted direction | Build reusable components, but prioritise correct behaviour |
| D13 | Existing prototype remains a demonstration, not pilot identity foundation | Recommended assumption | Avoid extending owner password and Telegram user session |
| D14 | Personal multi-workspace intelligence is later and explicitly scoped | Accepted direction | Foundation supports it without including it in initial pilot |

## 3. Material assumptions requiring review

### A01: First paying segment

Working assumption: established private paid/professional or membership communities
have the strongest pain and willingness to pay.

Validate through owner interviews, not feature usage alone. If voluntary social groups
show much stronger activation but weak willingness to pay, product and go-to-market
segments may differ.

### A02: Telegram Desktop export is acceptable onboarding

Working assumption: an owner can use a desktop export with good guidance for the pilot.

Risk: mobile-only owners or very large archives may find it too difficult. Validate
completion time and abandonment before treating it as scalable self-service. A
temporary local importer remains a possible later convenience, not a committed route.

### A03: Workspace-wide imported scope is sufficient

Working assumption: pilot communities choose content that all authorised Comvoly
members of that workspace may access.

Risk: Discord private channels or mixed-role communities may require per-content ACLs.
Do not import those spaces until entitlement fidelity is designed and tested.

### A04: Owner authority and notice provide an appropriate consent basis

This is not a legal conclusion. Community type, jurisdiction, platform terms, member
expectations, author rights, and AI processors may require stronger consent or exclusion
mechanisms. Obtain appropriate legal/privacy review before external ingestion.

### A05: Managed providers fit pilot economics

Neon, Railway, Cloudflare, identity, object storage, queues, and AI providers should
support low-cost pilot operation, but import/media/AI volumes are unmeasured. Instrument
cost before publishing plans or unlimited allowances.

## 4. Top risks and mitigations

| Risk | Likelihood | Impact | Mitigation / gate |
|---|---|---|---|
| Cross-workspace data leakage | Medium | Critical | Server-side workspace context; negative tests across API/retrieval/jobs/storage/export |
| Telegram terms/AI processing incompatible with design | Unknown | Critical | Written policy/legal review before external pilot; approved import/bot scope only |
| Skool lacks approved historical access | High | High | Conditional roadmap; contact Skool; do not scrape or promise full connector |
| Discord privileged intent not approved at scale | Medium | High | Apply early; keep explicit beta scale/gates; no unsupported fallback |
| Historical export setup is too difficult | Medium | High | Guided usability tests; resumable upload; investigate temporary local importer |
| Owner connects data without adequate member trust | Medium | High | Authority verification, notice preview/posting, reporting/exclusion, transparent settings |
| Media storage/processing costs exceed pricing | Medium | High | Inventory/estimate before processing; opt-in tiers; limits and lifecycle deletion |
| AI answer misrepresents community consensus | Medium | High | Evidence, uncertainty/conflict labelling, owner curation, report flow, quality tests |
| Provider outage/revocation silently makes archive stale | Medium | Medium | Health/freshness labels, alerts, reconcile/reconnect, distinguish retained history |
| Personal multi-community view leaks context | Medium | Critical | Defer until isolation proven; explicit selection; separate retrieval and labels |
| Support staff access sensitive content | Low | High | Time-bound audited support access; owner notification; minimise content access |
| Prototype secrets/session create exposure | Medium | High | Private access, rotation as appropriate, do not onboard others to prototype model |
| Premature visual polish delays core validation | Medium | Medium | Low-fidelity tests and acceptance gates before brand refinement |

Likelihood values are directional and should be revisited after discovery/testing.

## 5. External questions to resolve

### Telegram

- Are the proposed bot, export, storage, retrieval/inference, and member-notice uses
  permitted under current terms?
- What consent, attribution, deletion, sponsored-message, and protected-content duties
  apply?
- Can/should historical export media be processed by external AI providers?
- Which membership checks are reliable for the target group types?

### Discord

- Which privileged intents are required for planned pilot/beta behaviours?
- What application verification timing/evidence is needed?
- How should private channels/forums/threads be excluded or entitled?
- What attachment retention and member-removal obligations apply?

### Skool

- Does an owner-authorised API or comprehensive export expose posts, comments/replies,
  chats, classroom, events, members, media, edits/deletions, and ongoing changes?
- Is third-party storage and AI-assisted retrieval permitted?
- Is there an approved sign-in or membership-verification route?
- Is partnership/private API access available?

## 6. Founder review checklist

Approve or revise:

1. First customer segment
2. Telegram history route
3. Discord beta priority
4. Conditional Skool posture
5. Pilot media-processing boundary
6. Owner/member access model
7. Pilot cohort and exclusions
8. Owner-sponsored commercial model
9. No-training data promise
10. Decision to defer personal cross-community AI until isolation is proven

None of these questions blocks documentation. Items involving platform permission,
legal basis, significant spend, or live-data migration remain implementation gates and
must not be silently assumed.

## 7. Change-control rule

Update this log whenever a decision materially changes scope, permissions, provider
access, data handling, commercial model, or pilot gate. Implementation issues should
reference decision/requirement IDs rather than restating product policy inconsistently.

