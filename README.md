# Comvoly

Comvoly is a community intelligence platform. It will help authorised community members preserve, search, and understand the knowledge created in their conversations.

## Current prototype

The first validation target is deliberately small:

1. Connect one Telegram community with the necessary permission.
2. Import its messages into a local database.
3. Search those messages and show the original source.

AI answers, additional connectors, subscriptions, and native mobile apps are later stages—not requirements for proving the first concept.

## Project structure

- `frontend/` — Next.js web application
- `backend/` — planned Python service for ingestion and search
- `docs/` — product and technical notes

## Local development

From `frontend/`:

```bash
npm run dev
```

Then visit `http://localhost:3000`.

## Product principle

Comvoly must only expose a community's data to people authorised to access that community. AI output must cite the original community content it relies on.
