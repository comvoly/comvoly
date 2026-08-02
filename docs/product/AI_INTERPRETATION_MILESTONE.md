# AI interpretation milestone

## Outcome

Comvoly v2 now interprets authorised community knowledge instead of concatenating
keyword matches. Search remains a supporting retrieval capability; the user-facing
answer synthesises the community's evidence, distinguishes consensus from individual
views or humour, and cites the messages supporting each substantive claim.

## Approved development decision

- Provider: the existing server-side OpenAI integration.
- Pilot model: `gpt-5.6-luna`, selected for cost-sensitive, higher-volume use.
- API: stateless Responses API calls with `store=false`.
- Default reasoning: `none`; answer verbosity: low; maximum output: 700 tokens.
- Allowance: 50 attempted AI interpretations per workspace per calendar month.
- Scope: isolated v2 development only. Production activation remains a separate gate.

## Evidence boundary

Every request is authorised before retrieval. Retrieval filters by the verified
workspace ID, active review state, non-deleted source records and message item type.
It removes generic question terms, ranks exact word matches and passes at most 20
records / 24K characters to the interpreter. Evidence from another workspace cannot
enter either the prompt or returned citations.

Community evidence is treated as untrusted content, not model instructions. The model
has no tools or network access. Its response is accepted as interpreted output only
when it contains one or more valid evidence labels. Unknown or missing labels, an
unavailable model, exhausted allowance or provider error produces an honest ranked
evidence fallback.

## Privacy, safety and usage

- The OpenAI key never reaches the browser or database.
- A stable one-way account hash is sent as the safety identifier.
- API responses are not stored by the provider through this application request.
- Audit events record mode, model and evidence count, never question or message text.
- Separate counters record attempted interpretations and input/output tokens.
- The allowance is reserved atomically, so concurrent requests cannot bypass it.

## Acceptance coverage

Automated tests prove that generic question words no longer select unrelated recent
messages, another workspace's evidence never reaches the interpreter, valid citations
map back to the displayed evidence, the monthly allowance stops further external
calls, token usage is recorded and the Responses API adapter is stateless and bounded.

## Deferred decisions

Production activation, customer-facing plan allowances, semantic embeddings, retained
conversation context, media interpretation, provider data-control configuration and
formal per-model cost accounting remain later decisions. They are not required for
this development acceptance milestone.
