# Comvoly test deployment

This deployment uses one small Railway service for the Python API and Telegram sync,
Neon PostgreSQL for the archive, and Cloudflare Pages for the static frontend.

## Safety rules

- Never commit `.env`, the Telegram session, the Neon connection string, or API keys.
- Use Neon’s pooled connection string for `DATABASE_URL`.
- Keep Cloudflare Access in front of both the site and API during the private pilot.
- Keep the local SQLite archive until the Neon import and backup have been verified.

## Railway service

Deploy the repository using the root `Dockerfile`. Configure these Railway variables:

| Variable | Value |
|---|---|
| `DATABASE_URL` | Neon pooled connection string |
| `OPENAI_API_KEY` | OpenAI project key |
| `TELEGRAM_API_ID` | Existing Telegram application ID |
| `TELEGRAM_API_HASH` | Existing Telegram application hash |
| `TELEGRAM_PHONE` | Authorised Telegram account phone number |
| `TELEGRAM_GROUP` | Existing authorised group reference |
| `TELEGRAM_SESSION_STRING` | Output of `python src/export_telegram_session.py` |
| `COMVOLY_OWNER_PASSWORD_HASH` | Generated owner password hash |
| `COMVOLY_SESSION_SECRET` | Random session signing secret |
| `COMVOLY_AI_MODEL` | `gpt-5.6-luna` |
| `COMVOLY_AI_REASONING` | `none` |
| `COMVOLY_AI_MAX_OUTPUT_TOKENS` | `1200` |
| `COMVOLY_RUN_SYNC` | `true` |
| `COMVOLY_SYNC_INTERVAL` | `120` |
| `COMVOLY_SECURE_COOKIES` | `true` |
| `COMVOLY_WEB_ORIGIN` | `https://comvoly.com` |

Railway supplies `PORT`. After deployment, generate a Railway domain temporarily and
verify `/health` before adding `api.comvoly.com`.

## Initial archive import

The embedded sync creates the schema automatically and imports up to 100 new messages
per pass. For the current test archive this reproduces the local 61 messages in Neon.
Verify the message count in Comvoly before considering the cloud archive authoritative.

## Cloudflare Pages

Create a Pages project from the same GitHub repository:

- Root directory: `frontend`
- Build command: `npm run build`
- Output directory: `out`
- Build variable: `NEXT_PUBLIC_COMVOLY_API_URL=https://api.comvoly.com`

First use the generated `pages.dev` URL. After the API is healthy, attach `comvoly.com`
and `www.comvoly.com`, then redirect `comvoly.co.uk` to `https://comvoly.com`.

## Private-pilot access

Create Cloudflare Access self-hosted applications for `comvoly.com` and
`api.comvoly.com`. Start with an allow policy containing only the founder’s existing
Google identity. Do not invite pilot users until API access through Cloudflare and the
application owner session have both been tested.
