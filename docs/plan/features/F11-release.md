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
- [ ] Required backend suite and frontend typecheck/build run on the current checkout and pass with recorded commands/results.
- [ ] Tests use fixtures/mock HTTP and do not depend on live CloudFront, production Cloudflare, or personal data.
- [ ] The final fixture-only full local scenario passes: import fixture source data → inspect fixture items/photos → save an outfit → export a ZIP → import it into a clean fixture DB → verify IDs, links, photos, outfit associations, and export/report outcomes.
- [ ] Add two future test deliverables in `backend/tests/test_release_scenario.py`: `test_fixture_release_round_trip` and `test_hosted_import_failure_keeps_local_fallback`. Both must use synthetic fixtures and temporary storage, explicit test-only path injection, and no reads of `data/`; do not run `start.ps1`, which requires private CSVs.

  `test_fixture_release_round_trip` must verify fixture import, item/photo reads, outfit persistence, archive export and import to an empty DB, record/link/photo-byte integrity, and no partial mutation on rejected import.

  `test_hosted_import_failure_keeps_local_fallback` must itself snapshot the source fixture files and local DB, simulate hosted import failure, instantiate a fresh local app instance configured from temporary paths, and verify that fixture records and photo checksums remain unchanged. The test is the executable procedure; no manual uvicorn invocation is needed.

  Run both tests with:

  ```powershell
  $env:PYTHONPATH = "backend"
  py -m unittest discover -s backend/tests -p "test_release_scenario.py" -v
  ```

- [ ] README accurately reflects current status, local setup, cloud setup, privacy limits, and tested versions.
- [ ] Release record lists the exact commit, exact command and exit/output result for each required check, full fixture-scenario outcome, known limitations, and rollback evidence.

### Continuous baseline and regression checks

Run these checks during feature work as baseline and regression evidence, not as the final release acceptance:

- Backend suite:

  ```powershell
  $env:PYTHONPATH = "backend"
  py -m unittest discover -s backend/tests -v
  ```

- Frontend build:

  ```powershell
  pnpm --dir frontend build
  ```

Each run must record the checkout/commit, command, exit status, and relevant result. Passing intermediate runs is baseline/regression evidence only; it does not establish release acceptance.

### Final release acceptance

Release acceptance is the current-checkout gate, not a claim inherited from earlier feature work. It requires rerunning the documented backend suite and frontend build above, then completing the full local scenario with fixture-only source, catalog, photo, outfit, archive, and database data. Record the exact commands, exact outcomes, commit, known limitations, and rollback evidence. The full scenario's required outcome is successful fixture import, item/photo inspection, outfit persistence, ZIP export, clean-database archive import, and verification of IDs, links, photos, and outfit associations. The release record must identify any failed or unavailable check and must not infer success from compilation or partial scenarios.

#### Fixture-only rollback evidence procedure

The executable rollback procedure is the future `test_hosted_import_failure_keeps_local_fallback` test, not a manual app/server procedure. It must create disposable temporary storage and use test-only path injection. No manual uvicorn invocation is required.

The procedure is:

1. Create a disposable temporary workspace containing only synthetic catalog and visual CSV fixtures, synthetic photo bytes, a synthetic photo manifest, and a synthetic SQLite database. Do not use `data/`, private wardrobe files, or `start.ps1`.
2. Through test-only path injection, give the test temporary paths for fixture source files and the local DB. Snapshot/preserve copies of the source catalog CSV, visual-description CSV, photos, photo manifest, and SQLite database, and create and verify a SQLite backup. Record fixture record identifiers and SHA-256 checksums for every fixture photo before the test.
3. Configure the hosted side only with test-only resources and synthetic fixtures. If this test runs outside a real hosted target, use an explicit hosted-import failure substitute that performs no personal-data access. Simulate a hosted-import failure before any cloud record/photo is allowed to replace the local source set.
4. Quarantine the test cloud target: stop further cloud use, keep the target protected and out of use, record the test target identifier, and leave its contents untouched. Do not delete, truncate, overwrite, or restore D1/R2 in place.
5. Instantiate a fresh local app instance from the temporary fixture and DB paths recorded above. This is the fallback test itself; do not replace it with manual uvicorn startup.
6. Verify the fresh instance exposes the original fixture record set and the original photo bytes/checksums. Compare the SQLite backup and local source copies against their before-failure snapshots. Any difference is a rollback failure.
7. Record the exact test invocation, temporary workspace/backup location, fixture target, quarantine action, fresh-instance construction method, record comparison result, and photo SHA-256 values. Record observed results only after they are run.

Initial migration rollback is a local fallback, not an in-place D1/R2 restore. On a hosted-import failure, the approved recovery is to stop cloud use, quarantine the remote target unchanged, and continue with the preserved local source files and SQLite backup. Record the exact backup contents, target/restore point, cloud-quarantine action, local restart method, record comparison, and photo checksums. Do not invent commands or record unrun steps as results. Until this evidence exists, F11 release status remains unverified.

F11 release acceptance alone does not approve personal-data import. Import also requires the separate F09 security gate plus the applicable F07, F08, backup, private-R2, and tested-rollback gates.

## Current implementation / evidence

- Local README, start/stop scripts, backend tests, frontend package scripts, and Cloudflare guide exist.
- README contains cloud status text that does not yet reflect the new Cloudflare adapter; reconcile it.
- Cloudflare test suite has not been recorded as passing. Frontend and prior local test runs were previously reported, but rerun before release against this checkout.
- The future `backend/tests/test_release_scenario.py::test_fixture_release_round_trip` and `backend/tests/test_release_scenario.py::test_hosted_import_failure_keeps_local_fallback` deliverables remain isolated from private startup and personal data. They must use synthetic fixtures, temporary storage, and test-only path injection; avoid reads of `data/`; and never call `start.ps1`. The fallback test must snapshot source fixture files and the local DB, simulate hosted import failure, instantiate a fresh local app instance from temporary paths, and verify fixture records and photo checksums unchanged. No manual uvicorn procedure is required.
- Exact procedure: set `$env:PYTHONPATH = "backend"` and run `py -m unittest discover -s backend/tests -p "test_release_scenario.py" -v`. The exact result for these tests has not been run or recorded, so both remain marked future/unverified and no pass is claimed.
- Fixture-only rollback evidence has not been run or recorded. The procedure above is the reproducible evidence requirement, not a claim that rollback has passed. Exact rollback target, backup location, quarantine action, fresh-instance method, record comparison, and photo SHA-256 results must be added only from a completed run.

## Blockers / risks

- The current checkout has uncommitted Cloudflare changes; no release commit or deployment was completed in the last work session.
- Avoid publishing a success claim based only on code compilation.
- The fixture release scenario and fixture-only local-fallback evidence are not yet evidenced.
- Neither future release test is yet marked passing or unverified by an observed run.

## Next action

Establish and rerun a green local baseline, fix known test/documentation issues, then execute the full local fixture-only acceptance scenario for the current checkout before the release record is accepted. Keep intermediate checks separate from final release acceptance and do not record unrun commands or outcomes as passed.

Implement the approved future tests `backend/tests/test_release_scenario.py::test_fixture_release_round_trip` and `backend/tests/test_release_scenario.py::test_hosted_import_failure_keeps_local_fallback` only with synthetic fixtures and temporary storage, test-only path injection, and no reads of `data/` or `start.ps1` calls. Then run the exact future-scenario unittest command recorded above and record only observed results.

Before any personal-data migration, execute the fixture-only rollback procedure through `test_hosted_import_failure_keeps_local_fallback`: snapshot the synthetic source fixture files and local DB, simulate hosted-import failure, quarantine the test cloud target, instantiate a fresh local app instance from temporary paths, and compare fixture records and photo SHA-256 checksums. Record the exact procedure and observed results; do not claim rollback passed until evidence exists. Until implementation and execution are complete, keep both tests and F11 release status future/unverified.
