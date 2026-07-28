# Comvoly

Comvoly is a community intelligence platform. It helps authorised community
members preserve, search, and understand the knowledge created in their conversations.

## Current owner MVP

The first validation target is deliberately small:

1. Connect one Telegram community with the necessary permission.
2. Import its messages into a local database.
3. Ask grounded questions or search messages and inspect the original evidence.

The current build includes grounded AI answers with archive citations. Authentication,
additional connectors, subscriptions, and native mobile apps are later stages.

## Project structure

- `frontend/` — Next.js web application
- `backend/` — Python ingestion, archive, AI, and API services

## Local development

After completing the backend and frontend setup, run:

```cmd
backend\src\Start Comvoly.cmd
```

This starts the Telegram sync agent, JSON API, and Next.js interface, then opens
`http://localhost:3000`.

## Path to the purchased domain

The laptop is development infrastructure only. Do not expose its local server to the
internet. Move Comvoly to managed hosting after the owner MVP is stable and before
inviting outside users:

1. Replace the local owner-password gate with managed identity and enforce community
   membership on every request.
2. Move SQLite and the Telegram session to encrypted managed services, using PostgreSQL
   for the production archive and a dedicated background worker for ingestion.
3. Deploy the web application and API to managed cloud hosting with logs, backups,
   secrets management, and health monitoring.
4. Connect the purchased domain, enable HTTPS, and run a small private pilot.

The local owner gate now protects the development archive, but it is not the eventual
multi-user identity system. The domain is part of the production deployment milestone,
immediately after managed identity and access control—not something that should point
at the laptop.

## Product principle

Comvoly must only expose a community's data to people authorised to access that
community. AI output must cite the original community content it relies on.

## Product design

The working prototype is now followed by a documented multi-community product-design
phase. See the [Comvoly v2 product-design package](docs/product/README.md) for the
requirements, owner/member journeys, identity and permission model, platform connector
specifications, historical import/media design, pilot, risks, and implementation
roadmap. No major production rewrite should begin until its material decisions and
external platform gates have been reviewed.
