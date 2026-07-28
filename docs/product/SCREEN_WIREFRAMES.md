# Low-fidelity screen wireframes

These wireframes define hierarchy and actions, not final styling. Responsive layouts
stack navigation and secondary columns on narrow screens.

## 1. Account home

```text
+-----------------------------------------------------------------------+
| COMVOLY        Home  Communities  Saved  Notifications       [Account]|
+-----------------------------------------------------------------------+
| Good morning, Stephen                         [Create a community]      |
| One account for everything you own and belong to                      |
|                                                                       |
| NEEDS ATTENTION                                                       |
| [Jersey Tesla Owners]  Import ready for review          [Review]      |
|                                                                       |
| YOUR COMMUNITIES                                                      |
| [Jersey Tesla Owners]  Owner   Telegram   Catch-up ready [Open]       |
| [Creator Network]      Member  Skool      Approval/import state       |
| [EV Engineering]       Member  Discord    14 new topics  [Open]       |
|                                                                       |
| RECENT CATCH-UPS                    SAVED                              |
| [Community + summary + evidence]    [Saved answer + community label]  |
+-----------------------------------------------------------------------+
```

Decision: tiles show role/platform/freshness, not private excerpts from other
communities. The account page never implies that unrelated workspaces share data.

## 2. Create community and choose platform

```text
+---------------------------------------------------------------+
| Create your community                              Step 1 of 7|
| It remains private while you set it up.                        |
|                                                               |
| Community name [________________________________________]      |
| Purpose        [________________________________________]      |
| Your role      [Owner or administrator                v]      |
|                                                               |
|                                              [Continue]        |
+---------------------------------------------------------------+

+---------------------------------------------------------------+
| Where is your community?                           Step 2 of 7|
|                                                               |
| [TELEGRAM]                  [DISCORD beta]                     |
| Bot + previous history     Server channels + history          |
|                                                               |
| [SKOOL availability]                                          |
| Approved connection/import required                            |
|                                                               |
| [Back]                              [Continue with Telegram]   |
+---------------------------------------------------------------+
```

## 3. Telegram connection

```text
+---------------------------------------------------------------+
| Connect Telegram safely                            Step 3 of 7|
|                                                               |
|  1  Add Comvoly to the group                                  |
|     Collects new authorised activity and verifies members.    |
|                                                               |
|  2  Bring previous history                                    |
|     Upload an owner-created Telegram Desktop export.          |
|                                                               |
| [Open Telegram and add Comvoly]                               |
|                                                               |
| VERIFIED                                                      |
| Community: Jersey Tesla Owners                                |
| Your authority: Administrator                                 |
| Comvoly access: Ready                                         |
|                                                               |
| [Back]                                    [Choose content]     |
+---------------------------------------------------------------+
```

## 4. Scope and historical import

```text
+---------------------------------------------------------------+
| Choose what Comvoly can use                         Step 4 of 7|
|                                                               |
| History       [All available history v]                       |
| Messages      [x] Text  [x] Links                             |
| Media         [x] Images [x] Documents [ ] Voice/video        |
| Author names  [Visible to authorised members v]               |
|                                                               |
| Ongoing collection begins when setup is confirmed.            |
| [Back]                                    [Import history]     |
+---------------------------------------------------------------+

+---------------------------------------------------------------+
| Bring previous history                                        |
|                                                               |
| [ Illustrated Telegram Desktop export instructions ]          |
|                                                               |
| +-----------------------------------------------------------+ |
| | Drop exported ZIP/folder or choose from this computer     | |
| +-----------------------------------------------------------+ |
|                                                               |
| [Start from today]                           [Use this export] |
+---------------------------------------------------------------+
```

## 5. Import preview and access

```text
+---------------------------------------------------------------+
| Review before processing                           Step 5 of 7|
|                                                               |
| Jan 2021–today | 48,216 messages | 3,408 files | 2 warnings   |
|                                                               |
| Included: text, links, images, documents                       |
| Excluded: videos, protected/missing files                      |
| Estimated storage/processing shown against plan allowance     |
|                                                               |
| [Change scope]                           [Confirm import]       |
+---------------------------------------------------------------+

+---------------------------------------------------------------+
| Access and community notice                        Step 6 of 7|
|                                                               |
| Access [Verified Telegram members + invited admins v]          |
| Retention [While workspace is active v]                        |
| [x] Post a clear connection notice                             |
| [x] Allow members to report content concerns                   |
| [ ] Enable external OCR for selected images                    |
|                                                               |
| Workspace remains administrators-only during review.          |
| [Back]                               [Start secure import]      |
+---------------------------------------------------------------+
```

## 6. Import progress and owner review

```text
+---------------------------------------------------------------+
| Preparing Jersey Tesla Owners                                 |
|                                                               |
| [complete] Upload and validate                                 |
| [complete] Parse messages                                     |
| [active  ] Store media              2,341 / 3,408              |
| [waiting ] Extract selected text                               |
| [waiting ] Prepare search and topics                           |
|                                                               |
| Safe to leave this page. Bot connection: Healthy.              |
| [View 2 warnings]                                 [Cancel]     |
+---------------------------------------------------------------+

+---------------------------------------------------------------+
| Review before inviting members                                |
|                                                               |
| Search [__________________________________________] [Search]   |
| Suggested test: “What charging advice was repeated?”          |
| [Cited sample answer + supporting source messages]             |
|                                                               |
| Topics: Charging, service centres, insurance, local events    |
| Import: 48,204 succeeded | 12 omitted/failed                  |
|                                                               |
| [Adjust settings]                        [Activate workspace]   |
+---------------------------------------------------------------+
```

## 7. Member invitation and verification

```text
+---------------------------------------------------------------+
| JERSEY TESLA OWNERS uses Comvoly                               |
| Connected by: Community administrator                          |
|                                                               |
| Find prior advice, catch up and ask questions with citations. |
| History coverage: Jan 2021–today | Updated recently            |
|                                                               |
| [Continue with my Comvoly account]                             |
| Privacy | What is connected? | Contact administrators          |
+---------------------------------------------------------------+

+---------------------------------------------------------------+
| Verify your community membership                               |
|                                                               |
| Your Comvoly account: stephen@example…                         |
| Telegram identity: Not linked                                  |
|                                                               |
| Linking proves membership; it does not give Comvoly access     |
| to unrelated chats or your Telegram password.                  |
|                                                               |
| [Link Telegram]                                                |
|                                                               |
| Alternative: [Request administrator approval]                  |
+---------------------------------------------------------------+
```

## 8. Member workspace overview

```text
+-----------------------------------------------------------------------+
| COMVOLY  [Jersey Tesla Owners v]  Overview Ask Catch Up Explore Search|
+-----------------------------------------------------------------------+
| Welcome back                                                          |
| Archive Jan 2021–today · Last updated 3 minutes ago                    |
|                                                                       |
| [Catch me up since my last visit]         [Ask a question]             |
|                                                                       |
| IMPORTANT SINCE YOUR LAST VISIT                                       |
| Decision      Monthly meet moved to Saturday      [3 sources]          |
| Recommendation Local tyre supplier mentioned      [8 sources]          |
| Open question Home-charging grant eligibility     [View discussion]    |
|                                                                       |
| FOLLOWED TOPICS                 COMMUNITY KNOWLEDGE                    |
| Charging, servicing             FAQs, decisions, links, files         |
+-----------------------------------------------------------------------+
```

## 9. Ask and evidence

```text
+-----------------------------------------------------------------------+
| Ask Jersey Tesla Owners                                                |
| [What has the group said about winter tyre suppliers?______________]  |
| Scope [All connected history v] Date [Any time v]        [Ask]         |
|                                                                       |
| ANSWER                                                                |
| Members most often recommended ... [1][2], while two people reported  |
| ... [3]. The archive does not establish current pricing.              |
|                                                                       |
| EVIDENCE CHECKED                                                      |
| [1] Message excerpt · #recommendations · 12 Jan 2026 [Open context]    |
| [2] Message + attached invoice/image · 3 Feb 2026    [Open context]    |
| [3] Conflicting experience · 14 Mar 2026             [Open context]    |
|                                                                       |
| [Save] [Ask a follow-up] [Report concern]                              |
+-----------------------------------------------------------------------+
```

## 10. Catch Up, Explore, and Search

```text
+-----------------------------------------------------------------------+
| Catch Up  [Since last visit v] [All topics v]                          |
|                                                                       |
| DECISIONS (2)      QUESTIONS (3)      RECOMMENDATIONS (5)              |
| [Summary + evidence links grouped by discussion]                      |
|                                                                       |
| USEFUL LINKS AND FILES                                                 |
| [Resource + why it appeared + source]                                 |
+-----------------------------------------------------------------------+

+-----------------------------------------------------------------------+
| Explore  Topics | FAQs | Decisions | Recommendations | Links | Files  |
| [Search/filter this community]                                        |
| [Generated topic, coverage, last activity, owner-curated indicator]   |
+-----------------------------------------------------------------------+

+-----------------------------------------------------------------------+
| Search                                                                |
| (o) Find messages  ( ) Find discussions about                         |
| [query________________] [Date] [Space] [Author] [Has attachment]       |
| [Result excerpt + reply/thread context + open original]               |
+-----------------------------------------------------------------------+
```

## 11. Owner settings

```text
+-----------------------------------------------------------------------+
| Settings  Connections | Members | Content & AI | Usage | Export/Delete|
|                                                                       |
| TELEGRAM                                                              |
| Healthy · Last update 3 min · History Jan 2021–today                  |
| Included: Main group · Images/docs · Voice/video excluded             |
| [Change scope] [Pause] [Reconnect]                                    |
|                                                                       |
| IMPORTS                                                               |
| Initial history · Complete with 12 warnings · [View report]           |
+-----------------------------------------------------------------------+
```

## 12. Mobile priority

On mobile:

- account/workspace switcher remains one tap away;
- Ask input and primary action appear before summaries;
- evidence cards stack and preserve open-context actions;
- setup uses one decision per screen;
- upload can be initiated on desktop and monitored on mobile;
- tables become labelled rows rather than horizontal overflow where possible;
- no essential setting depends on hover.

