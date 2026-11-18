# Roadmap Refresh Design

## Intent

Make the delivery roadmap easier to execute and safer to use for Cloudflare work. Keep `docs/plan/README.md` as the source of truth for scope, status, dependencies, and sequencing.

## Goals

- Make feature dependencies and verification order explicit.
- Separate Cloudflare fixture-only bootstrap, production exposure, and any import of personal data.
- Define security, backup, rollback, and verification gates before real-data import.
- Treat quality checks as continuous work, with F11 as the final release gate.
- Keep evidence concrete and consistent across the roadmap and affected feature plans.
- Align the Cloudflare deployment guide's import instructions with the roadmap gates.
- Require an isolated automated fixture scenario for release verification; never use the private-data startup script for that fixture run.

## Non-goals

- Change product scope, feature status, or implementation.
- Install skills, run tests, deploy Cloudflare, or inspect personal wardrobe data.
- Rewrite unrelated feature plans or deployment documentation.

## Constraints

- Preserve the local-first workflow and independent local API and Cloudflare adapters.
- Keep original local CSVs, photos, manifest, and SQLite data as the rollback source for the initial CSV-to-cloud migration. Do not import personal data before Access protection, export integrity, and local fallback are verified.
- Keep current acceptance requirements unless a wording change is needed to clarify sequencing or evidence.

## Approaches

1. **README-only:** clarify dependencies and gates centrally. This is smaller, but leaves F07/F08/F09/F11 instructions inconsistent.
2. **Coordinated documentation update — selected:** update the README and F07, F08, F09, and F11 so the central sequence and feature-level criteria agree. This addresses the identified risks without broadening feature scope.

## Design

- The README will give a dependency-oriented sequence: local data/API baseline; photos and UI/outfit flows; portability; security gate; Cloudflare test deployment; release verification. F10 remains deferred until the API contracts are verified.
- F07 will make a fixture-based export/import round trip and documented local-fallback evidence prerequisites to cloud migration. The initial migration rollback is to the unchanged local file-based app; quarantine a failed cloud target rather than attempting an unverified in-place D1/R2 restore.
- F08 will require the Worker test suite, local D1 migration/reapplication, and local end-to-end fixture checks before hosted work. It will separate fixture-only bootstrap, hosted fixture verification, production exposure, and personal-data import. If an initial deployment is needed to configure Access, limit it to an empty/test-only Worker and data, then protect and verify Access immediately. Do not apply remote migrations until Access is verified or expose production until F09 passes.
- Before personal-data import, verify Access, private storage, local and hosted fixture checks, tested export integrity, a verified local source backup, and a tested local-app fallback. The Cloudflare deployment guide will make these stages and prerequisites explicit.
- Verify that Wrangler reports the intended D1 database name and ID. Keep the actual local ID out of documentation and version control by using a local config copy ignored through `.git/info/exclude`, and pass it with Wrangler's `--config` flag.
- Start hosted resource operations only after local verification passes. Document create-or-select commands for D1 and R2 without allowing config auto-updates to touch tracked files.
- Apply and reapply remote D1 migrations only after the fixture-only Worker is protected by verified Access. Keep local migrations and fixture checks before hosted work.
- F09 will state that security gates apply before hosted exposure and real-data import, and identify testable evidence rather than treating security review as a status label.
- F09 evidence will include separate unauthenticated checks for the production host and every enabled preview route.
- F11 will distinguish checks run throughout delivery from the final release gate. The final gate will include new tests in `backend/tests/test_release_scenario.py` using temporary storage and synthetic fixtures, plus exact commands/results for the current checkout.
- The fixture scenario will verify import, item/photo reads, outfit persistence, archive export/import into an empty database, preserved records/links/image bytes, and no partial mutation on rejected import. It must not read `data/` or run `start.ps1`, which requires private CSV files.
- The fixture tests will include `test_fixture_release_round_trip` and `test_hosted_import_failure_keeps_local_fallback`. They will use temporary storage and explicit test-only path injection, instantiate a fresh local app instance after a simulated hosted-import failure, and verify fixture records and photo checksums remain unchanged. They must not read `data/` or run `start.ps1`.

## Builder calls

- Keep exact operational values, command syntax, and check results to be filled in when verified; do not invent them in the plan.
- Keep F01–F06 and F10 unchanged unless a cross-reference is required to make dependencies clear.
