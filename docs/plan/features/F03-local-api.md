# F03 — Local backend and stable API

**Status:** Implemented, needs verification  
**Goal:** provide a dependable local FastAPI/SQLite application boundary that future adapters can reuse.

## Scope

- SQLAlchemy models and SQLite persistence for items, original/source fields, visual descriptions, image manifest, and outfits.
- REST API for listing/filtering items, item details/updates, photo status and reads/uploads, outfits, statistics, and exports/imports.
- Business logic in services, validation in schemas, documented OpenAPI contract.
- Keep item ID immutable after creation.

## Acceptance criteria

- [ ] API starts locally with the documented command and exposes OpenAPI docs.
- [ ] CRUD and filters operate on real imported rows, with stable W001–W139 identifiers.
- [ ] Item update cannot change an existing ID and preserves unedited fields/notes.
- [ ] Missing rows and invalid requests return documented error responses.
- [ ] API handlers delegate business logic to service modules; no future integration needs direct database access.
- [ ] Contract fixtures cover item, visual description, image, outfit, and export representations.

## Current implementation / evidence

- `backend/app/main.py`, `backend/app/api/v1.py`, `backend/app/models.py`, `backend/app/schemas.py`, `backend/app/database.py`, and service modules exist.
- `backend/cloudflare/worker.py` separately implements a D1/R2 adapter; contract parity still needs review.

## Blockers / risks

- Do not expose unauthenticated hosted API routes to the public internet.
- Avoid allowing Cloudflare-specific response details to leak into the shared REST contract.

## Next action

Run and record existing backend tests, then document API response schemas and compare local versus Worker behavior.
