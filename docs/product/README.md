# Comvoly v2 product-design package

Status: ready for founder review  
Baseline date: 28 July 2026

This package defines the next Comvoly product without changing the working owner
prototype. It turns the high-level [product blueprint](../../PRODUCT_BLUEPRINT.md) into
requirements, journeys, permissions, connector contracts, import/media behaviour,
screen specifications, pilot criteria, and an implementation sequence.

For phone review, open the consolidated
[Comvoly v2 mobile review PDF](../../output/pdf/comvoly-v2-mobile-review.pdf).

## Documents

1. [Product requirements](PRODUCT_REQUIREMENTS.md)
2. [Experience and screen designs](EXPERIENCE_AND_SCREENS.md)
3. [Low-fidelity screen wireframes](SCREEN_WIREFRAMES.md)
4. [Accounts, identity, and permissions](IDENTITY_AND_PERMISSIONS.md)
5. [Platform connector specifications](CONNECTOR_SPECIFICATIONS.md)
6. [Historical import and media](IMPORT_AND_MEDIA.md)
7. [Pilot and implementation roadmap](PILOT_AND_ROADMAP.md)
8. [Decisions, assumptions, and risks](DECISIONS_AND_RISKS.md)

## Package status

| Area | Status | Main dependency |
|---|---|---|
| Product positioning and scope | Proposed decision | Founder review |
| Owner and member journeys | Designed | Usability testing |
| Account/workspace model | Specified | Identity-provider selection |
| Telegram ongoing connection | Specified | Bot registration and policy review |
| Telegram history import | Specified | Export fixture validation |
| Discord connector | Feasible and specified | Test server and privileged intents |
| Skool connector | Conditional | Approved API/export access |
| Media pipeline | Specified in stages | Storage/provider selection |
| Private pilot | Defined | 3–5 recruited communities |
| Production implementation | Sequenced | Approval of this package |

## Review order

For a concise founder review:

1. Review the decisions in `DECISIONS_AND_RISKS.md`.
2. Walk through the journeys in `EXPERIENCE_AND_SCREENS.md`.
3. Confirm the pilot boundary in `PILOT_AND_ROADMAP.md`.
4. Use the remaining specifications during implementation planning.

## Design boundary

The package intentionally prioritises comprehension, security, history, and member
value over final visual styling. The production UI should use a modern design system,
but visual polish must not conceal missing permissions, uncertain import scope, or
incomplete processing.
