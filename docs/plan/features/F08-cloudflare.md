# F08 — Cloudflare hosting and data adapter

**Status:** In progress  
**Goal:** make the app remotely reachable through a single Access-protected Worker while keeping personal data in private D1/R2 resources.

## Scope

- Python Worker adapter, D1 migrations, private R2 object access, static frontend assets, same-origin API, deployment guide.
- D1 is the system of record for cloud catalog/outfits/manifest; R2 stores photo bytes.
- Protect all Worker URLs with Cloudflare Access before importing personal data.
- Use test data for first deployment and end-to-end checks.

## Acceptance criteria

- [ ] Wrangler config has the real D1 database ID and matching D1/R2 binding names; no secrets or personal data are committed.
- [ ] D1 migration applies cleanly and can be safely reapplied according to Wrangler migration behavior.
- [ ] Worker starts locally with local bindings; frontend and API work on the same origin.
- [ ] All local contract endpoints used by the UI have equivalent Worker behavior, including useful error responses.
- [ ] Image upload/read/replacement uses private R2; no public bucket URL is enabled.
- [ ] Cloudflare Access protects production Worker and preview routes; private-window test unauthenticated gets a login gate.
- [ ] Cloudflare Worker test suite passes; local end-to-end workflow passes with fixtures.
- [ ] Export/import on cloud preserves catalog, visual details, outfits, and photos; conflicts and failures are safe.
- [ ] A rollback/backup path is documented before importing real data.
- [ ] After deploying test data, only then import the user's export and verify a sample of IDs and images.

## Current implementation / evidence

- `backend/cloudflare/worker.py`, `backend/cloudflare/migrations/0001_initial.sql`, and `wrangler.jsonc` exist.
- `wrangler.jsonc` still contains `REPLACE_WITH_D1_DATABASE_ID`; deployment has not been demonstrated.
- `docs/cloudflare_deployment.md` describes setup, Access, migration, deployment, and import steps.
- `backend/tests/test_cloudflare_worker.py` has a test harness but still needs a syntax/test run and broader integration coverage.

## Blockers

- Actual D1 ID has not been added to local Wrangler configuration.
- Access gate has not been verified from an unauthenticated browser session.
- Worker runtime compatibility, API parity, D1/R2 behavior, and archive flow remain unverified.

## Next action

Check test file syntax and understand local Windows async test constraints, then run targeted Worker tests and `pywrangler dev` with local bindings. Do not deploy until the Access gate and database ID are ready.

## Operational guardrails

- No personal import before Access verification.
- No bucket public access.
- Do not include database IDs if sensitive policy changes; do not put API tokens in frontend code.
- Local mode remains supported independently of Cloudflare.
