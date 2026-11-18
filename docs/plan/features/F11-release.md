# F11 — Quality, setup, and release

**Status:** In progress  
**Goal:** make the app reproducible to install, safe to update, and verifiable from source import through export.

## Scope

- Clean local setup instructions and one clear start/stop path.
- Tests for catalog/visual imports, photos, API CRUD, outfits, exports, archive import, and security edge cases.
- Build and smoke checks for frontend and local backend.
- Cloud test deployment instructions distinct from production data migration.
- User-facing troubleshooting and recovery notes.

## Acceptance criteria

- [ ] A clean checkout can install dependencies and start locally with documented steps.
- [ ] Required backend suite and frontend typecheck/build pass with recorded commands/results.
- [ ] Tests use fixtures/mock HTTP and do not depend on live CloudFront or production Cloudflare data.
- [ ] Full scenario passes: import source CSVs → inspect items/photos → save outfit → export ZIP → import into clean DB → verify IDs/links.
- [ ] README accurately reflects current status, local setup, cloud setup, privacy limits, and tested versions.
- [ ] Release record lists commit, test evidence, known limitations, and rollback instructions.

## Current implementation / evidence

- Local README, start/stop scripts, backend tests, frontend package scripts, and Cloudflare guide exist.
- README contains cloud status text that does not yet reflect the new Cloudflare adapter; reconcile it.
- Cloudflare test suite has not been recorded as passing. Frontend and prior local test runs were previously reported, but rerun before release against this checkout.

## Blockers / risks

- The current checkout has uncommitted Cloudflare changes; no release commit or deployment was completed in the last work session.
- Avoid publishing a success claim based only on code compilation.

## Next action

Establish a green local baseline, fix known test/documentation issues, then execute the full local acceptance scenario before cloud migration.
