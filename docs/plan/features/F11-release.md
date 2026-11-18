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
- [x] Add two test deliverables in `backend/tests/test_release_scenario.py`: `test_fixture_release_round_trip` and `test_hosted_import_failure_keeps_local_fallback`. Both use synthetic fixtures and temporary storage, explicit test-only path injection, and no reads of `data/`; they do not run `start.ps1`, which requires private CSVs.

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

The executable rollback procedure is `test_hosted_import_failure_keeps_local_fallback`, not a manual app/server procedure. It creates disposable temporary storage and uses test-only path injection. No manual uvicorn invocation is required.

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
- PR #2 merged these tests through commit `51636f5`. The implementation commit is `d5f7a64`.
- `backend/tests/test_release_scenario.py::test_fixture_release_round_trip` and `backend/tests/test_release_scenario.py::test_hosted_import_failure_keeps_local_fallback` use synthetic fixtures, temporary storage, explicit test-only path injection, no `data/` reads, and no `start.ps1` calls.
- Release scenario command: `$env:PYTHONPATH = "backend"; py -m unittest discover -s backend/tests -p "test_release_scenario.py" -v`. Observed result on commit `d5f7a64`: 2 tests passed.
- Backend suite command: `$env:PYTHONPATH = "backend"; py -m unittest discover -s backend/tests -v`. Observed result on commit `d5f7a64`: 17 tests passed.
- Frontend command: `pnpm --dir frontend build`. Observed result on commit `d5f7a64`: build and typecheck passed.
- The suite emitted a SQLAlchemy `ResourceWarning` from temporary SQLite connections during the fallback test; the test passed. This warning remains a minor cleanup item.
- F11 final release acceptance remains unverified until rerun on the exact release candidate commit and all remaining release evidence is recorded.

## Blockers / risks

- Personal-data migration remains blocked by the F09, F08, F07, private-R2, backup, and rollback gates.
- Avoid publishing a release success claim until final current-checkout acceptance is complete.
- The Cloudflare Worker and real hosted resources remain unverified.

## Next action

On the exact release-candidate commit, rerun the backend suite, frontend build, and fixture release scenario. Record the commit, commands, exit statuses, known limitations, and final rollback evidence. Do not treat intermediate PR checks or merge success as final release acceptance.
